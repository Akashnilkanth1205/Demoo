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

from streamlit.testing.v1 import AppTest


def test_smoke():
    at = AppTest.from_string(
        """
        import streamlit as st

        st.radio("radio", options=["a", "b", "c"], key="r")
        st.radio("default index", options=["a", "b", "c"], index=2)
        """
    ).run()
    assert at.radio
    assert at.radio[0].value == "a"
    assert at.radio(key="r").value == "a"
    assert at.radio.values == ["a", "c"]

    r = at.radio[0].set_value("b")
    assert r.index == 1
    assert r.value == "b"
    at = r.run()
    assert at.radio[0].value == "b"
    assert at.radio.values == ["b", "c"]


def test_checkbox():
    script = AppTest.from_string(
        """
        import streamlit as st

        st.checkbox("defaults")
        st.checkbox("defaulted on", True)
        """,
    )
    sr = script.run()
    assert sr.checkbox
    assert sr.checkbox.values == [False, True]

    sr.checkbox[0].check().run()
    assert sr.checkbox[0].value == True
    assert sr.checkbox[1].value == True

    sr.checkbox[1].uncheck().run()
    assert sr.checkbox[0].value == True
    assert sr.checkbox[1].value == False


def test_from_file():
    script = AppTest.from_file("../test_data/widgets_script.py")
    script.run()


def test_query_params():
    sr = AppTest.from_string(
        """
        import streamlit as st

        st.write(st.experimental_get_query_params())
        """
    ).run()
    assert sr.get("json")[0].proto.json.body == "{}"
    sr.query_params["foo"] = 5
    sr.query_params["bar"] = "baz"
    sr.run()
    assert sr.get("json")[0].proto.json.body == '{"foo": ["5"], "bar": ["baz"]}'
