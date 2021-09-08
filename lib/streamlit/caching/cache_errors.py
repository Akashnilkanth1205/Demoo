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

import types

from streamlit.errors import StreamlitAPIWarning


class CacheKeyNotFoundError(Exception):
    pass


class CacheError(Exception):
    pass


class CachedStFunctionWarning(StreamlitAPIWarning):
    def __init__(self, st_func_name, cached_func):
        msg = self._get_message(st_func_name, cached_func)
        super(CachedStFunctionWarning, self).__init__(msg)

    def _get_message(self, st_func_name, cached_func):
        args = {
            "st_func_name": "`st.%s()` or `st.write()`" % st_func_name,
            "func_name": _get_cached_func_name_md(cached_func),
        }

        return (
            """
Your script uses %(st_func_name)s to write to your Streamlit app from within
some cached code at %(func_name)s. This code will only be called when we detect
a cache "miss", which can lead to unexpected results.

How to fix this:
* Move the %(st_func_name)s call outside %(func_name)s.
* Or, if you know what you're doing, use `@st.cache(suppress_st_warning=True)`
to suppress the warning.
            """
            % args
        ).strip("\n")


def _get_cached_func_name_md(func: types.FunctionType) -> str:
    """Get markdown representation of the function name."""
    if hasattr(func, "__name__"):
        return "`%s()`" % func.__name__
    else:
        return "a cached function"
