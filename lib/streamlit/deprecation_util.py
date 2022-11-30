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

import enum
import functools
from typing import Any, Callable, List, TypeVar, cast

import streamlit

TFunc = TypeVar("TFunc", bound=Callable[..., Any])
TObj = TypeVar("TObj", bound=object)


class PrereleaseAPIType(enum.Enum):
    BETA = "BETA"
    EXPERIMENTAL = "EXPERIMENTAL"


def _get_function_name_prefix(api_type: PrereleaseAPIType) -> str:
    """Return the function name prefix (e.g. 'beta_') for the given PrereleaseAPIType."""
    if api_type is PrereleaseAPIType.BETA:
        return "beta_"
    if api_type is PrereleaseAPIType.EXPERIMENTAL:
        return "experimental_"
    raise RuntimeError(f"Unrecognized PrereleaseAPIType: {api_type}")


def _show_api_graduation_warning(
    api_type: PrereleaseAPIType, name: str, removal_date: str
) -> None:
    prefix = _get_function_name_prefix(api_type)
    streamlit.warning(
        f"Please replace `st.{prefix}{name}` with `st.{name}`.\n\n"
        f"`st.{prefix}{name}` will be removed after {removal_date}."
    )


def function_prerelease_graduation_warning(
    api_type: PrereleaseAPIType, func: TFunc, removal_date: str
) -> TFunc:
    """Wrapper for functions that have "graduated" from pre-release.

    Wrapped functions will run as normal, but then proceed to show an st.warning
    saying that the beta_/experimental_ version will be removed in ~3 months.

    Parameters
    ----------
    api_type : PrereleaseAPIType
        The type of prerelease API that's graduating to release.

    func: callable
        The `st.` function that has graduated from beta/experimental.

    removal_date: str
        A date like "2020-01-01", indicating the last day we'll guarantee
        support for the beta_/experimental_ prefix.
    """

    @functools.wraps(func)
    def wrapped_func(*args, **kwargs):
        result = func(*args, **kwargs)
        _show_api_graduation_warning(api_type, func.__name__, removal_date)
        return result

    # Update the wrapped func's name & docstring so st.help does the right thing
    wrapped_func.__name__ = f"{_get_function_name_prefix(api_type)}{func.__name__}"
    wrapped_func.__doc__ = func.__doc__
    return cast(TFunc, wrapped_func)


def object_prerelease_graduation_warning(
    api_type: PrereleaseAPIType, obj: TObj, obj_name: str, removal_date: str
) -> TObj:
    """Wrapper for objects that have "graduated" from pre-release.

    Wrapped objects will run as normal, but then proceed to show an st.warning
    saying that the beta_/experimental_ version will be removed in ~3 months.

    Parameters
    ----------
    obj: Any
        The `st.` object that used to be in beta.

    api_type : PrereleaseAPIType
        The type of prerelease API that's graduating to release.

    obj_name: str
        The name of the object within __init__.py

    removal_date: str
        A date like "2020-01-01", indicating the last day we'll guarantee
        support for the beta_ prefix.
    """

    return _create_deprecated_object_wrapper(
        obj, lambda: _show_api_graduation_warning(api_type, obj_name, removal_date)
    )


def deprecate_object_with_console_warning(obj: TObj, warning: str) -> TObj:
    """Create a wrapper for an object that has been deprecated. The first
    time any of the object's properties or functions is accessed, the
    given warning text will be written to the console.
    """
    return _create_deprecated_object_wrapper(obj, lambda: print(warning))


def _create_deprecated_object_wrapper(
    obj: TObj, show_warning: Callable[[], Any]
) -> TObj:
    """Create a wrapper for an object that has been deprecated. The first
    time one of the object's properties or functions is accessed, the
    given `show_warning` callback will be called.
    """
    has_shown_warning = False

    def maybe_show_warning() -> None:
        # Call `show_warning` if it hasn't already been called once.
        nonlocal has_shown_warning
        if not has_shown_warning:
            has_shown_warning = True
            show_warning()

    class Wrapper:
        def __init__(self):
            # Override all the Wrapped object's magic functions
            for name in Wrapper._get_magic_functions(obj.__class__):
                setattr(
                    self.__class__,
                    name,
                    property(self._make_magic_function_proxy(name)),
                )

        def __getattr__(self, attr):
            # We handle __getattr__ separately from our other magic
            # functions. The wrapped class may not actually implement it,
            # but we still need to implement it to call all its normal
            # functions.
            if attr in self.__dict__:
                return getattr(self, attr)

            maybe_show_warning()
            return getattr(obj, attr)

        @staticmethod
        def _get_magic_functions(cls) -> List[str]:
            # ignore the handful of magic functions we cannot override without
            # breaking the Wrapper.
            ignore = ("__class__", "__dict__", "__getattribute__", "__getattr__")
            return [
                name
                for name in dir(cls)
                if name not in ignore and name.startswith("__")
            ]

        @staticmethod
        def _make_magic_function_proxy(name):
            def proxy(self, *args):
                maybe_show_warning()
                return getattr(obj, name)

            return proxy

    return cast(TObj, Wrapper())
