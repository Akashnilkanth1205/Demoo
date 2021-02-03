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

import streamlit as st

options = ("male", "female")
i1 = st.multiselect("selectbox 1", options)
st.text(f"value 1: {i1}")

i2 = st.multiselect("selectbox 2", options, format_func=lambda x: x.capitalize())
st.text(f"value 2: {i2}")

i3 = st.multiselect("selectbox 3", [])
st.text(f"value 3: {i3}")

i4 = st.multiselect("selectbox 4", ["coffee", "tea", "water"], ["tea", "water"])
st.text(f"value 4: {i4}")

i5 = st.multiselect(
    "selectbox 5",
    list(
        map(
            lambda x: f"{x} I am a ridiculously long string to have in a multiselect, so perhaps I should just not wrap and go to the next line.",
            range(5),
        )
    ),
)
st.text(f"value 5: {i5}")

# st.session_state() can only run in streamlit
if st._is_running_with_streamlit:
    state = st.beta_session_state(multiselect_changed=False)

    def change_handler(new_text):
        state.multiselect_changed = True

    i6 = st.multiselect("selectbox 6", options, on_change=change_handler)
    st.text(f"value 6: {i6}")
    st.text("Multiselect Changed: %s" % state.multiselect_changed)
