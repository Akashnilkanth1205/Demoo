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

from __future__ import annotations

import contextlib
import threading
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Iterator, Literal, Union

import streamlit as st
from streamlit import runtime, util
from streamlit.deprecation_util import show_deprecation_warning
from streamlit.runtime.caching.cache_errors import CacheReplayClosureError
from streamlit.runtime.scriptrunner_utils.script_run_context import (
    in_cached_function,
)

if TYPE_CHECKING:
    from types import FunctionType

    from google.protobuf.message import Message

    from streamlit.delta_generator import DeltaGenerator
    from streamlit.proto.Block_pb2 import Block
    from streamlit.runtime.caching.cache_type import CacheType


@dataclass(frozen=True)
class MediaMsgData:
    media: bytes | str
    mimetype: str
    media_id: str


@dataclass(frozen=True)
class ElementMsgData:
    """An element's message and related metadata for
    replaying that element's function call.

    media_data is filled in iff this is a media element (image, audio, video).
    """

    delta_type: str
    message: Message
    id_of_dg_called_on: str
    returned_dgs_id: str
    media_data: list[MediaMsgData] | None = None


@dataclass(frozen=True)
class BlockMsgData:
    message: Block
    id_of_dg_called_on: str
    returned_dgs_id: str


MsgData = Union[ElementMsgData, BlockMsgData]


@dataclass
class CachedResult:
    """The full results of calling a cache-decorated function, enough to
    replay the st functions called while executing it.
    """

    value: Any
    messages: list[MsgData]
    main_id: str
    sidebar_id: str


"""
Note [DeltaGenerator method invocation]
There are two top level DG instances defined for all apps:
`main`, which is for putting elements in the main part of the app
`sidebar`, for the sidebar

There are 3 different ways an st function can be invoked:
1. Implicitly on the main DG instance (plain `st.foo` calls)
2. Implicitly in an active contextmanager block (`st.foo` within a `with st.container` context)
3. Explicitly on a DG instance (`st.sidebar.foo`, `my_column_1.foo`)

To simplify replaying messages from a cached function result, we convert all of these
to explicit invocations. How they get rewritten depends on if the invocation was
implicit vs explicit, and if the target DG has been seen/produced during replay.

Implicit invocation on a known DG -> Explicit invocation on that DG
Implicit invocation on an unknown DG -> Rewrite as explicit invocation on main
    with st.container():
        my_cache_decorated_function()

    This is situation 2 above, and the DG is a block entirely outside our function call,
    so we interpret it as "put this element in the enclosing contextmanager block"
    (or main if there isn't one), which is achieved by invoking on main.
Explicit invocation on a known DG -> No change needed
Explicit invocation on an unknown DG -> Raise an error
    We have no way to identify the target DG, and it may not even be present in the
    current script run, so the least surprising thing to do is raise an error.

"""


class CachedMessageReplayContext(threading.local):
    """A utility for storing messages generated by `st` commands called inside
    a cached function.

    Data is stored in a thread-local object, so it's safe to use an instance
    of this class across multiple threads.
    """

    def __init__(self, cache_type: CacheType):
        self._cached_message_stack: list[list[MsgData]] = []
        self._seen_dg_stack: list[set[str]] = []
        self._most_recent_messages: list[MsgData] = []
        self._media_data: list[MediaMsgData] = []
        self._cache_type = cache_type

    def __repr__(self) -> str:
        return util.repr_(self)

    @contextlib.contextmanager
    def calling_cached_function(self, func: FunctionType) -> Iterator[None]:
        """Context manager that should wrap the invocation of a cached function.
        It allows us to track any `st.foo` messages that are generated from inside the
        function for playback during cache retrieval.
        """
        self._cached_message_stack.append([])
        self._seen_dg_stack.append(set())
        nested_call = False
        if in_cached_function.get():
            nested_call = True
        # If we're in a cached function. To disallow usage of widget-like element,
        # we need to set the in_cached_function to true for this cached function run
        # to prevent widget usage (triggers a warning).
        in_cached_function.set(True)

        try:
            yield
        finally:
            self._most_recent_messages = self._cached_message_stack.pop()
            self._seen_dg_stack.pop()
            if not nested_call:
                # Reset the in_cached_function flag. But only if this
                # is not nested inside a cached function that disallows widget usage.
                in_cached_function.set(False)

    def save_element_message(
        self,
        delta_type: str,
        element_proto: Message,
        invoked_dg_id: str,
        used_dg_id: str,
        returned_dg_id: str,
    ) -> None:
        """Record the element protobuf as having been produced during any currently
        executing cached functions, so they can be replayed any time the function's
        execution is skipped because they're in the cache.
        """
        if not runtime.exists():
            return
        if len(self._cached_message_stack) >= 1:
            id_to_save = self.select_dg_to_save(invoked_dg_id, used_dg_id)

            media_data = self._media_data

            element_msg_data = ElementMsgData(
                delta_type,
                element_proto,
                id_to_save,
                returned_dg_id,
                media_data,
            )
            for msgs in self._cached_message_stack:
                msgs.append(element_msg_data)

        # Reset instance state, now that it has been used for the
        # associated element.
        self._media_data = []

        for s in self._seen_dg_stack:
            s.add(returned_dg_id)

    def save_block_message(
        self,
        block_proto: Block,
        invoked_dg_id: str,
        used_dg_id: str,
        returned_dg_id: str,
    ) -> None:
        id_to_save = self.select_dg_to_save(invoked_dg_id, used_dg_id)
        for msgs in self._cached_message_stack:
            msgs.append(BlockMsgData(block_proto, id_to_save, returned_dg_id))
        for s in self._seen_dg_stack:
            s.add(returned_dg_id)

    def select_dg_to_save(self, invoked_id: str, acting_on_id: str) -> str:
        """Select the id of the DG that this message should be invoked on
        during message replay.

        See Note [DeltaGenerator method invocation]

        invoked_id is the DG the st function was called on, usually `st._main`.
        acting_on_id is the DG the st function ultimately runs on, which may be different
        if the invoked DG delegated to another one because it was in a `with` block.
        """
        if len(self._seen_dg_stack) > 0 and acting_on_id in self._seen_dg_stack[-1]:
            return acting_on_id
        else:
            return invoked_id

    def save_image_data(
        self, image_data: bytes | str, mimetype: str, image_id: str
    ) -> None:
        self._media_data.append(MediaMsgData(image_data, mimetype, image_id))


def replay_cached_messages(
    result: CachedResult, cache_type: CacheType, cached_func: FunctionType
) -> None:
    """Replay the st element function calls that happened when executing a
    cache-decorated function.

    When a cache function is executed, we record the element and block messages
    produced, and use those to reproduce the DeltaGenerator calls, so the elements
    will appear in the web app even when execution of the function is skipped
    because the result was cached.

    To make this work, for each st function call we record an identifier for the
    DG it was effectively called on (see Note [DeltaGenerator method invocation]).
    We also record the identifier for each DG returned by an st function call, if
    it returns one. Then, for each recorded message, we get the current DG instance
    corresponding to the DG the message was originally called on, and enqueue the
    message using that, recording any new DGs produced in case a later st function
    call is on one of them.
    """
    from streamlit.delta_generator import DeltaGenerator

    # Maps originally recorded dg ids to this script run's version of that dg
    returned_dgs: dict[str, DeltaGenerator] = {
        result.main_id: st._main,
        result.sidebar_id: st.sidebar,
    }
    try:
        for msg in result.messages:
            if isinstance(msg, ElementMsgData):
                if msg.media_data is not None:
                    for data in msg.media_data:
                        runtime.get_instance().media_file_mgr.add(
                            data.media, data.mimetype, data.media_id
                        )
                dg = returned_dgs[msg.id_of_dg_called_on]
                maybe_dg = dg._enqueue(msg.delta_type, msg.message)
                if isinstance(maybe_dg, DeltaGenerator):
                    returned_dgs[msg.returned_dgs_id] = maybe_dg
            elif isinstance(msg, BlockMsgData):
                dg = returned_dgs[msg.id_of_dg_called_on]
                new_dg = dg._block(msg.message)
                returned_dgs[msg.returned_dgs_id] = new_dg
    except KeyError as ex:
        raise CacheReplayClosureError(cache_type, cached_func) from ex


def show_widget_replay_deprecation(
    decorator: Literal["cache_data", "cache_resource"],
) -> None:
    show_deprecation_warning(
        "The `experimental_allow_widgets` parameter is deprecated and will be removed "
        "in a future release. Please remove the `experimental_allow_widgets` parameter "
        f"from the `@st.{decorator}` decorator and move all widget commands outside of "
        "cached functions.\n\nTo speed up your app, we recommend moving your widgets "
        "into fragments. Find out more about fragments in "
        "[our docs](https://docs.streamlit.io/develop/api-reference/execution-flow/st.fragment). "
        "\n\nIf you have a specific use-case that requires the "
        "`experimental_allow_widgets` functionality, please tell us via an "
        "[issue on Github](https://github.com/streamlit/streamlit/issues)."
    )
