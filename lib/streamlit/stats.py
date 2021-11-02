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

import typing
from abc import abstractmethod
from typing import List

import tornado.web


class CacheStat(typing.NamedTuple):
    """Describes a single cache entry.

    Properties
    ----------
    category_name : str
        A human-readable name for the cache "category" that the entry belongs
        to - e.g. "st.memo", "session_state", etc.
    cache_name : str
        A human-readable name for cache instance that the entry belongs to.
        For "st.memo" and other function decorator caches, this might be the
        name of the cached function. If the cache category doesn't have
        multiple separate cache instances, this can just be the empty string.
    byte_length : int
        The entry's memory footprint in bytes.
    """

    category_name: str
    cache_name: str
    byte_length: int

    def to_metric_str(self) -> str:
        return 'cache_memory_bytes{cache_type="%s",cache="%s"} %s' % (
            self.category_name,
            self.cache_name,
            self.byte_length,
        )


class CacheStatsProvider:
    @abstractmethod
    def get_stats(self) -> List[CacheStat]:
        raise NotImplementedError


class StatsManager:
    def __init__(self):
        self._cache_stats_providers: List[CacheStatsProvider] = []

    def register_provider(self, provider: CacheStatsProvider) -> None:
        """Register a CacheStatsProvider with the manager.
        This function is not thread-safe. Call it immediately after
        creation.
        """
        self._cache_stats_providers.append(provider)

    def get_stats(self) -> List[CacheStat]:
        """Return a list containing all stats from each registered provider."""
        all_stats: List[CacheStat] = []
        for provider in self._cache_stats_providers:
            all_stats.extend(provider.get_stats())
        return all_stats


class StatsHandler(tornado.web.RequestHandler):
    def initialize(self, stats_manager: StatsManager) -> None:
        self._manager = stats_manager

    def set_default_headers(self):
        # Avoid a circular import
        from streamlit.server.routes import allow_cross_origin_requests

        if allow_cross_origin_requests():
            self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Content-Type", "application/openmetrics-text")

    def options(self):
        """/OPTIONS handler for preflight CORS checks."""
        self.set_status(204)
        self.finish()

    def get(self) -> None:
        metric_type = "# TYPE cache_memory_bytes gauge"
        metric_unit = "# UNIT cache_memory_bytes bytes"
        metric_help = "# HELP Total memory consumed by a cache."
        openmetrics_eof = "# EOF\n"

        # Format: header, stats, EOF
        stats = [metric_type, metric_unit, metric_help]
        stats.extend(stat.to_metric_str() for stat in self._manager.get_stats())
        stats.append(openmetrics_eof)
        self.write("\n".join(stats))
        self.set_status(200)
