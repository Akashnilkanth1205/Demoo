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

from dataclasses import dataclass, field
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    Sequence,
    cast,
)

from streamlit.elements.lib.policies import (
    check_cache_replay_rules,
    check_callback_rules,
    check_fragment_path_policy,
    check_session_state_rules,
)
from streamlit.errors import StreamlitAPIException
from streamlit.type_util import (
    OptionSequence,
    T,
    check_python_comparable,
    ensure_indexable,
    is_type,
)

if TYPE_CHECKING:
    from streamlit.delta_generator import DeltaGenerator
    from streamlit.runtime.state import (
        WidgetCallback,
    )


@dataclass
class MultiSelectSerde(Generic[T]):
    options: Sequence[T]
    default_value: list[int] = field(default_factory=list)

    def serialize(self, value: list[T]) -> list[int]:
        indices = _check_and_convert_to_indices(self.options, value)
        return indices if indices is not None else []

    def deserialize(
        self,
        ui_value: list[int] | None,
        widget_id: str = "",
    ) -> list[T]:
        current_value: list[int] = (
            ui_value if ui_value is not None else self.default_value
        )
        return [self.options[i] for i in current_value]


def _check_and_convert_to_indices(
    opt: Sequence[Any], default_values: Sequence[Any] | Any | None
) -> list[int] | None:
    """Perform validation checks and return indices based on the default values."""
    if default_values is None and None not in opt:
        return None

    if not isinstance(default_values, list):
        # This if is done before others because calling if not x (done
        # right below) when x is of type pd.Series() or np.array() throws a
        # ValueError exception.
        if is_type(default_values, "numpy.ndarray") or is_type(
            default_values, "pandas.core.series.Series"
        ):
            default_values = list(cast(Sequence[Any], default_values))
        elif (
            isinstance(default_values, (tuple, set))
            or default_values
            and default_values not in opt
        ):
            default_values = list(default_values)
        else:
            default_values = [default_values]
    for value in default_values:
        if value not in opt:
            raise StreamlitAPIException(
                f"The default value '{value}' is not part of the options. "
                "Please make sure that every default values also exists in the options."
            )

    return [opt.index(value) for value in default_values]


def check_multiselect_policies(
    dg: DeltaGenerator,
    key: str | None,
    on_change: WidgetCallback | None = None,
    default: Sequence[Any] | Any | None = None,
):
    check_fragment_path_policy(dg)
    check_cache_replay_rules()
    check_callback_rules(dg, on_change)
    check_session_state_rules(default_value=default, key=key, writes_allowed=True)


def ensure_indexable_and_comparable(options: OptionSequence[T]) -> Sequence[T]:
    indexable_options = ensure_indexable(options)
    check_python_comparable(indexable_options)
    return indexable_options


def get_default_indices(
    indexable_options: Sequence[T], default: Sequence[Any] | Any | None = None
) -> list[int]:
    default_indices = _check_and_convert_to_indices(indexable_options, default)
    default_indices = default_indices if default_indices is not None else []
    return default_indices
