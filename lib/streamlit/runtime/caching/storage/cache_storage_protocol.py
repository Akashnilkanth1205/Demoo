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

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass

from typing_extensions import Literal, Protocol


class CacheStorageError(Exception):
    """Base exception raised by the cache storage"""


class CacheStorageKeyNotFoundError(CacheStorageError):
    """Raised when the key is not found in the cache storage"""


@dataclass(frozen=True)
class CacheStorageContext:
    """
    Context passed to the cache storage during initialization
    This is the normalized parameters that are passed to CacheStorageManager.create()
    method.

    Parameters
    ----------
    function_key: str
        A hash computed based on function name and source code decorated
        by st.cache_data

    ttl_seconds : float or None
        The time-to-live for the keys in storage, in seconds. If None, the entry
        will never expire.

    max_entries : int or None
        The maximum number of entries to store in the cache storage.
        If None, the cache storage will not limit the number of entries.

    persist : Literal["disk"] or None
        The persistence mode for the cache storage.
        Legacy parameter, that used in Streamlit current cache storage implementation.
        Could be ignored by cache storage implementation, if storage does not support
        persistence or it persistent by default.
    """

    function_key: str
    ttl_seconds: float | None = None
    max_entries: int | None = None
    persist: Literal["disk"] | None = None


class CacheStorage(Protocol):
    @abstractmethod
    def get(self, key: str) -> bytes:
        """
        Returns the stored value for the key or raises
        a CacheStorageKeyNotFoundError if the key is not found
        """
        raise NotImplementedError

    @abstractmethod
    def set(self, key: str, value: bytes) -> None:
        """Sets the value for a given key"""
        raise NotImplementedError

    @abstractmethod
    def delete(self, key: str) -> None:
        """Delete a given key"""
        raise NotImplementedError

    @abstractmethod
    def clear(self) -> None:
        """Remove all keys for the storage"""
        raise NotImplementedError

    def close(self) -> None:
        """
        Closes the cache storage, it is optional to implement, and should be used
        to close open resources, before we delete the storage instance.
        e.g. close the database connection etc.
        """
        pass


class CacheStorageManager(Protocol):
    @abstractmethod
    def create(self, context: CacheStorageContext) -> CacheStorage:
        """
        Creates a new cache storage instance
        Please note that the ttl, max_entries and other context fields are specific
        for whole storage, not for individual key.
        """
        raise NotImplementedError

    def clear_all(self) -> None:
        """
        Remove everything what possible from the cache storages in optimal way.
        meaningful default behaviour is to raise NotImplementedError, so this is not
        abstractmethod.

        Cache data API will fall back to remove all available storages one by one
        via storage.clear() method if clear_all raises NotImplementedError.
        """
        raise NotImplementedError

    def check_context(self, context: CacheStorageContext, function_name: str) -> None:
        """
        Checks if the context is valid for the storage manager.
        This method should not return anything, but log message or raise an exception
        if the context is invalid.

        In case of raising an exception, we not handle it and let the exception to be
        raised.

        check_context is called only once at the moment of creating cache_data
        decorator for specific function, so it is not called for every cache hit.

        Parameters
        ----------
        context: CacheStorageContext
            The context to check for the storage manager, dummy function_key in context
            will be used, since it is not computed at the point of calling this method.
        function_name: str
            The name of the function that is decorated by st.cache_data, could be used
            in the error log message.
        """

        pass
