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

# Explicitly re-export public symbols
from streamlit.runtime.state.safe_session_state import (
    SafeSessionState as SafeSessionState,
)

from streamlit.runtime.state.session_state import (
    SessionState as SessionState,
    WidgetCallback as WidgetCallback,
    WidgetArgs as WidgetArgs,
    WidgetKwargs as WidgetKwargs,
    SessionStateStatProvider as SessionStateStatProvider,
    SCRIPT_RUN_WITHOUT_ERRORS_KEY as SCRIPT_RUN_WITHOUT_ERRORS_KEY,
)

from streamlit.runtime.state.session_state_proxy import (
    SessionStateProxy as SessionStateProxy,
    get_session_state as get_session_state,
)

from streamlit.runtime.state.widgets import (
    coalesce_widget_states as coalesce_widget_states,
    register_widget as register_widget,
    NoValue as NoValue,
)
