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

import json
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Dict,
    List,
    Mapping,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
    cast,
    overload,
)

import pandas as pd
import pyarrow as pa
from typing_extensions import Literal, TypeAlias, TypedDict

from streamlit import logger as _logger
from streamlit import type_util
from streamlit.elements.form import current_form_id
from streamlit.elements.lib.column_config_utils import (
    INDEX_IDENTIFIER,
    ColumnConfigMapping,
    ColumnConfigMappingInput,
    ColumnDataKind,
    DataframeSchema,
    determine_dataframe_schema,
    is_type_compatible,
    marshall_column_config,
    process_config_mapping,
)
from streamlit.elements.lib.pandas_styler_utils import marshall_styler
from streamlit.errors import StreamlitAPIException
from streamlit.proto.Arrow_pb2 import Arrow as ArrowProto
from streamlit.runtime.metrics_util import gather_metrics
from streamlit.runtime.scriptrunner import get_script_run_ctx
from streamlit.runtime.state import (
    WidgetArgs,
    WidgetCallback,
    WidgetKwargs,
    register_widget,
)
from streamlit.type_util import DataFormat, DataFrameGenericAlias, Key, is_type, to_key

if TYPE_CHECKING:
    import numpy as np
    from pandas.io.formats.style import Styler

    from streamlit.delta_generator import DeltaGenerator

_LOGGER = _logger.get_logger("root")

# All formats that support direct editing, meaning that these
# formats will be returned with the same type when used with data_editor.
EditableData = TypeVar(
    "EditableData",
    bound=Union[
        DataFrameGenericAlias[Any],  # covers DataFrame and Series
        Tuple[Any],
        List[Any],
        Set[Any],
        Dict[str, Any],
        # TODO(lukasmasuch): Add support for np.ndarray
        # but it is not possible with np.ndarray.
        # NDArray[Any] works, but is only available in numpy>1.20.
    ],
)


# All data types supported by the data editor.
DataTypes: TypeAlias = Union[
    pd.DataFrame,
    pd.Index,
    "Styler",
    pa.Table,
    "np.ndarray[Any, np.dtype[np.float64]]",
    Tuple[Any],
    List[Any],
    Set[Any],
    Dict[str, Any],
]


class EditingState(TypedDict, total=False):
    """
    A dictionary representing the current state of the data editor.

    Attributes
    ----------
    edited_cells : Dict[str, str | int | float | bool | None]
        A dictionary of edited cells, where the key is the cell's row and
        column position (row:column), and the value is the new value of the cell.

    added_rows : List[Dict[str, str | int | float | bool | None]]
        A list of added rows, where each row is a dictionary of column position
        and the respective value.

    deleted_rows : List[int]
        A list of deleted rows, where each row is the numerical position of the deleted row.
    """

    edited_cells: Dict[str, str | int | float | bool | None]
    added_rows: List[Dict[str, str | int | float | bool | None]]
    deleted_rows: List[int]


@dataclass
class DataEditorSerde:
    """DataEditorSerde is used to serialize and deserialize the data editor state."""

    def deserialize(self, ui_value: Optional[str], widget_id: str = "") -> EditingState:
        return (  # type: ignore
            {
                "edited_cells": {},
                "added_rows": [],
                "deleted_rows": [],
            }
            if ui_value is None
            else json.loads(ui_value)
        )

    def serialize(self, editing_state: EditingState) -> str:
        return json.dumps(editing_state, default=str)


def _parse_value(
    value: str | int | float | bool | None,
    column_data_kind: ColumnDataKind,
) -> Any:
    """Convert a value to the correct type.

    Parameters
    ----------
    value : str | int | float | bool | None
        The value to convert.

    column_data_kind : ColumnDataKind
        The determined data kind of the column. The column data kind refers to the
        shared data type of the values in the column (e.g. integer, float, string).

    Returns
    -------
    The converted value.
    """
    if value is None:
        return None

    try:
        if column_data_kind == ColumnDataKind.STRING:
            return str(value)

        if column_data_kind == ColumnDataKind.INTEGER:
            return int(value)

        if column_data_kind == ColumnDataKind.FLOAT:
            return float(value)

        if column_data_kind == ColumnDataKind.BOOLEAN:
            return bool(value)

        if column_data_kind in [
            ColumnDataKind.DATETIME,
            ColumnDataKind.DATE,
            ColumnDataKind.TIME,
        ]:
            datetime_value = pd.Timestamp(value)

            if datetime_value is pd.NaT:
                return None

            if column_data_kind == ColumnDataKind.DATETIME:
                return datetime_value

            if column_data_kind == ColumnDataKind.DATE:
                return datetime_value.date()

            if column_data_kind == ColumnDataKind.TIME:
                return datetime_value.time()

    except (ValueError, pd.errors.ParserError) as ex:
        _LOGGER.warning(
            "Failed to parse value %s as %s. Exception: %s", value, column_data_kind, ex
        )
        return None
    return value


def _apply_cell_edits(
    df: pd.DataFrame,
    edited_cells: Mapping[str, str | int | float | bool | None],
    dataframe_schema: DataframeSchema,
) -> None:
    """Apply cell edits to the provided dataframe (inplace).

    Parameters
    ----------
    df : pd.DataFrame
        The dataframe to apply the cell edits to.

    edited_cells : Dict[str, str | int | float | bool | None]
        A dictionary of cell edits. The keys are the cell ids in the format
        "row:column" and the values are the new cell values.

    dataframe_schema: DataframeSchema
        The schema of the dataframe.
    """
    index_count = df.index.nlevels or 0

    for cell, value in edited_cells.items():
        row_pos, col_pos = map(int, cell.split(":"))

        if col_pos < index_count:
            # The edited cell is part of the index
            # To support multi-index in the future: use a tuple of values here
            # instead of a single value
            df.index.values[row_pos] = _parse_value(value, dataframe_schema[col_pos])
        else:
            # We need to subtract the number of index levels from col_pos
            # to get the correct column position for Pandas DataFrames
            mapped_column = col_pos - index_count
            df.iat[row_pos, mapped_column] = _parse_value(
                value, dataframe_schema[col_pos]
            )


def _apply_row_additions(
    df: pd.DataFrame,
    added_rows: List[Dict[str, Any]],
    dataframe_schema: DataframeSchema,
) -> None:
    """Apply row additions to the provided dataframe (inplace).

    Parameters
    ----------
    df : pd.DataFrame
        The dataframe to apply the row additions to.

    added_rows : List[Dict[str, Any]]
        A list of row additions. Each row addition is a dictionary with the
        column position as key and the new cell value as value.

    dataframe_schema: DataframeSchema
        The schema of the dataframe.
    """
    if not added_rows:
        return

    index_count = df.index.nlevels or 0

    # This is only used if the dataframe has a range index:
    # There seems to be a bug in older pandas versions with RangeIndex in
    # combination with loc. As a workaround, we manually track the values here:
    range_index_stop = None
    range_index_step = None
    if isinstance(df.index, pd.RangeIndex):
        range_index_stop = df.index.stop
        range_index_step = df.index.step

    for added_row in added_rows:
        index_value = None
        new_row: List[Any] = [None for _ in range(df.shape[1])]
        for col in added_row.keys():
            value = added_row[col]
            col_pos = int(col)
            if col_pos < index_count:
                # To support multi-index in the future: use a tuple of values here
                # instead of a single value
                index_value = _parse_value(value, dataframe_schema[col_pos])
            else:
                # We need to subtract the number of index levels from the col_pos
                # to get the correct column position for Pandas DataFrames
                mapped_column = col_pos - index_count
                new_row[mapped_column] = _parse_value(value, dataframe_schema[col_pos])
        # Append the new row to the dataframe
        if range_index_stop is not None:
            df.loc[range_index_stop, :] = new_row
            # Increment to the next range index value
            range_index_stop += range_index_step
        elif index_value is not None:
            # TODO(lukasmasuch): we are only adding rows that have a non-None index
            # value to prevent issues in the frontend component. Also, it just overwrites
            # the row in case the index value already exists in the dataframe.
            # In the future, it would be better to require users to provide unique
            # non-None values for the index with some kind of visual indications.
            df.loc[index_value, :] = new_row


def _apply_row_deletions(df: pd.DataFrame, deleted_rows: List[int]) -> None:
    """Apply row deletions to the provided dataframe (inplace).

    Parameters
    ----------
    df : pd.DataFrame
        The dataframe to apply the row deletions to.

    deleted_rows : List[int]
        A list of row numbers to delete.
    """
    # Drop rows based in numeric row positions
    df.drop(df.index[deleted_rows], inplace=True)


def _apply_dataframe_edits(
    df: pd.DataFrame,
    data_editor_state: EditingState,
    dataframe_schema: DataframeSchema,
) -> None:
    """Apply edits to the provided dataframe (inplace).

    This includes cell edits, row additions and row deletions.

    Parameters
    ----------
    df : pd.DataFrame
        The dataframe to apply the edits to.

    data_editor_state : EditingState
        The editing state of the data editor component.

    dataframe_schema: DataframeSchema
        The schema of the dataframe.
    """
    if data_editor_state.get("edited_cells"):
        _apply_cell_edits(df, data_editor_state["edited_cells"], dataframe_schema)

    if data_editor_state.get("added_rows"):
        _apply_row_additions(df, data_editor_state["added_rows"], dataframe_schema)

    if data_editor_state.get("deleted_rows"):
        _apply_row_deletions(df, data_editor_state["deleted_rows"])


def _apply_data_specific_configs(
    columns_config: ColumnConfigMapping, data_df: pd.DataFrame, data_format: DataFormat
) -> None:
    """Apply data specific configurations to the provided dataframe.

    This will apply inplace changes to the dataframe and the column configurations
    depending on the data format.

    Parameters
    ----------
    columns_config : ColumnConfigMapping
        A mapping of column names/ids to column configurations.

    data_df : pd.DataFrame
        The dataframe to apply the configurations to.

    data_format : DataFormat
        The format of the data.
    """
    # Deactivate editing for columns that are not compatible with arrow
    for column_name, column_data in data_df.items():
        if type_util.is_colum_type_arrow_incompatible(column_data):
            if column_name not in columns_config:
                columns_config[column_name] = {}
            columns_config[column_name]["disabled"] = True
            # Convert incompatible type to string
            data_df[column_name] = column_data.astype(str)

    # Pandas adds a range index as default to all datastructures
    # but for most of the non-pandas data objects it is unnecessary
    # to show this index to the user. Therefore, we will hide it as default.
    if data_format in [
        DataFormat.SET_OF_VALUES,
        DataFormat.TUPLE_OF_VALUES,
        DataFormat.LIST_OF_VALUES,
        DataFormat.NUMPY_LIST,
        DataFormat.NUMPY_MATRIX,
        DataFormat.LIST_OF_RECORDS,
        DataFormat.LIST_OF_ROWS,
        DataFormat.COLUMN_VALUE_MAPPING,
    ]:
        if INDEX_IDENTIFIER not in columns_config:
            columns_config[INDEX_IDENTIFIER] = {}
        columns_config[INDEX_IDENTIFIER]["hidden"] = True

    # Rename the first column to "value" for some of the data formats
    if data_format in [
        DataFormat.SET_OF_VALUES,
        DataFormat.TUPLE_OF_VALUES,
        DataFormat.LIST_OF_VALUES,
        DataFormat.NUMPY_LIST,
        DataFormat.KEY_VALUE_DICT,
    ]:
        # Pandas automatically names the first column "0"
        # We rename it to "value" in selected cases to make it more descriptive
        data_df.rename(columns={0: "value"}, inplace=True)


def _is_supported_index(df_index: pd.Index) -> bool:
    """Check if the index is supported by the data editor component.

    Parameters
    ----------
    df_index : pd.Index
        The index to check.

    Returns
    -------
    bool
        True if the index is supported, False otherwise.
    """

    return (
        type(df_index)
        in [
            pd.RangeIndex,
            pd.Index,
        ]
        # We need to check these index types without importing, since they are deprecated
        # and planned to be removed soon.
        or is_type(df_index, "pandas.core.indexes.numeric.Int64Index")
        or is_type(df_index, "pandas.core.indexes.numeric.Float64Index")
        or is_type(df_index, "pandas.core.indexes.numeric.UInt64Index")
    )


def _check_type_compatibilities(
    data_df: pd.DataFrame,
    columns_config: ColumnConfigMapping,
    dataframe_schema: DataframeSchema,
):
    """Check column type to data type compatibility.

    Iterates the index and all columns of the dataframe to check if
    the configured column types are compatible with the underlying data types.

    Parameters
    ----------
    data_df : pd.DataFrame
        The dataframe to check the type compatibilities for.

    columns_config : ColumnConfigMapping
        A mapping of column to column configurations.

    dataframe_schema : DataframeSchema
        The schema of the dataframe.

    Raises
    ------
    StreamlitAPIException
        If a configured column type is editable and not compatible with the
        underlying data type.
    """
    for i, column in enumerate(
        [(INDEX_IDENTIFIER, data_df.index)] + list(data_df.items())
    ):
        column_name, _ = column
        column_data_kind = dataframe_schema[i]

        # TODO: support column config by numerical index
        if column_name in columns_config:
            column_config = columns_config[column_name]
            if column_config.get("disabled") is True:
                # Disabled columns are not checked for compatibility.
                # This might change in the future.
                continue

            configured_column_type = column_config.get("type")

            if configured_column_type is None:
                continue

            if is_type_compatible(configured_column_type, column_data_kind) is False:
                # TODO: Put on top as constant?
                raise StreamlitAPIException(
                    f"The configured column type `{configured_column_type}` for column "
                    f"`{column_name}` is not compatible for editing the underlying "
                    f"data type `{column_data_kind}`.\n\nYou have following options to "
                    f"fix this: 1) choose a compatible type 2) disable the column "
                    f"3) convert the column into a compatible data type."
                )


class DataEditorMixin:
    @overload
    def experimental_data_editor(
        self,
        data: EditableData,
        *,
        width: Optional[int] = None,
        height: Optional[int] = None,
        use_container_width: bool = False,
        num_rows: Literal["fixed", "dynamic"] = "fixed",
        disabled: bool = False,
        key: Optional[Key] = None,
        on_change: Optional[WidgetCallback] = None,
        args: Optional[WidgetArgs] = None,
        kwargs: Optional[WidgetKwargs] = None,
        column_config: Optional[ColumnConfigMappingInput] = None,
    ) -> EditableData:
        pass

    @overload
    def experimental_data_editor(
        self,
        data: Any,
        *,
        width: Optional[int] = None,
        height: Optional[int] = None,
        use_container_width: bool = False,
        num_rows: Literal["fixed", "dynamic"] = "fixed",
        disabled: bool = False,
        key: Optional[Key] = None,
        on_change: Optional[WidgetCallback] = None,
        args: Optional[WidgetArgs] = None,
        kwargs: Optional[WidgetKwargs] = None,
        column_config: Optional[ColumnConfigMappingInput] = None,
    ) -> pd.DataFrame:
        pass

    @gather_metrics("experimental_data_editor")
    def experimental_data_editor(
        self,
        data: DataTypes,
        *,
        width: Optional[int] = None,
        height: Optional[int] = None,
        use_container_width: bool = False,
        num_rows: Literal["fixed", "dynamic"] = "fixed",
        disabled: bool = False,
        key: Optional[Key] = None,
        on_change: Optional[WidgetCallback] = None,
        args: Optional[WidgetArgs] = None,
        kwargs: Optional[WidgetKwargs] = None,
        column_config: Optional[ColumnConfigMappingInput] = None,
    ) -> DataTypes:
        """Display a data editor widget.

        Display a data editor widget that allows you to edit DataFrames and
        many other data structures in a table-like UI.

        Parameters
        ----------
        data : pandas.DataFrame, pandas.Styler, pandas.Index, pyarrow.Table, numpy.ndarray, pyspark.sql.DataFrame, snowflake.snowpark.DataFrame, list, set, tuple, dict, or None
            The data to edit in the data editor.

        width : int or None
            Desired width of the data editor expressed in pixels. If None, the width will
            be automatically determined.

        height : int or None
            Desired height of the data editor expressed in pixels. If None, the height will
            be automatically determined.

        use_container_width : bool
            If True, set the data editor width to the width of the parent container.
            This takes precedence over the width argument. Defaults to False.

        num_rows : "fixed" or "dynamic"
            Specifies if the user can add and delete rows in the data editor.
            If "fixed", the user cannot add or delete rows. If "dynamic", the user can
            add and delete rows in the data editor, but column sorting is disabled.
            Defaults to "fixed".

        disabled : bool
            An optional boolean which, if True, disables the data editor and prevents
            any edits. Defaults to False. This argument can only be supplied by keyword.

        key : str
            An optional string to use as the unique key for this widget. If this
            is omitted, a key will be generated for the widget based on its
            content. Multiple widgets of the same type may not share the same
            key.

        on_change : callable
            An optional callback invoked when this data_editor's value changes.

        args : tuple
            An optional tuple of args to pass to the callback.

        kwargs : dict
            An optional dict of kwargs to pass to the callback.

        Returns
        -------
        pd.DataFrame, pd.Styler, pyarrow.Table, np.ndarray, list, set, tuple, or dict.
            The edited data. The edited data is returned in its original data type if
            it corresponds to any of the supported return types. All other data types
            are returned as a ``pd.DataFrame``.

        Examples
        --------
        >>> import streamlit as st
        >>> import pandas as pd
        >>>
        >>> df = pd.DataFrame(
        >>>     [
        >>>        {"command": "st.selectbox", "rating": 4, "is_widget": True},
        >>>        {"command": "st.balloons", "rating": 5, "is_widget": False},
        >>>        {"command": "st.time_input", "rating": 3, "is_widget": True},
        >>>    ]
        >>> )
        >>> edited_df = st.experimental_data_editor(df)
        >>>
        >>> favorite_command = edited_df.loc[edited_df["rating"].idxmax()]["command"]
        >>> st.markdown(f"Your favorite command is **{favorite_command}** 🎈")

        .. output::
           https://doc-data-editor.streamlit.app/
           height: 350px

        You can also allow the user to add and delete rows by setting ``num_rows`` to "dynamic":

        >>> import streamlit as st
        >>> import pandas as pd
        >>>
        >>> df = pd.DataFrame(
        >>>     [
        >>>        {"command": "st.selectbox", "rating": 4, "is_widget": True},
        >>>        {"command": "st.balloons", "rating": 5, "is_widget": False},
        >>>        {"command": "st.time_input", "rating": 3, "is_widget": True},
        >>>    ]
        >>> )
        >>> edited_df = st.experimental_data_editor(df, num_rows="dynamic")
        >>>
        >>> favorite_command = edited_df.loc[edited_df["rating"].idxmax()]["command"]
        >>> st.markdown(f"Your favorite command is **{favorite_command}** 🎈")

        .. output::
           https://doc-data-editor1.streamlit.app/
           height: 450px

        """

        data_format = type_util.determine_data_format(data)
        if data_format == DataFormat.UNKNOWN:
            raise StreamlitAPIException(
                f"The data type ({type(data).__name__}) or format is not supported by the data editor. "
                "Please convert your data into a Pandas Dataframe or another supported data format."
            )

        # The dataframe should always be a copy of the original data
        # since we will apply edits directly to it.
        data_df = type_util.convert_anything_to_df(data, ensure_copy=True)

        # Check if the index is supported.
        if not _is_supported_index(data_df.index):
            raise StreamlitAPIException(
                f"The type of the dataframe index - {type(data_df.index).__name__} - is not "
                "yet supported by the data editor."
            )

        column_config_mapping = process_config_mapping(column_config)
        _apply_data_specific_configs(column_config_mapping, data_df, data_format)

        # Temporary workaround: We hide range indices if num_rows is dynamic.
        # since the current way of handling this index during editing is a bit confusing.
        if isinstance(data_df.index, pd.RangeIndex) and num_rows == "dynamic":
            if INDEX_IDENTIFIER not in column_config_mapping:
                column_config_mapping[INDEX_IDENTIFIER] = {}
            column_config_mapping[INDEX_IDENTIFIER]["hidden"] = True

        # Convert the dataframe to an arrow table which is used as the main
        # serialization format for sending the data to the frontend.
        # We also utilize the arrow schema to determine the data kinds of every column.
        arrow_table = pa.Table.from_pandas(data_df)

        # Determine the dataframe schema which is required for parsing edited values
        # and for checking type compatibilities.
        dataframe_schema = determine_dataframe_schema(data_df, arrow_table.schema)

        # Check if all configured column types are compatible with the underlying data.
        # Throws an exception if any of the configured types are incompatible.
        _check_type_compatibilities(data_df, column_config_mapping, dataframe_schema)

        proto = ArrowProto()

        proto.use_container_width = use_container_width

        if width:
            proto.width = width
        if height:
            proto.height = height

        proto.disabled = disabled
        proto.editing_mode = (
            ArrowProto.EditingMode.DYNAMIC
            if num_rows == "dynamic"
            else ArrowProto.EditingMode.FIXED
        )
        proto.form_id = current_form_id(self.dg)

        if type_util.is_pandas_styler(data):
            # Pandas styler will only work for non-editable/disabled columns.
            delta_path = self.dg._get_delta_path_str()
            default_uuid = str(hash(delta_path))
            marshall_styler(proto, data, default_uuid)

        proto.data = type_util.pyarrow_table_to_bytes(arrow_table)

        marshall_column_config(proto, column_config_mapping)

        serde = DataEditorSerde()

        widget_state = register_widget(
            "data_editor",
            proto,
            user_key=to_key(key),
            on_change_handler=on_change,
            args=args,
            kwargs=kwargs,
            deserializer=serde.deserialize,
            serializer=serde.serialize,
            ctx=get_script_run_ctx(),
        )

        _apply_dataframe_edits(data_df, widget_state.value, dataframe_schema)
        self.dg._enqueue("arrow_data_frame", proto)
        return type_util.convert_df_to_data_format(data_df, data_format)

    @property
    def dg(self) -> "DeltaGenerator":
        """Get our DeltaGenerator."""
        return cast("DeltaGenerator", self)
