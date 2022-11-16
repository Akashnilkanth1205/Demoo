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

import os
import pathlib
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Union, overload

from streamlit.proto.Block_pb2 import Block as BlockProto
from streamlit.proto.ClientState_pb2 import ClientState
from streamlit.proto.Delta_pb2 import Delta
from streamlit.proto.Element_pb2 import Element as ElementProto
from streamlit.proto.ForwardMsg_pb2 import ForwardMsg
from streamlit.proto.Radio_pb2 import Radio as RadioProto
from streamlit.proto.Text_pb2 import Text as TextProto
from streamlit.proto.WidgetStates_pb2 import WidgetState, WidgetStates
from streamlit.runtime.forward_msg_queue import ForwardMsgQueue
from streamlit.runtime.scriptrunner import RerunData, ScriptRunner, ScriptRunnerEvent
from streamlit.runtime.state.session_state import SessionState
from streamlit.runtime.uploaded_file_manager import UploadedFileManager


class TestScriptRunner(ScriptRunner):
    """Subclasses ScriptRunner to provide some testing features."""

    # PyTest is unable to collect Test classes with __init__,
    # and issues PytestCollectionWarning: cannot collect test class
    # Since class TestScriptRunner is a helper class,
    # there is no need for class TestScriptRunner to be collected by PyTest
    # To prevent PytestCollectionWarning we set __test__ property to False
    __test__ = False

    def __init__(self, script_path: str):
        """Initializes the ScriptRunner for the given script_name"""
        # DeltaGenerator deltas will be enqueued into self.forward_msg_queue.
        self.forward_msg_queue = ForwardMsgQueue()

        super().__init__(
            session_id="test session id",
            main_script_path=script_path,
            client_state=ClientState(),
            session_state=SessionState(),
            uploaded_file_mgr=UploadedFileManager(),
            initial_rerun_data=RerunData(),
            user_info={"email": "test@test.com"},
        )

        # Accumulates uncaught exceptions thrown by our run thread.
        self.script_thread_exceptions: List[BaseException] = []

        # Accumulates all ScriptRunnerEvents emitted by us.
        self.events: List[ScriptRunnerEvent] = []
        self.event_data: List[Any] = []

        def record_event(
            sender: Optional[ScriptRunner], event: ScriptRunnerEvent, **kwargs
        ) -> None:
            # Assert that we're not getting unexpected `sender` params
            # from ScriptRunner.on_event
            assert (
                sender is None or sender == self
            ), "Unexpected ScriptRunnerEvent sender!"

            self.events.append(event)
            self.event_data.append(kwargs)

            # Send ENQUEUE_FORWARD_MSGs to our queue
            if event == ScriptRunnerEvent.ENQUEUE_FORWARD_MSG:
                forward_msg = kwargs["forward_msg"]
                self.forward_msg_queue.enqueue(forward_msg)

        self.on_event.connect(record_event, weak=False)

    def _run_script_thread(self) -> None:
        try:
            super()._run_script_thread()
        except BaseException as e:
            self.script_thread_exceptions.append(e)

    def _run_script(self, rerun_data: RerunData) -> None:
        self.forward_msg_queue.clear()
        super()._run_script(rerun_data)

    def join(self) -> None:
        """Join the script_thread if it's running."""
        if self._script_thread is not None:
            self._script_thread.join()

    def clear_forward_msgs(self) -> None:
        """Clear all messages from our ForwardMsgQueue."""
        self.forward_msg_queue.clear()

    def forward_msgs(self) -> List[ForwardMsg]:
        """Return all messages in our ForwardMsgQueue."""
        return self.forward_msg_queue._queue

    def deltas(self) -> List[Delta]:
        """Return the delta messages in our ForwardMsgQueue."""
        return [
            msg.delta for msg in self.forward_msg_queue._queue if msg.HasField("delta")
        ]

    def elements(self) -> List[ElementProto]:
        """Return the delta.new_element messages in our ForwardMsgQueue."""
        return [delta.new_element for delta in self.deltas()]

    def get_widget_id(self, widget_type: str, label: str) -> Optional[str]:
        """Returns the id of the widget with the specified type and label"""
        for delta in self.deltas():
            new_element = getattr(delta, "new_element", None)
            widget = getattr(new_element, widget_type, None)
            widget_label = getattr(widget, "label", None)
            if widget_label == label:
                return widget.id
        return None

    def run(self, widget_state: Optional[WidgetStates] = None) -> Root:
        rerun_data = RerunData(widget_states=widget_state)
        self.request_rerun(rerun_data)
        if not self._script_thread:
            self.start()
        require_widgets_deltas(self)
        tree = parse_tree_from_messages(self.forward_msgs())
        tree.script_runner = self
        return tree

    def script_stopped(self) -> bool:
        for e in self.events:
            if (
                e == ScriptRunnerEvent.SCRIPT_STOPPED_FOR_RERUN
                or e == ScriptRunnerEvent.SCRIPT_STOPPED_WITH_COMPILE_ERROR
                or e == ScriptRunnerEvent.SCRIPT_STOPPED_WITH_SUCCESS
            ):
                return True
        return False


def script_from_string(path: pathlib.Path, script: str) -> TestScriptRunner:
    path.write_text(script)
    return TestScriptRunner(str(path))


def script_from_filename(script_name: str) -> TestScriptRunner:
    script_path = os.path.join(
        os.path.dirname(__file__), "streamlit", "test_data", script_name
    )
    return TestScriptRunner(script_path)


def require_widgets_deltas(runner: TestScriptRunner, timeout: float = 3) -> None:
    """Wait for the given ScriptRunner to emit a completion event. If the timeout
    is reached, the runner will be shutdown and an error will be thrown.
    """

    t0 = time.time()
    while time.time() - t0 < timeout:
        time.sleep(0.1)
        if runner.script_stopped():
            return

    # If we get here, the runner hasn't yet completed before our
    # timeout. Create an error string for debugging.
    err_string = f"require_widgets_deltas() timed out after {timeout}s)"

    # Shutdown the runner before throwing an error, so that the script
    # doesn't hang forever.
    runner.request_stop()
    runner.join()

    raise RuntimeError(err_string)


@dataclass(init=False)
class Element:
    type: str
    proto: ElementProto = field(repr=False)
    root: Root = field(repr=False)

    def __init__(self, proto: ElementProto, root: Root):
        self.proto = proto
        self.root = root
        ty = proto.WhichOneof("type")
        assert ty is not None
        self.type = ty

    def __iter__(self):
        yield self

    @property
    def value(self):
        p = getattr(self.proto, self.type)
        return p.value

    def widget_state(self) -> Optional[WidgetState]:
        return None

    def run(self) -> Root:
        assert self.root.script_runner is not None

        widget_states = self.root.get_widget_states()
        return self.root.script_runner.run(widget_states)


@dataclass(init=False)
class Text(Element):
    proto: TextProto
    root: Root = field(repr=False)

    def __init__(self, proto: TextProto, root: Root):
        self.proto = proto
        self.root = root

    @property
    def value(self) -> str:
        return self.proto.body

    @property
    def type(self) -> str:
        return "text"


@dataclass(init=False)
class Radio(Element):
    proto: RadioProto
    _index: Any
    root: Root = field(repr=False)

    def __init__(self, proto: RadioProto, root: Root):
        self.proto = proto
        self.root = root
        self._index = None

    @property
    def index(self) -> int:
        if self.proto.set_value:
            v = self.proto.value
        else:
            v = self.proto.default
        return v

    @property
    def value(self) -> str:
        v = self.index
        return self.proto.options[v]

    @property
    def type(self) -> str:
        return "radio"

    @property
    def label(self) -> str:
        return self.proto.label

    @property
    def id(self) -> str:
        return self.proto.id

    def set_value(self, v: str) -> Radio:
        self._index = list(self.proto.options).index(v)
        return self

    def widget_state(self) -> WidgetState:
        ws = WidgetState()
        ws.id = self.id
        if self._index is not None:
            ws.int_value = self._index
        else:
            ws.int_value = self.index
        return ws


@dataclass(init=False)
class Block:
    type: str
    children: Dict[int, Union[Element, Block]]
    proto: Optional[BlockProto] = field(repr=False)
    root: Root = field(repr=False)

    def __init__(
        self,
        root: Root,
        proto: Optional[BlockProto] = None,
        type: Optional[str] = None,
    ):
        self.children = {}
        self.proto = proto
        if proto:
            ty = proto.WhichOneof("type")
            assert ty is not None
            self.type = ty
        elif type is not None:
            self.type = type
        else:
            self.type = ""
        self.root = root

    def __len__(self) -> int:
        return len(self.children)

    def __iter__(self):
        yield self
        for child_idx in self.children:
            for c in self.children[child_idx]:
                yield c

    @overload
    def get(self, elt: Literal["text"]) -> List[Text]:
        ...

    @overload
    def get(self, elt: Literal["radio"]) -> List[Radio]:
        ...

    def get(self, elt: str) -> List[Union[Element, Block]]:
        return [e for e in self if e.type == elt]

    def widget_state(self) -> Optional[WidgetState]:
        return None

    def get_widget_states(self) -> WidgetStates:
        ws = WidgetStates()
        for node in self.root:
            w = node.widget_state()
            if w is not None:
                ws.widgets.append(w)

        return ws

    def run(self) -> Root:
        assert self.root.script_runner is not None

        widget_states = self.get_widget_states()
        return self.root.script_runner.run(widget_states)


@dataclass(init=False)
class Root(Block):
    script_runner: Optional[TestScriptRunner]

    def __init__(self):
        self.children = {}
        self.root = self
        self.script_runner = None

    @property
    def type(self) -> str:
        return "root"


def parse_tree_from_messages(messages: List[ForwardMsg]) -> Root:
    root = Root()
    root.children = {
        0: Block(type="main", root=root),
        1: Block(type="sidebar", root=root),
    }

    for msg in messages:
        if not msg.HasField("delta"):
            continue
        delta_path = msg.metadata.delta_path
        delta = msg.delta
        if delta.WhichOneof("type") == "new_element":
            elt = delta.new_element
            if elt.WhichOneof("type") == "text":
                new_node = Text(elt.text, root=root)
            elif elt.WhichOneof("type") == "radio":
                new_node = Radio(elt.radio, root=root)
            else:
                new_node = Element(elt, root=root)
        elif delta.WhichOneof("type") == "add_block":
            new_node = Block(proto=delta.add_block, root=root)
        else:
            # add_rows
            continue

        current_node = root
        # Every node up to the end is a Block
        for idx in delta_path[:-1]:
            children = current_node.children
            child = children.get(idx)
            if child is None:
                child = Block(root=root)
                children[idx] = child
            current_node = child
            assert isinstance(current_node, Block)
        current_node.children[delta_path[-1]] = new_node

    return root
