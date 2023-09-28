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

import hashlib
import pathlib
import tempfile
import textwrap
import traceback
from typing import Any, Sequence
from unittest.mock import MagicMock

from streamlit import source_util
from streamlit.proto.WidgetStates_pb2 import WidgetStates
from streamlit.runtime import Runtime
from streamlit.runtime.caching.storage.dummy_cache_storage import (
    MemoryCacheStorageManager,
)
from streamlit.runtime.media_file_manager import MediaFileManager
from streamlit.runtime.memory_media_file_storage import MemoryMediaFileStorage
from streamlit.runtime.state.session_state import SessionState
from streamlit.testing.v1.element_tree import (
    Block,
    Caption,
    Checkbox,
    Code,
    ColorPicker,
    DateInput,
    Divider,
    ElementList,
    ElementTree,
    Exception,
    Header,
    Latex,
    Markdown,
    Multiselect,
    Node,
    NumberInput,
    Radio,
    Selectbox,
    SelectSlider,
    Slider,
    Subheader,
    Text,
    TextArea,
    TextInput,
    TimeInput,
    Title,
    WidgetList,
)
from streamlit.testing.v1.local_script_runner import LocalScriptRunner
from streamlit.testing.v1.util import patch_config_options

TMP_DIR = tempfile.TemporaryDirectory()


class AppTest:
    def __init__(self, script_path: str, default_timeout: float):
        self._script_path = script_path
        self.default_timeout = default_timeout
        self.session_state = SessionState()
        self.query_params = {}

        tree = ElementTree()
        tree._runner = self
        self._tree = tree

    @classmethod
    def from_string(cls, script: str, default_timeout: float = 3) -> AppTest:
        """Create a runner for a script with the contents from a string.

        Useful for testing short scripts that fit comfortably as an inline
        string in the test itself, without having to create a separate file
        for it.

        `default_timeout` is the default time in seconds before a script is
        timed out, if not overridden for an individual `.run()` call.
        """
        hasher = hashlib.md5(bytes(script, "utf-8"))
        script_name = hasher.hexdigest()

        path = pathlib.Path(TMP_DIR.name, script_name)
        aligned_script = textwrap.dedent(script)
        path.write_text(aligned_script)
        return AppTest(str(path), default_timeout=default_timeout)

    @classmethod
    def from_file(cls, script_path: str, default_timeout: float = 3) -> AppTest:
        """Create a runner for the script with the given name, for testing.

        `default_timeout` is the default time in seconds before a script is
        timed out, if not overridden for an individual `.run()` call.
        """
        stack = traceback.StackSummary.extract(traceback.walk_stack(None))
        filepath = pathlib.Path(stack[1].filename)
        full_path = filepath.parent / script_path
        return AppTest(str(full_path), default_timeout=default_timeout)

    def _run(
        self,
        widget_state: WidgetStates | None = None,
        timeout: float | None = None,
    ) -> AppTest:
        """Run the script, and parse the output messages for querying
        and interaction.

        Timeout is in seconds, or None to use the default timeout of the runner.
        """
        if timeout is None:
            timeout = self.default_timeout

        # setup
        mock_runtime = MagicMock(spec=Runtime)
        mock_runtime.media_file_mgr = MediaFileManager(
            MemoryMediaFileStorage("/mock/media")
        )
        mock_runtime.cache_storage_manager = MemoryCacheStorageManager()
        Runtime._instance = mock_runtime
        with source_util._pages_cache_lock:
            self.saved_cached_pages = source_util._cached_pages
            source_util._cached_pages = None

        with patch_config_options({"runner.postScriptGC": False}):
            script_runner = LocalScriptRunner(self._script_path, self.session_state)
            self._tree = script_runner.run(widget_state, self.query_params, timeout)
            self._tree._runner = self

        # teardown
        with source_util._pages_cache_lock:
            source_util._cached_pages = self.saved_cached_pages
        Runtime._instance = None

        return self

    def run(self, timeout: float | None = None) -> AppTest:
        """Run the script, and parse the output messages for querying
        and interaction.

        Timeout is in seconds, or None to use the default timeout of the runner.
        """
        return self._tree.run(timeout)

    @property
    def main(self) -> Block:
        return self._tree.main

    @property
    def caption(self) -> ElementList[Caption]:
        return self._tree.caption

    @property
    def checkbox(self) -> WidgetList[Checkbox]:
        return self._tree.checkbox

    @property
    def code(self) -> ElementList[Code]:
        return self._tree.code

    @property
    def color_picker(self) -> WidgetList[ColorPicker]:
        return self._tree.color_picker

    @property
    def date_input(self) -> WidgetList[DateInput]:
        return self._tree.date_input

    @property
    def divider(self) -> ElementList[Divider]:
        return self._tree.divider

    @property
    def exception(self) -> ElementList[Exception]:
        return self._tree.exception

    @property
    def header(self) -> ElementList[Header]:
        return self._tree.header

    @property
    def latex(self) -> ElementList[Latex]:
        return self._tree.latex

    @property
    def markdown(self) -> ElementList[Markdown]:
        return self._tree.markdown

    @property
    def multiselect(self) -> WidgetList[Multiselect[Any]]:
        return self._tree.multiselect

    @property
    def number_input(self) -> WidgetList[NumberInput]:
        return self._tree.number_input

    @property
    def radio(self) -> WidgetList[Radio[Any]]:
        return self._tree.radio

    @property
    def select_slider(self) -> WidgetList[SelectSlider[Any]]:
        return self._tree.select_slider

    @property
    def selectbox(self) -> WidgetList[Selectbox[Any]]:
        return self._tree.selectbox

    @property
    def slider(self) -> WidgetList[Slider[Any]]:
        return self._tree.slider

    @property
    def subheader(self) -> ElementList[Subheader]:
        return self._tree.subheader

    @property
    def text(self) -> ElementList[Text]:
        return self._tree.text

    @property
    def text_area(self) -> WidgetList[TextArea]:
        return self._tree.text_area

    @property
    def text_input(self) -> WidgetList[TextInput]:
        return self._tree.text_input

    @property
    def time_input(self) -> WidgetList[TimeInput]:
        return self._tree.time_input

    @property
    def title(self) -> ElementList[Title]:
        return self._tree.title

    def __len__(self) -> int:
        return len(self._tree)

    def __iter__(self):
        yield from self._tree

    def __getitem__(self, idx: int) -> Node:
        return self._tree[idx]

    def get(self, element_type: str) -> Sequence[Node]:
        return self._tree.get(element_type)
