# Copyright (c) Streamlit Inc. (2018-2022) Snowflake Inc. (2022)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""@st.cache_data: pickle-based caching"""

from __future__ import annotations

import pickle
import threading
import types
from datetime import timedelta
from typing import Any, Callable, TypeVar, Union, cast, overload

from typing_extensions import Literal, TypeAlias

import streamlit as st
from streamlit import runtime
from streamlit.deprecation_util import show_deprecation_warning
from streamlit.errors import StreamlitAPIException
from streamlit.logger import get_logger
from streamlit.runtime.caching.cache_errors import CacheError, CacheKeyNotFoundError
from streamlit.runtime.caching.cache_type import CacheType
from streamlit.runtime.caching.cache_utils import (
    Cache,
    CachedFuncInfo,
    make_cached_func_wrapper,
    ttl_to_seconds,
)
from streamlit.runtime.caching.cached_message_replay import (
    CachedMessageReplayContext,
    CachedResult,
    ElementMsgData,
    MsgData,
    MultiCacheResults,
)
from streamlit.runtime.caching.storage import (
    CacheStorage,
    CacheStorageContext,
    CacheStorageKeyNotFoundError,
    CacheStorageManager,
)
from streamlit.runtime.metrics_util import gather_metrics
from streamlit.runtime.scriptrunner.script_run_context import get_script_run_ctx
from streamlit.runtime.stats import CacheStat, CacheStatsProvider

_LOGGER = get_logger(__name__)

# Streamlit directory where persisted @st.cache_data objects live.
# (This is the same directory that @st.cache persisted objects live.
# But @st.cache_data uses a different extension, so they don't overlap.)
_CACHE_DIR_NAME = "cache"

# The extension for our persisted @st.cache_data objects.
# (`@st.cache_data` was originally called `@st.memo`)
_CACHED_FILE_EXTENSION = "memo"

CACHE_DATA_MESSAGE_REPLAY_CTX = CachedMessageReplayContext(CacheType.DATA)

# The cache persistence options we support: "disk" or None
CachePersistType: TypeAlias = Union[Literal["disk"], None]


class CachedDataFuncInfo(CachedFuncInfo):
    """Implements the CachedFuncInfo interface for @st.cache_data"""

    def __init__(
        self,
        func: types.FunctionType,
        show_spinner: bool | str,
        persist: CachePersistType,
        max_entries: int | None,
        ttl: float | timedelta | None,
        allow_widgets: bool,
    ):
        super().__init__(
            func,
            show_spinner=show_spinner,
            allow_widgets=allow_widgets,
        )
        self.persist = persist
        self.max_entries = max_entries
        self.ttl = ttl

        self.validate_params()

    @property
    def cache_type(self) -> CacheType:
        return CacheType.DATA

    @property
    def cached_message_replay_ctx(self) -> CachedMessageReplayContext:
        return CACHE_DATA_MESSAGE_REPLAY_CTX

    @property
    def display_name(self) -> str:
        """A human-readable name for the cached function"""
        return f"{self.func.__module__}.{self.func.__qualname__}"

    def get_function_cache(self, function_key: str) -> Cache:
        return _data_caches.get_cache(
            key=function_key,
            persist=self.persist,
            max_entries=self.max_entries,
            ttl=self.ttl,
            display_name=self.display_name,
            allow_widgets=self.allow_widgets,
        )

    def validate_params(self):
        """ "
        Validate the params passed to @st.cache_data are compatible with cache storage
        """
        _data_caches.validate_cache_params(
            function_name=self.func.__name__,
            persist=self.persist,
            max_entries=self.max_entries,
            ttl=self.ttl,
        )


class DataCaches(CacheStatsProvider):
    """Manages all DataCache instances"""

    def __init__(self):
        self._caches_lock = threading.Lock()
        self._function_caches: dict[str, DataCache] = {}

    def get_cache(
        self,
        key: str,
        persist: CachePersistType,
        max_entries: int | None,
        ttl: int | float | timedelta | None,
        display_name: str,
        allow_widgets: bool,
    ) -> DataCache:
        """Return the mem cache for the given key.

        If it doesn't exist, create a new one with the given params.
        """

        ttl_seconds = ttl_to_seconds(ttl, allow_none=True)

        # Get the existing cache, if it exists, and validate that its params
        # haven't changed.
        with self._caches_lock:
            cache = self._function_caches.get(key)
            # Fixme: [Karen] instead of comparing key,
            #  we can override __eq__ in DataCache
            if (
                cache is not None
                and cache.ttl_seconds == ttl_seconds
                and cache.max_entries == max_entries
                and cache.persist == persist
            ):
                return cache

            # Create a new cache object and put it in our dict
            _LOGGER.debug(
                "Creating new DataCache (key=%s, persist=%s, max_entries=%s, ttl=%s)",
                key,
                persist,
                max_entries,
                ttl,
            )

            cache_context = self.create_cache_storage_context(
                function_key=key,
                ttl_seconds=ttl_seconds,
                max_entries=max_entries,
                persist=persist,
            )
            cache_storage_manager = self.get_storage_manager()
            storage = cache_storage_manager.create(cache_context)

            cache = DataCache(
                key=key,
                storage=storage,
                persist=persist,
                max_entries=max_entries,
                ttl_seconds=ttl_seconds,
                display_name=display_name,
                allow_widgets=allow_widgets,
            )
            # TODO [Karen]: Since we override old function cache with new one, we should
            # also think about connected storage resource deallocation/close connection,
            # before we override it with new one
            self._function_caches[key] = cache
            return cache

    def clear_all(self) -> None:
        """Clear all in-memory and on-disk caches."""
        with self._caches_lock:
            # TODO: [Karen] We should also think about call storage.close() to
            #  release resources
            try:
                # Try to remove with optimal way, if not possible fallback to
                # remove all available storages one by one
                self.get_storage_manager().clear_all()
            except NotImplementedError:
                for data_cache in self._function_caches.values():
                    data_cache.clear()
            # TODO: [Karen] We should also think about call storage.close() here too.
            self._function_caches = {}

    def get_stats(self) -> list[CacheStat]:
        with self._caches_lock:
            # Shallow-clone our caches. We don't want to hold the global
            # lock during stats-gathering.
            function_caches = self._function_caches.copy()

        stats: list[CacheStat] = []
        for cache in function_caches.values():
            stats.extend(cache.get_stats())
        return stats

    def validate_cache_params(
        self,
        function_name: str,
        persist: CachePersistType,
        max_entries: int | None,
        ttl: int | float | timedelta | None,
    ) -> None:
        """Validate that the cache params are valid for given storage."""

        ttl_seconds = ttl_to_seconds(ttl, allow_none=True)

        cache_context = self.create_cache_storage_context(
            function_key="DUMMY_KEY",  # Pass dummy key, since we don't have function
            # key yet, and we use context to validate params
            ttl_seconds=ttl_seconds,
            max_entries=max_entries,
            persist=persist,
        )
        self.get_storage_manager().check_context(cache_context, function_name)

    def create_cache_storage_context(
        self,
        function_key: str,
        persist: CachePersistType,
        ttl_seconds: float | None,
        max_entries: int | None,
    ) -> CacheStorageContext:

        return CacheStorageContext(
            function_key=function_key,
            ttl_seconds=ttl_seconds,
            max_entries=max_entries,
            persist=persist,
        )

    def get_storage_manager(self) -> CacheStorageManager:
        return runtime.get_instance().cache_storage_manager


# Singleton DataCaches instance
_data_caches = DataCaches()


def get_data_cache_stats_provider() -> CacheStatsProvider:
    """Return the StatsProvider for all @st.cache_data functions."""
    return _data_caches


class CacheDataAPI:
    """Implements the public st.cache_data API: the @st.cache_data decorator, and
    st.cache_data.clear().
    """

    def __init__(
        self, decorator_metric_name: str, deprecation_warning: str | None = None
    ):
        """Create a CacheDataAPI instance.

        Parameters
        ----------
        decorator_metric_name
            The metric name to record for decorator usage. `@st.experimental_memo` is
            deprecated, but we're still supporting it and tracking its usage separately
            from `@st.cache_data`.

        deprecation_warning
            An optional deprecation warning to show when the API is accessed.
        """

        # Parameterize the decorator metric name.
        # (Ignore spurious mypy complaints - https://github.com/python/mypy/issues/2427)
        self._decorator = gather_metrics(  # type: ignore[assignment]
            decorator_metric_name, self._decorator
        )
        self._deprecation_warning = deprecation_warning

    # Type-annotate the decorator function.
    # (See https://mypy.readthedocs.io/en/stable/generics.html#decorator-factories)
    F = TypeVar("F", bound=Callable[..., Any])

    # Bare decorator usage
    @overload
    def __call__(self, func: F) -> F:
        ...

    # Decorator with arguments
    @overload
    def __call__(
        self,
        *,
        ttl: float | timedelta | None = None,
        max_entries: int | None = None,
        show_spinner: bool | str = True,
        persist: CachePersistType | bool = None,
        experimental_allow_widgets: bool = False,
    ) -> Callable[[F], F]:
        ...

    def __call__(
        self,
        func: F | None = None,
        *,
        ttl: float | timedelta | None = None,
        max_entries: int | None = None,
        show_spinner: bool | str = True,
        persist: CachePersistType | bool = None,
        experimental_allow_widgets: bool = False,
    ):
        return self._decorator(
            func,
            ttl=ttl,
            max_entries=max_entries,
            persist=persist,
            show_spinner=show_spinner,
            experimental_allow_widgets=experimental_allow_widgets,
        )

    def _decorator(
        self,
        func: F | None = None,
        *,
        ttl: float | timedelta | None,
        max_entries: int | None,
        show_spinner: bool | str,
        persist: CachePersistType | bool,
        experimental_allow_widgets: bool,
    ):
        """Decorator to cache functions that return data (e.g. dataframe transforms, database queries, ML inference).

        Cached objects are stored in "pickled" form, which means that the return
        value of a cached function must be pickleable. Each caller of the cached
        function gets its own copy of the cached data.

        You can clear a function's cache with ``func.clear()`` or clear the entire
        cache with ``st.cache_data.clear()``.

        To cache global resources, use ``st.cache_resource`` instead. Learn more
        about caching at https://docs.streamlit.io/library/advanced-features/caching.

        Parameters
        ----------
        func : callable
            The function to cache. Streamlit hashes the function's source code.

        ttl : float or timedelta or None
            The maximum number of seconds to keep an entry in the cache, or
            None if cache entries should not expire. The default is None.
            Note that ttl is incompatible with ``persist="disk"`` - ``ttl`` will be
            ignored if ``persist`` is specified.

        max_entries : int or None
            The maximum number of entries to keep in the cache, or None
            for an unbounded cache. (When a new entry is added to a full cache,
            the oldest cached entry will be removed.) The default is None.

        show_spinner : boolean
            Enable the spinner. Default is True to show a spinner when there is
            a cache miss.

        persist : str or boolean or None
            Optional location to persist cached data to. Passing "disk" (or True)
            will persist the cached data to the local disk. None (or False) will disable
            persistence. The default is None.

        experimental_allow_widgets : boolean
            Allow widgets to be used in the cached function. Defaults to False.
            Support for widgets in cached functions is currently experimental.
            Setting this parameter to True may lead to excessive memory use since the
            widget value is treated as an additional input parameter to the cache.
            We may remove support for this option at any time without notice.

        Example
        -------
        >>> import streamlit as st
        >>>
        >>> @st.cache_data
        ... def fetch_and_clean_data(url):
        ...     # Fetch data from URL here, and then clean it up.
        ...     return data
        ...
        >>> d1 = fetch_and_clean_data(DATA_URL_1)
        >>> # Actually executes the function, since this is the first time it was
        >>> # encountered.
        >>>
        >>> d2 = fetch_and_clean_data(DATA_URL_1)
        >>> # Does not execute the function. Instead, returns its previously computed
        >>> # value. This means that now the data in d1 is the same as in d2.
        >>>
        >>> d3 = fetch_and_clean_data(DATA_URL_2)
        >>> # This is a different URL, so the function executes.

        To set the ``persist`` parameter, use this command as follows:

        >>> import streamlit as st
        >>>
        >>> @st.cache_data(persist="disk")
        ... def fetch_and_clean_data(url):
        ...     # Fetch data from URL here, and then clean it up.
        ...     return data

        By default, all parameters to a cached function must be hashable.
        Any parameter whose name begins with ``_`` will not be hashed. You can use
        this as an "escape hatch" for parameters that are not hashable:

        >>> import streamlit as st
        >>>
        >>> @st.cache_data
        ... def fetch_and_clean_data(_db_connection, num_rows):
        ...     # Fetch data from _db_connection here, and then clean it up.
        ...     return data
        ...
        >>> connection = make_database_connection()
        >>> d1 = fetch_and_clean_data(connection, num_rows=10)
        >>> # Actually executes the function, since this is the first time it was
        >>> # encountered.
        >>>
        >>> another_connection = make_database_connection()
        >>> d2 = fetch_and_clean_data(another_connection, num_rows=10)
        >>> # Does not execute the function. Instead, returns its previously computed
        >>> # value - even though the _database_connection parameter was different
        >>> # in both calls.

        A cached function's cache can be procedurally cleared:

        >>> import streamlit as st
        >>>
        >>> @st.cache_data
        ... def fetch_and_clean_data(_db_connection, num_rows):
        ...     # Fetch data from _db_connection here, and then clean it up.
        ...     return data
        ...
        >>> fetch_and_clean_data.clear()
        >>> # Clear all cached entries for this function.

        """

        # Parse our persist value into a string
        persist_string: CachePersistType
        if persist is True:
            persist_string = "disk"
        elif persist is False:
            persist_string = None
        else:
            persist_string = persist

        if persist_string not in (None, "disk"):
            # We'll eventually have more persist options.
            raise StreamlitAPIException(
                f"Unsupported persist option '{persist}'. Valid values are 'disk' or None."
            )

        self._maybe_show_deprecation_warning()

        def wrapper(f):
            return make_cached_func_wrapper(
                CachedDataFuncInfo(
                    func=f,
                    persist=persist_string,
                    show_spinner=show_spinner,
                    max_entries=max_entries,
                    ttl=ttl,
                    allow_widgets=experimental_allow_widgets,
                )
            )

        if func is None:
            return wrapper

        return make_cached_func_wrapper(
            CachedDataFuncInfo(
                func=cast(types.FunctionType, func),
                persist=persist_string,
                show_spinner=show_spinner,
                max_entries=max_entries,
                ttl=ttl,
                allow_widgets=experimental_allow_widgets,
            )
        )

    @gather_metrics("clear_data_caches")
    def clear(self) -> None:
        """Clear all in-memory and on-disk data caches."""
        self._maybe_show_deprecation_warning()
        _data_caches.clear_all()

    def _maybe_show_deprecation_warning(self):
        """If the API is being accessed with the deprecated `st.experimental_memo` name,
        show a deprecation warning.
        """
        if self._deprecation_warning is not None:
            show_deprecation_warning(self._deprecation_warning)


class DataCache(Cache):
    """Manages cached values for a single st.cache_data function."""

    def __init__(
        self,
        key: str,
        storage: CacheStorage,
        persist: CachePersistType,
        max_entries: int | None,
        ttl_seconds: float | None,
        display_name: str,
        allow_widgets: bool = False,
    ):
        super().__init__()
        self.key = key
        self.display_name = display_name
        self.storage = storage
        self.ttl_seconds = ttl_seconds
        self.max_entries = max_entries
        self.persist = persist
        self.allow_widgets = allow_widgets

    # TODO [Karen] think about this max_entries live here or in the storage

    def get_stats(self) -> list[CacheStat]:
        stats: list[CacheStat] = []

        for item_byte_length in self.storage.get_stats():
            stats.append(
                CacheStat(
                    category_name="st_cache_data",
                    cache_name=self.display_name,
                    byte_length=item_byte_length,
                )
            )
        return stats

    def read_result(self, key: str) -> CachedResult:
        """Read a value and messages from the cache. Raise `CacheKeyNotFoundError`
        if the value doesn't exist, and `CacheError` if the value exists but can't
        be unpickled.
        """
        try:
            pickled_entry = self.storage.get(key)
        except CacheStorageKeyNotFoundError as e:
            raise CacheKeyNotFoundError(str(e)) from e

        try:
            entry = pickle.loads(pickled_entry)
            if not isinstance(entry, MultiCacheResults):
                # Loaded an old cache file format, remove it and let the caller
                # rerun the function.
                self.storage.delete(key)
                raise CacheKeyNotFoundError()

            ctx = get_script_run_ctx()
            if not ctx:
                raise CacheKeyNotFoundError()

            widget_key = entry.get_current_widget_key(ctx, CacheType.DATA)
            if widget_key in entry.results:
                return entry.results[widget_key]
            else:
                raise CacheKeyNotFoundError()
        except pickle.UnpicklingError as exc:
            raise CacheError(f"Failed to unpickle {key}") from exc

    @gather_metrics("_cache_data_object")
    def write_result(self, key: str, value: Any, messages: list[MsgData]) -> None:
        """Write a value and associated messages to the cache.
        The value must be pickleable.
        """
        ctx = get_script_run_ctx()
        if ctx is None:
            return

        main_id = st._main.id
        sidebar_id = st.sidebar.id

        if self.allow_widgets:
            widgets = {
                msg.widget_metadata.widget_id
                for msg in messages
                if isinstance(msg, ElementMsgData) and msg.widget_metadata is not None
            }
        else:
            widgets = set()

        multi_cache_results: MultiCacheResults | None = None

        # Try to find in mem cache, falling back to disk, then falling back
        # to a new result instance
        try:
            multi_cache_results = self._read_multi_results_from_storage(key)
        except (CacheKeyNotFoundError, pickle.UnpicklingError):
            # TODO: [Karen] move pickle.UnpicklingError to
            #  _read_multi_results_from_storage
            pass

        if multi_cache_results is None:
            multi_cache_results = MultiCacheResults(widget_ids=widgets, results={})
        multi_cache_results.widget_ids.update(widgets)
        widget_key = multi_cache_results.get_current_widget_key(ctx, CacheType.DATA)

        result = CachedResult(value, messages, main_id, sidebar_id)
        multi_cache_results.results[widget_key] = result

        try:
            pickled_entry = pickle.dumps(multi_cache_results)
        except (pickle.PicklingError, TypeError) as exc:
            raise CacheError(f"Failed to pickle {key}") from exc

        self.storage.set(key, pickled_entry)

    def _clear(self) -> None:
        self.storage.clear()

    def _read_multi_results_from_storage(self, key: str) -> MultiCacheResults:
        """Look up the results from storage and ensure it has the right type.

        Raises a `CacheKeyNotFoundError` if the key has no entry, or if the
        entry is malformed.
        """
        try:
            pickled = self.storage.get(key)
        except CacheStorageKeyNotFoundError as e:
            raise CacheKeyNotFoundError(str(e)) from e

        maybe_results = pickle.loads(pickled)

        if isinstance(maybe_results, MultiCacheResults):
            return maybe_results
        else:
            self.storage.delete(key)
            raise CacheKeyNotFoundError()
