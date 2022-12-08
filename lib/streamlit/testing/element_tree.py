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
import time
from copy import deepcopy
from dataclasses import dataclass, field
from typing import Any, Generic, TypeVar, overload

from typing_extensions import Literal

from streamlit.proto.Block_pb2 import Block as BlockProto
from streamlit.proto.ClientState_pb2 import ClientState
from streamlit.proto.Element_pb2 import Element as ElementProto
from streamlit.proto.ForwardMsg_pb2 import ForwardMsg
from streamlit.proto.Radio_pb2 import Radio as RadioProto
from streamlit.proto.Text_pb2 import Text as TextProto
from streamlit.proto.WidgetStates_pb2 import WidgetState, WidgetStates
from streamlit.runtime.forward_msg_queue import ForwardMsgQueue
from streamlit.runtime.scriptrunner import RerunData, ScriptRunner, ScriptRunnerEvent
from streamlit.runtime.state.session_state import SessionState
from streamlit.runtime.state.widgets import user_key_from_widget_id
from streamlit.runtime.uploaded_file_manager import UploadedFileManager


class LocalScriptRunner(ScriptRunner):
    """Subclasses ScriptRunner to provide some testing features."""

    def __init__(
        self,
        script_path: str,
        prev_session_state: SessionState | None = None,
    ):
        """Initializes the ScriptRunner for the given script_name"""

        assert os.path.isfile(script_path), f"File not found at {script_path}"

        self.forward_msg_queue = ForwardMsgQueue()
        self.script_path = script_path
        if prev_session_state is not None:
            self.session_state = deepcopy(prev_session_state)
        else:
            self.session_state = SessionState()

        super().__init__(
            session_id="test session id",
            main_script_path=script_path,
            client_state=ClientState(),
            session_state=self.session_state,
            uploaded_file_mgr=UploadedFileManager(),
            initial_rerun_data=RerunData(),
            user_info={"email": "test@test.com"},
        )

        # Accumulates uncaught exceptions thrown by our run thread.
        self.script_thread_exceptions: list[BaseException] = []

        # Accumulates all ScriptRunnerEvents emitted by us.
        self.events: list[ScriptRunnerEvent] = []
        self.event_data: list[Any] = []

        def record_event(
            sender: ScriptRunner | None, event: ScriptRunnerEvent, **kwargs
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

    def join(self) -> None:
        """Wait for the script thread to finish, if it is running."""
        if self._script_thread is not None:
            self._script_thread.join()

    def forward_msgs(self) -> list[ForwardMsg]:
        """Return all messages in our ForwardMsgQueue."""
        return self.forward_msg_queue._queue

    def run(self, widget_state: WidgetStates | None = None) -> ElementTree:
        """Run the script, and parse the output messages for querying
        and interaction."""
        rerun_data = RerunData(widget_states=widget_state)
        self.request_rerun(rerun_data)
        if not self._script_thread:
            self.start()
        require_widgets_deltas(self)
        tree = parse_tree_from_messages(self.forward_msgs())
        tree.script_path = self.script_path
        tree._session_state = self.session_state
        return tree

    def script_stopped(self) -> bool:
        for e in self.events:
            if e in (
                ScriptRunnerEvent.SCRIPT_STOPPED_FOR_RERUN,
                ScriptRunnerEvent.SCRIPT_STOPPED_WITH_COMPILE_ERROR,
                ScriptRunnerEvent.SCRIPT_STOPPED_WITH_SUCCESS,
            ):
                return True
        return False


def require_widgets_deltas(runner: LocalScriptRunner, timeout: float = 3) -> None:
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


# TODO This class serves as a fallback option for elements that have not
# been implemented yet, as well as providing implementations of some
# trivial methods. It may have significantly reduced scope, or be removed
# entirely, once all elements have been implemented.
@dataclass(init=False)
class Element:
    type: str
    proto: ElementProto = field(repr=False)
    root: ElementTree = field(repr=False)
    key: str | None

    def __init__(self, proto: ElementProto, root: ElementTree):
        self.proto = proto
        self.root = root
        self.key = None
        ty = proto.WhichOneof("type")
        assert ty is not None
        self.type = ty

    def __iter__(self):
        yield self

    @property
    def value(self) -> Any:
        p = getattr(self.proto, self.type)
        try:
            state = self.root.session_state
            assert state
            return state[p.id]
        except ValueError:
            # No id field, not a widget
            return p.value

    def widget_state(self) -> WidgetState | None:
        return None

    def run(self) -> ElementTree:
        return self.root.run()


@dataclass(init=False)
class Text(Element):
    root: ElementTree = field(repr=False)

    proto: TextProto
    type: str = "text"
    key: None = None

    def __init__(self, proto: TextProto, root: ElementTree):
        self.proto = proto
        self.root = root

    @property
    def value(self) -> str:
        return self.proto.body


T = TypeVar("T")


@dataclass(init=False)
class Radio(Element, Generic[T]):
    root: ElementTree = field(repr=False)
    _value: T | None

    proto: RadioProto
    type: str
    id: str
    label: str
    options: list[str]
    help: str
    form_id: str
    disabled: bool
    horizontal: bool
    key: str | None

    def __init__(self, proto: RadioProto, root: ElementTree):
        self.proto = proto
        self.root = root
        self._value = None

        self.type = "radio"
        self.id = proto.id
        self.label = proto.label
        self.options = list(proto.options)
        self.help = proto.help
        self.form_id = proto.form_id
        self.disabled = proto.disabled
        self.horizontal = proto.horizontal
        self.key = user_key_from_widget_id(self.id)

    @property
    def index(self) -> int:
        return self.options.index(str(self.value))

    @property
    def value(self) -> T:
        """The currently selected value from the options."""
        if self._value is not None:
            return self._value
        else:
            state = self.root.session_state
            assert state
            return state[self.id]

    def set_value(self, v: T) -> Radio:
        self._value = v
        return self

    def widget_state(self) -> WidgetState:
        """Protobuf message representing the state of the widget, including
        any interactions that have happened.
        Should be the same as the frontend would produce for those interactions.
        """
        ws = WidgetState()
        ws.id = self.id
        ws.int_value = self.index
        return ws


@dataclass(init=False)
class Block:
    type: str
    children: dict[int, Element | Block]
    proto: BlockProto | None = field(repr=False)
    root: ElementTree = field(repr=False)

    def __init__(
        self,
        root: ElementTree,
        proto: BlockProto | None = None,
        type: str | None = None,
    ):
        self.children = {}
        self.proto = proto
        if proto:
            ty = proto.WhichOneof("type")
            # TODO does not work for `st.container` which has no block proto
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

    def __getitem__(self, k: int) -> Element | Block:
        return self.children[k]

    @property
    def key(self) -> str | None:
        return None

    @overload
    def get(self, elt: Literal["text"]) -> list[Text]:
        ...

    @overload
    def get(self, elt: Literal["radio"]) -> list[Radio]:
        ...

    def get(self, elt: str) -> list[Element | Block]:
        return [e for e in self if e.type == elt]

    def get_widget(self, key: str) -> Element | None:
        for e in self:
            if e.key == key:
                assert isinstance(e, Element)
                return e
        return None

    def widget_state(self) -> WidgetState | None:
        return None

    def run(self) -> ElementTree:
        return self.root.run()


@dataclass(init=False)
class ElementTree(Block):
    script_path: str | None = field(repr=False, default=None)
    _session_state: SessionState | None = field(repr=False, default=None)

    type: str = "root"

    def __init__(self):
        # Expect script_path and session_state to be filled in afterwards
        self.children = {}
        self.root = self

    @property
    def session_state(self) -> SessionState:
        assert self._session_state is not None
        return self._session_state

    def get_widget_states(self) -> WidgetStates:
        ws = WidgetStates()
        for node in self:
            w = node.widget_state()
            if w is not None:
                ws.widgets.append(w)

        return ws

    def run(self) -> ElementTree:
        assert self.script_path is not None

        widget_states = self.get_widget_states()
        runner = LocalScriptRunner(self.script_path, self.session_state)
        return runner.run(widget_states)


def parse_tree_from_messages(messages: list[ForwardMsg]) -> ElementTree:
    root = ElementTree()
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
