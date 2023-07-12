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
import time

import streamlit as st

status = st.status_panel(behavior="autocollapse")

with status.stage("🤔 Creating files...") as s:
    text = st.text("Doing a thing...")
    time.sleep(3)
    text.text("Done!")
    s.set_label("✅ Created!")

with status.stage("🤔 Reticulating splines...") as s:
    text = st.text("Doing a thing...")
    time.sleep(3)
    text.text("Done!")
    s.set_label("✅ Reticulated!")

with status.stage("🤔 Watering dromedaries...") as s:
    text = st.text("Doing a thing...")
    time.sleep(3)
    text.text("Done!")
    s.set_label("✅ Watered!")
