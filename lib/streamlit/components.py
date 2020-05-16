# -*- coding: utf-8 -*-
# Copyright 2018-2020 Streamlit Inc.
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

import json
import mimetypes
import os
from typing import Any, Dict, Optional, Type, Union, Callable

import tornado.web

import streamlit as st  # plugins_test relies on this import name, for patching
import streamlit.server.routes
from streamlit import type_util
from streamlit.DeltaGenerator import DeltaGenerator
from streamlit.DeltaGenerator import NoValue
from streamlit.DeltaGenerator import _get_widget_ui_value
from streamlit.elements import arrow_table
from streamlit.errors import StreamlitAPIException
from streamlit.logger import get_logger
from streamlit.proto.ComponentInstance_pb2 import ArgsDataframe
from streamlit.proto.Element_pb2 import Element

LOGGER = get_logger(__name__)


class MarshallComponentException(StreamlitAPIException):
    """Class for exceptions generated during custom component marshalling."""

    pass


# mypy doesn't support *args or **kwargs in Callable declarations, so this
# is as close as we can get to a type for our _custom_wrapper type.
_WrapperFunc = Callable[..., Any]


class CustomComponent:
    """A Custom Component declaration. Instances of this class aren't
    used directly; you must first call `st.register_component` to register
    the Component as a named Streamlit function.
    """

    def __init__(
        self, path: Optional[str] = None, url: Optional[str] = None,
    ):
        if (path is None and url is None) or (path is not None and url is not None):
            raise StreamlitAPIException(
                "Either 'path' or 'url' must be set, but not both."
            )
        self.path = path
        self.url = url
        self._custom_wrapper = None  # type: Optional[_WrapperFunc]

    def __call__(self, *args, **kwargs):
        """Assign a wrapper function to the Component.

        This is intended to be used as a function decorator, e.g.:

        >>> MyComponent = st.declare_component(...)
        >>> @MyComponent
        ... def wrapper(f, foo, bar):
        ...   return f(foo=foo, bar=bar, default=0)

        """

        if len(args) != 1 or not callable(args[0]):
            raise StreamlitAPIException("Expected a single argument of type 'callable'")

        self._custom_wrapper = args[0]

    def create_instance(
        self, component_name: str, dg: DeltaGenerator, *args, **kwargs
    ) -> Optional[Any]:
        """Create a new instance of this CustomComponent."""
        builder = _ComponentInstanceBuilder(self, component_name, dg)
        if self._custom_wrapper is not None:
            return self._custom_wrapper(builder.invoke, *args, **kwargs)
        else:
            return builder.invoke(*args, **kwargs)


class _ComponentInstanceBuilder:
    """A helper class that builds an instance of a CustomComponent.

    (This class exists for readability purposes; it could alternately be
    expressed as a closure within CustomComponent.create_instance(), but at
    the expense of nesting functions absurdly deep.)
    """

    def __init__(
        self, component: CustomComponent, registered_name: str, dg: DeltaGenerator
    ):
        self.component = component
        self.registered_name = registered_name
        self.dg = dg

    def invoke(self, *args, **kwargs) -> Optional[Any]:
        """Create a new instance of the component.

        Parameters
        ----------
        *args
            This must be empty; all args must be named kwargs. This parameter
            only exists to catch incorrect use of the function.
        **kwargs
            Keyword args to pass to the component.

        Returns
        -------
        any or None
            The component's widget value.

        """
        if len(args) > 0:
            raise MarshallComponentException("Argument '%s' needs a label" % args[0])

        args_json = {}
        args_df = {}
        for key, value in kwargs.items():
            if type_util.is_dataframe_like(value):
                args_df[key] = value
            else:
                args_json[key] = value

        args_json = {}
        args_df = {}
        for key, value in kwargs.items():
            if type_util.is_dataframe_compatible(value):
                args_df[key] = value
            else:
                args_json[key] = value

        try:
            serialized_args_json = json.dumps(args_json)
        except BaseException as e:
            raise MarshallComponentException(
                "Could not convert component args to JSON", e
            )

        # If args["default"] is set, then it's the default widget value we
        # return when the user hasn't interacted yet.
        default_value = kwargs.get("default", None)

        # If args["key"] is set, it is the user_key we use to generate our
        # widget ID.
        user_key = kwargs.get("key", None)

        def marshall_component(element: Element) -> Union[Any, Type[NoValue]]:
            element.component_instance.component_name = self.registered_name
            if self.component.url is not None:
                element.component_instance.url = self.component.url

            # Normally, a widget's element_hash (which determines
            # its identity across multiple runs of an app) is computed
            # by hashing the entirety of its protobuf. This means that,
            # if any of the arguments to the widget are changed, Streamlit
            # considers it a new widget instance and it loses its previous
            # state.
            #
            # However! If a *component* has a `key` argument, then the
            # component's hash identity is determined by entirely by
            # `component_name + url + key`. This means that, when `key`
            # exists, the component will maintain its identity even when its
            # other arguments change, and the component's iframe won't be
            # remounted on the frontend.
            #
            # So: if `key` is None, we marshall the element's arguments
            # *before* computing its widget_ui_value (which creates its hash).
            # If `key` is not None, we marshall the arguments *after*.

            def marshall_element_args():
                element.component_instance.args_json = serialized_args_json
                for key, value in args_df.items():
                    new_args_dataframe = ArgsDataframe()
                    new_args_dataframe.key = key
                    arrow_table.marshall(new_args_dataframe.value.data, value)
                    element.component_instance.args_dataframe.append(new_args_dataframe)

            if user_key is None:
                marshall_element_args()

            widget_value = _get_widget_ui_value(
                element_type="component_instance",
                element=element,
                user_key=user_key,
                widget_func_name=self.registered_name,
            )

            if user_key is not None:
                marshall_element_args()

            if widget_value is None:
                widget_value = default_value

            # widget_value will be either None or whatever the component's most
            # recent setWidgetValue value is. We coerce None -> NoValue,
            # because that's what _enqueue_new_element_delta expects.
            return widget_value if widget_value is not None else NoValue

        result = self.dg._enqueue_new_element_delta(
            marshall_element=marshall_component, delta_type="component"
        )

        return result


def declare_component(
    path: Optional[str] = None, url: Optional[str] = None
) -> CustomComponent:
    """Declare a new custom component."""
    return CustomComponent(path, url)


def register_component(name: str, component: CustomComponent) -> None:
    """Register a custom component."""
    # Register this component with our global registry.
    ComponentRegistry.instance().register_component(name, component.path)

    # Build our component function.
    def create_instance(dg: DeltaGenerator, *args, **kwargs) -> Optional[Any]:
        return component.create_instance(name, dg, *args, **kwargs)

    # Build st.[component_name], which just calls component_instance with the
    # main DeltaGenerator.
    def create_instance_main(*args, **kwargs):
        return create_instance(streamlit._main, *args, **kwargs)

    # Register the component as a member function of DeltaGenerator, and as
    # a standalone function in the streamlit namespace.
    # TODO: disallow collisions with important streamlit functions!
    setattr(DeltaGenerator, name, create_instance)
    setattr(st, name, create_instance_main)


class ComponentRequestHandler(tornado.web.RequestHandler):
    def initialize(self, registry: "ComponentRegistry"):
        self._registry = registry

    def get(self, path: str) -> None:
        parts = path.split("/")
        component_name = parts[0]
        component_root = self._registry.get_component_path(component_name)
        if component_root is None:
            self.write("%s not found" % path)
            self.set_status(404)
            return

        filename = "/".join(parts[1:])
        abspath = os.path.join(component_root, filename)

        LOGGER.debug("ComponentRequestHandler: GET: %s -> %s", path, abspath)

        try:
            with open(abspath, "r") as file:
                contents = file.read()
        except OSError as e:
            self.write("%s read error: %s" % (path, e))
            self.set_status(404)
            return

        self.write(contents)
        self.set_header("Content-Type", self.get_content_type(abspath))

        self.set_extra_headers(path)

    def set_extra_headers(self, path):
        """Disable cache for HTML files.

        Other assets like JS and CSS are suffixed with their hash, so they can
        be cached indefinitely.
        """
        is_index_url = len(path) == 0

        if is_index_url or path.endswith(".html"):
            self.set_header("Cache-Control", "no-cache")
        else:
            self.set_header("Cache-Control", "public")

    def set_default_headers(self) -> None:
        if streamlit.server.routes.allow_cross_origin_requests():
            self.set_header("Access-Control-Allow-Origin", "*")

    def options(self) -> None:
        """/OPTIONS handler for preflight CORS checks."""
        self.set_status(204)
        self.finish()

    @staticmethod
    def get_content_type(abspath):
        """Returns the ``Content-Type`` header to be used for this request.
        From tornado.web.StaticFileHandler.
        """
        mime_type, encoding = mimetypes.guess_type(abspath)
        # per RFC 6713, use the appropriate type for a gzip compressed file
        if encoding == "gzip":
            return "application/gzip"
        # As of 2015-07-21 there is no bzip2 encoding defined at
        # http://www.iana.org/assignments/media-types/media-types.xhtml
        # So for that (and any other encoding), use octet-stream.
        elif encoding is not None:
            return "application/octet-stream"
        elif mime_type is not None:
            return mime_type
        # if mime_type not detected, use application/octet-stream
        else:
            return "application/octet-stream"

    @staticmethod
    def get_url(file_id: str) -> str:
        """Return the URL for a component file with the given ID."""
        return "components/{}".format(file_id)


class ComponentRegistry:
    _instance = None  # type: Optional[ComponentRegistry]

    @classmethod
    def instance(cls) -> "ComponentRegistry":
        """Returns the singleton ComponentRegistry"""
        if cls._instance is None:
            cls._instance = ComponentRegistry()
        return cls._instance

    def __init__(self):
        self._components = {}  # type: Dict[str, Optional[str]]

    def register_component(self, name: str, path: Optional[str] = None) -> None:
        """Register a filesystem path as a custom component.

        Parameters
        ----------
        name : str
            The component's name.
        path : str or None
            The path to the directory that contains the component's contents,
            or None if the component is being served as a URL.
        """
        abspath = None
        if path is not None:
            abspath = os.path.abspath(path)
            if not os.path.isdir(abspath):
                raise StreamlitAPIException(
                    "No such component directory: '%s'" % abspath
                )

        self._components[name] = abspath

    def get_component_path(self, name: str) -> Optional[str]:
        """Return the path for the component with the given name.
        If no such component is registered, None will be returned instead.
        """
        return self._components.get(name, None)
