# Copyright 2018-2021 Streamlit Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""@st.memo: pickle-based caching"""

import contextlib
import functools
import types
from typing import Optional, Iterator

import streamlit as st
from streamlit import config
from streamlit.logger import get_logger

from .cache_errors import CachedStFunctionWarning
from .cache_utils import ThreadLocalCacheInfo, make_function_key, make_value_key
from .memo_cache import CacheKeyNotFoundError, MemoCache

_LOGGER = get_logger(__name__)


_cache_info = ThreadLocalCacheInfo()


@contextlib.contextmanager
def _calling_cached_function(func: types.FunctionType) -> Iterator[None]:
    _cache_info.cached_func_stack.append(func)
    try:
        yield
    finally:
        _cache_info.cached_func_stack.pop()


@contextlib.contextmanager
def suppress_cached_st_function_warning() -> Iterator[None]:
    _cache_info.suppress_st_function_warning += 1
    try:
        yield
    finally:
        _cache_info.suppress_st_function_warning -= 1
        assert _cache_info.suppress_st_function_warning >= 0


def _show_cached_st_function_warning(
    dg: "st.delta_generator.DeltaGenerator",
    st_func_name: str,
    cached_func: types.FunctionType,
) -> None:
    # Avoid infinite recursion by suppressing additional cached
    # function warnings from within the cached function warning.
    with suppress_cached_st_function_warning():
        e = CachedStFunctionWarning(st_func_name, cached_func)
        dg.exception(e)


def maybe_show_cached_st_function_warning(
    dg: "st.delta_generator.DeltaGenerator", st_func_name: str
) -> None:
    """If appropriate, warn about calling st.foo inside @cache.

    DeltaGenerator's @_with_element and @_widget wrappers use this to warn
    the user when they're calling st.foo() from within a function that is
    wrapped in @st.cache.

    Parameters
    ----------
    dg : DeltaGenerator
        The DeltaGenerator to publish the warning to.

    st_func_name : str
        The name of the Streamlit function that was called.

    """
    if (
        len(_cache_info.cached_func_stack) > 0
        and _cache_info.suppress_st_function_warning <= 0
    ):
        cached_func = _cache_info.cached_func_stack[-1]
        _show_cached_st_function_warning(dg, st_func_name, cached_func)


def memo(
    func: Optional[types.FunctionType] = None,
    persist: bool = False,
    show_spinner: bool = True,
    suppress_st_warning=False,
    max_entries: Optional[int] = None,
    ttl: Optional[float] = None,
):
    # Support passing the params via function decorator, e.g.
    # @st.memo(persist=True, show_spinner=False)
    if func is None:
        return lambda f: _make_memo_wrapper(
            func=f,
            persist=persist,
            show_spinner=show_spinner,
            suppress_st_warning=suppress_st_warning,
            max_entries=max_entries,
            ttl=ttl,
        )

    return _make_memo_wrapper(
        func=func,
        persist=persist,
        show_spinner=show_spinner,
        suppress_st_warning=suppress_st_warning,
        max_entries=max_entries,
        ttl=ttl,
    )


def _make_memo_wrapper(
    func: types.FunctionType,
    persist: bool = False,
    show_spinner: bool = True,
    suppress_st_warning=False,
    max_entries: Optional[int] = None,
    ttl: Optional[float] = None,
):
    function_key = None

    @functools.wraps(func)
    def wrapped_func(*args, **kwargs):
        """This function wrapper will only call the underlying function in
        the case of a cache miss. Cached objects are stored in the cache/
        directory."""

        if not config.get_option("client.caching"):
            _LOGGER.debug("Purposefully skipping cache")
            return func(*args, **kwargs)

        name = func.__qualname__

        if len(args) == 0 and len(kwargs) == 0:
            message = "Running `%s()`." % name
        else:
            message = "Running `%s(...)`." % name

        def get_or_create_cached_value():
            nonlocal function_key
            if function_key is None:
                # Create our function key. If the function's source code
                # changes, it'll be invalidated.
                function_key = make_function_key(func)

            # Get the cache that's attached to this function.
            cache = MemoCache.get_cache(function_key, max_entries, ttl)

            # Generate the key for the cached value. This is based on the
            # arguments passed to the function.
            value_key = make_value_key(func, *args, **kwargs)

            try:
                return_value = cache.read_value(
                    key=value_key,
                    persist=persist,
                )
                _LOGGER.debug("Cache hit: %s", func)

            except CacheKeyNotFoundError:
                _LOGGER.debug("Cache miss: %s", func)

                with _calling_cached_function(func):
                    if suppress_st_warning:
                        with suppress_cached_st_function_warning():
                            return_value = func(*args, **kwargs)
                    else:
                        return_value = func(*args, **kwargs)

                cache.write_value(
                    key=value_key,
                    value=return_value,
                    persist=persist,
                )

            return return_value

        if show_spinner:
            with st.spinner(message):
                return get_or_create_cached_value()
        else:
            return get_or_create_cached_value()

    # Make this a well-behaved decorator by preserving important function
    # attributes.
    try:
        wrapped_func.__dict__.update(func.__dict__)
    except AttributeError:
        pass

    return wrapped_func
