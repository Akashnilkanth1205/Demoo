# Copyright (c) Streamlit Inc. (2018-2022) Snowflake Inc. (2022-2024)
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

import streamlit as st


def display():

    # Provide links to lower and higher level pages in sidebar
    # It can be functionized if you don't want to write every time.
    st.sidebar.page_link("app.py", label="🏠 Main")

    st.sidebar.title("Nested Multipage App")
    st.sidebar.header("This is a nested multipage example.")
    st.sidebar.write(
        "We will make a 2 level nested app. It can be extended as much as you want."
    )

    st.sidebar.page_link("pages/cookbook.py", label="◀️ Cookbook")

    # main page
    st.title("Why don't you explain about your sub-pages here?")

    st.header("Applications.")
    st.write("Describe your app here, and guide your users to the app pages.")
    st.sidebar.page_link("pages/cookbook/multipages/apps.py", label="▶️ Apps")

    st.header("Blog.")
    st.write("Describe your blog.")
    st.sidebar.page_link("pages/cookbook/multipages/blog.py", label="▶️ Blog")
