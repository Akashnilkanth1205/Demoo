# Copyright 2018 Streamlit Inc. All rights reserved.
# -*- coding: utf-8 -*-

"""A library of caching utilities."""

# Python 2/3 compatibility
from __future__ import (absolute_import, division, print_function,
                        unicode_literals)

import ast
import hashlib
import inspect
import os
import shutil
import struct
import textwrap
from collections import namedtuple
from functools import wraps

import astor

import streamlit as st
from streamlit import config, util
from streamlit.compatibility import setup_2_3_shims
from streamlit.hashing import CodeHasher, Context, get_hash
from streamlit.logger import get_logger

setup_2_3_shims(globals())


try:
    # cPickle, if available, is much faster than pickle.
    # Source: https://pymotw.com/2/pickle/
    import cPickle as pickle
except ImportError:
    import pickle


LOGGER = get_logger(__name__)


class CacheError(Exception):
    pass


class CacheKeyNotFoundError(Exception):
    pass


class CachedObjectWasMutatedError(ValueError):
    pass


CacheEntry = namedtuple('CacheEntry', ['value', 'hash'])


# The in memory cache.
_mem_cache = {}  # type: Dict[string, CacheEntry]


class _AddCopy(ast.NodeTransformer):
    """
    An AST transformer that wraps function calls with copy.deepcopy.
    Use this transformer if you will convert the AST back to code.
    The code won't work without importing copy.
    """

    def __init__(self, func_name):
        self.func_name = func_name

    def visit_Call(self, node):
        if (hasattr(node.func, 'func') and hasattr(node.func.func, 'value')
                and node.func.func.value.id == 'st'
                and node.func.func.attr == 'cache'):
            # Wrap st.cache(func(...))().
            return ast.copy_location(ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id='copy', ctx=ast.Load()),
                    attr='deepcopy', ctx=ast.Load()
                ), args=[node], keywords=[]
            ), node)
        elif hasattr(node.func, 'id') and node.func.id == self.func_name:
            # Wrap func(...) where func is the cached function.

            # Add caching to nested calls.
            self.generic_visit(node)

            return ast.copy_location(ast.Call(
                func=ast.Attribute(
                    value=ast.Name(id='copy', ctx=ast.Load()),
                    attr='deepcopy', ctx=ast.Load()
                ), args=[node], keywords=[]), node)

        self.generic_visit(node)
        return node


def _build_caching_func_error_message(persisted, func, caller_frame):
    name = func.__name__

    frameinfo = inspect.getframeinfo(caller_frame)
    caller_file_name, caller_lineno, _, lines, _ = frameinfo

    try:
        # only works if calling code is a single line
        parsed_context = ast.parse(lines[0])
        parsed_context = _AddCopy(name).visit(parsed_context)
        copy_code = astor.to_source(parsed_context)
    except SyntaxError:
        LOGGER.debug('Could not parse calling code `%s`.', lines[0])
        copy_code = '... = copy.deepcopy(%s(...))' % name

    if persisted:
        load_or_rerun = 'load the value from disk'
    else:
        load_or_rerun = 'rerun the function'

    message = (
        '### ⚠️ Your Code Mutated a Return Value\n'
        'Since your program subsequently mutated the return value of the '
        'cached function `{name}`, Streamlit has to {load_or_rerun} in '
        '`{file_name}` line {lineno}.\n\n'
        'To dismiss this warning, you could copy the return value. '
        'For example by changing `{caller_file_name}` line {caller_lineno} to:'
        '\n```python\nimport copy\n{copy_code}\n```\n\n'

        'Or add `ignore_hash=True` to the `streamlit.cache` decorator for '
        '`{name}`.\n\n'

        'Learn more about caching and copying in the '
        '[Streamlit documentation](https://streamlit.io/secret/docs/tutorial/caching_mapping_more.html).'
    )

    return message.format(
        name=name,
        load_or_rerun=load_or_rerun,
        file_name=os.path.relpath(func.__code__.co_filename),
        lineno=func.__code__.co_firstlineno,
        caller_file_name=os.path.relpath(caller_file_name),
        caller_lineno=caller_lineno,
        copy_code=copy_code
    )


def _build_caching_block_error_message(persisted, code):
    load_or_rerun = 'load the value from disk' if persisted else 'rerun the code'

    message = (
        '### ⚠️ Your Code Mutated a Computed Value\n'
        'Since your program subsequently mutated the value of a cached block, '
        'Streamlit has to {load_or_rerun} in `{file_name}` line {lineno}.\n\n'
        'To dismiss this warning, you could copy the computed value. '

        'Or add `ignore_hash=True` to the constructor of `streamlit.Cache`.\n\n'

        'Learn more about caching and copying in the '
        '[Streamlit documentation](https://streamlit.io/secret/docs/tutorial/tutorial_caching.html).'
    )

    return message.format(
        load_or_rerun=load_or_rerun,
        file_name=os.path.relpath(code.co_filename),
        lineno=code.co_firstlineno
    )


def _read_from_mem_cache(key, ignore_hash):
    if key in _mem_cache:
        entry = _mem_cache[key]

        if ignore_hash or get_hash(entry.value) == entry.hash:
            LOGGER.debug('Memory cache HIT: %s', type(entry.value))
            return entry.value
        else:
            LOGGER.debug('Cache object was mutated: %s', key)
            raise CachedObjectWasMutatedError()
    else:
        LOGGER.debug('Memory cache MISS: %s', key)
        raise CacheKeyNotFoundError('Key not found in mem cache')


def _write_to_mem_cache(key, value, ignore_hash):
    _mem_cache[key] = CacheEntry(
        value=value,
        hash=None if ignore_hash else get_hash(value)
    )


def _read_from_disk_cache(key):
    path = util.get_streamlit_file_path('cache', '%s.pickle' % key)

    try:
        with util.streamlit_read(path, binary=True) as input:
            value = pickle.load(input)
            LOGGER.debug('Disk cache HIT: %s', type(value))
    except util.Error as e:
        LOGGER.error(e)
        raise CacheError('Unable to read from cache: %s' % e)
    except FileNotFoundError:
        raise CacheKeyNotFoundError('Key not found in disk cache')
    return value


def _write_to_disk_cache(key, value):
    path = util.get_streamlit_file_path('cache', '%s.pickle' % key)

    try:
        with util.streamlit_write(path, binary=True) as output:
            pickle.dump(value, output, pickle.HIGHEST_PROTOCOL)
    # In python 2, it's pickle struct error.
    # In python 3, it's an open error in util.
    except (util.Error, struct.error) as e:
        LOGGER.debug(e)
        # Cleanup file so we don't leave zero byte files.
        try:
            os.remove(path)
        except (FileNotFoundError, IOError, OSError):
            pass
        raise CacheError('Unable to write to cache: %s' % e)


def _read_from_cache(key, persisted, ignore_hash, func_or_code, caller_frame):
    """
    Read the value from the cache. Our goal is to read from memory
    if possible. If the data was mutated (hash changed), we show a
    warning. If reading from memory fails, we either read from disk
    or rerun the code.
    """
    try:
        return _read_from_mem_cache(key, ignore_hash)
    except (CacheKeyNotFoundError, CachedObjectWasMutatedError) as e:
        if isinstance(e, CachedObjectWasMutatedError):
            if inspect.isroutine(func_or_code):
                message = _build_caching_func_error_message(
                    persisted, func_or_code, caller_frame)
            else:
                message = _build_caching_block_error_message(
                    persisted, func_or_code)
            st.warning(message)

        if persisted:
            value = _read_from_disk_cache(key)
            _write_to_mem_cache(key, value, ignore_hash)
            return value
        raise e


def _write_to_cache(key, value, persist, ignore_hash):
    _write_to_mem_cache(key, value, ignore_hash)
    if persist:
        _write_to_disk_cache(key, value)


def cache(func=None, persist=False, ignore_hash=False):
    """Function decorator to memoize function executions.

    Parameters
    ----------
    func : callable
        The function to cache. Streamlit hashes the function and dependent code.
        Streamlit can only hash nested objects (e.g. `bar` in `foo.bar`) in
        Python 3.4+.

    persist : boolean
        Whether to persist the cache on disk.

    ignore_hash : boolean
        Disable hashing return values. These hash values are otherwise
        used to validate that return values are not mutated.

    Example
    -------
    >>> @st.cache
    ... def fetch_and_clean_data(url):
    ...     # Fetch data from URL here, and then clean it up.
    ...     return data
    ...
    >>> d1 = fetch_and_clean_data(DATA_URL_1)
    >>> # Actually executes the function, since this is the first time it was
    >>> # encountered.
    >>>
    >>> d2 = fetch_and_clean_data(DATA_URL_1)
    >>> # Does not execute the function. Just returns its previously computed
    >>> # value. This means that now the data in d1 is the same as in d2.
    >>>
    >>> d3 = fetch_and_clean_data(DATA_URL_2)
    >>> # This is a different URL, so the function executes.

    To set the `persist` parameter, use this command as follows:

    >>> @st.cache(persist=True)
    ... def fetch_and_clean_data(url):
    ...     # Fetch data from URL here, and then clean it up.
    ...     return data

    To disable hashing return values, set the `ignore_hash` parameter to `True`:

    >>> @st.cache(ignore_hash=True)
    ... def fetch_and_clean_data(url):
    ...     # Fetch data from URL here, and then clean it up.
    ...     return data

    """
    # Support setting the persist and ignore_hash parameters via
    # @st.cache(persist=True, ignore_hash=True)
    if func is None:
        return lambda f: cache(func=f, persist=persist, ignore_hash=ignore_hash)

    @wraps(func)
    def wrapped_func(*argc, **argv):
        """This function wrapper will only call the underlying function in
        the case of a cache miss. Cached objects are stored in the cache/
        directory."""
        if not config.get_option('client.caching'):
            LOGGER.debug('Purposefully skipping cache')
            return func(*argc, **argv)

        name = func.__name__

        if len(argc) == 0 and len(argv) == 0:
            message = 'Running %s().' % name
        else:
            message = 'Running %s(...).' % name
        with st.spinner(message):
            hasher = hashlib.new('md5')

            args_hasher = CodeHasher('md5', hasher)
            args_hasher.update([argc, argv])
            LOGGER.debug('Hashing arguments to %s of %i bytes.',
                         name, args_hasher.size)

            code_hasher = CodeHasher('md5', hasher)
            code_hasher.update(func)
            LOGGER.debug('Hashing function %s in %i bytes.',
                         name, code_hasher.size)

            key = hasher.hexdigest()
            LOGGER.debug('Cache key: %s', key)

            caller_frame = inspect.currentframe().f_back
            try:
                return_value = _read_from_cache(
                    key, persist, ignore_hash, func, caller_frame)
            except (CacheKeyNotFoundError, CachedObjectWasMutatedError):
                return_value = func(*argc, **argv)
                _write_to_cache(key, return_value, persist, ignore_hash)

        return return_value

    # Make this a well-behaved decorator by preserving important function
    # attributes.
    try:
        wrapped_func.__dict__.update(func.__dict__)
    except AttributeError:
        pass

    return wrapped_func


class Cache(dict):
    """Cache object to persist data across reruns.

    Parameters
    ----------

    Example
    -------
    >>> c = st.Cache()
    ... if c:
    ...     # Fetch data from URL here, and then clean it up. Finally assign to c.
    ...     c.data = ...
    ...
    >>> # c.data will always be defined but the code block only runs the first time

    The only valid side effect inside the if code block are changes to c. Any
    other side effect has undefined behavior.

    In Python 3.8 and above, you can combine the assignment and if-check with an
    assignment expression (`:=`).

    >>> if c := st.Cache():
    ...     # Fetch data from URL here, and then clean it up. Finally assign to c.
    ...     c.data = ...


    """

    def __init__(self, persist=False, ignore_hash=False):
        self._persist = persist
        self._ignore_hash = ignore_hash

        dict.__init__(self)

    def has_changes(self):
        caller_frame = inspect.currentframe().f_back

        caller_name = caller_frame.f_code.co_name
        if caller_name == '__nonzero__' or caller_name == '__bool__':
            caller_frame = caller_frame.f_back

        frameinfo = inspect.getframeinfo(caller_frame)
        filename, caller_lineno, _, code_context, _ = frameinfo

        code_context = code_context[0]

        indent_if = len(code_context) - len(code_context.lstrip())

        lines = ''
        with open(filename, 'r') as f:
            for line in f.readlines()[caller_lineno:]:
                if line.strip() == '':
                    continue
                indent = len(line) - len(line.lstrip())
                if indent <= indent_if:
                    break
                if line.strip() and not line.lstrip().startswith('#'):
                    lines += line

        program = textwrap.dedent(lines)

        context = Context(
            dict(caller_frame.f_globals, **caller_frame.f_locals),None, {})
        code = compile(program, filename, 'exec')

        code_hasher = CodeHasher('md5')
        code_hasher.update(code, context)
        LOGGER.debug('Hashing block in %i bytes.', code_hasher.size)

        key = code_hasher.hexdigest()
        LOGGER.debug('Cache key: %s', key)

        try:
            self.update(_read_from_cache(
                key, self._persist, self._ignore_hash, code, caller_frame))
        except (CacheKeyNotFoundError, CachedObjectWasMutatedError):
            exec(code, caller_frame.f_globals, caller_frame.f_locals)
            _write_to_cache(key, self, self._persist, self._ignore_hash)

        # Always return False so that we have control over the execution.
        return False

    def __bool__(self):
        return self.has_changes()

    # Python 2 doesn't have __bool__
    def __nonzero__(self):
        return self.__bool__()

    def __getattr__(self, key):
        if key not in self:
            raise AttributeError('Cache has no atribute %s' % key)
        return self.__getitem__(key)

    def __setattr__(self, key, value):
        dict.__setitem__(self, key, value)


def clear_cache():
    """Clear the memoization cache.

    Returns
    -------
    boolean
        True if the disk cache was cleared. False otherwise (e.g. cache file
        doesn't exist on disk).
    """
    _clear_mem_cache()
    return _clear_disk_cache()


def get_cache_path():
    return util.get_streamlit_file_path('cache')


def _clear_disk_cache():
    # TODO: Only delete disk cache for functions related to the user's current
    # script.
    cache_path = get_cache_path()
    if os.path.isdir(cache_path):
        shutil.rmtree(cache_path)
        return True
    return False


def _clear_mem_cache():
    global _mem_cache
    _mem_cache = {}
