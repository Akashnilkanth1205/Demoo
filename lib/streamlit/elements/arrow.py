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

import json
from dataclasses import dataclass
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Literal,
    TypedDict,
    Union,
    cast,
    overload,
)

from typing_extensions import TypeAlias

from streamlit import type_util
from streamlit.elements.form import current_form_id
from streamlit.elements.lib.column_config_utils import (
    INDEX_IDENTIFIER,
    ColumnConfigMappingInput,
    apply_data_specific_configs,
    marshall_column_config,
    process_config_mapping,
    update_column_config,
)
from streamlit.elements.lib.pandas_styler_utils import marshall_styler
from streamlit.elements.utils import check_callback_rules, check_session_state_rules
from streamlit.proto.Arrow_pb2 import Arrow as ArrowProto
from streamlit.runtime.metrics_util import gather_metrics
from streamlit.runtime.scriptrunner import get_script_run_ctx
from streamlit.runtime.state import register_widget
from streamlit.runtime.state.common import compute_widget_id
from streamlit.type_util import Key, to_key

if TYPE_CHECKING:
    import pyarrow as pa
    from numpy import ndarray
    from pandas import DataFrame, Index, Series
    from pandas.io.formats.style import Styler

    from streamlit.delta_generator import DeltaGenerator

Data: TypeAlias = Union[
    "DataFrame",
    "Series",
    "Styler",
    "Index",
    "pa.Table",
    "ndarray",
    Iterable,
    Dict[str, List[Any]],
    None,
]


class SelectState(TypedDict, total=False):
    """
    A dictionary representing the current selection state of the dataframe.

    Attributes
    ----------
    rows
        The selected rows in the dataframe.
    """

    rows: list[int]


class SelectionState(TypedDict, total=False):
    """
    A dictionary representing the current selection state of the dataframe.

    Attributes
    ----------
    select : SelectState
        The state of the `on_select` event.
    """

    select: SelectionState


@dataclass
class DataframeSelectionSerde:
    """DataframeSelectionSerde is used to serialize and deserialize the dataframe selection state."""

    def deserialize(self, ui_value: str | None, widget_id: str = "") -> SelectionState:
        selection_state: SelectionState = (
            {
                "select": {
                    "rows": [],
                },
            }
            if ui_value is None
            else json.loads(ui_value)
        )

        if "select" not in selection_state:
            selection_state["select"] = {
                "rows": [],
            }

        return selection_state

    def serialize(self, editing_state: SelectionState) -> str:
        return json.dumps(editing_state, default=str)


class ArrowMixin:
    @overload
    def dataframe(
        self,
        data: Data = None,
        width: int | None = None,
        height: int | None = None,
        *,
        use_container_width: bool = False,
        hide_index: bool | None = None,
        column_order: Iterable[str] | None = None,
        column_config: ColumnConfigMappingInput | None = None,
        key: Key | None = None,
        on_select: Literal[False] = False,
        selection_mode: Literal["single-row", "multi-row"] = "single-row",
    ) -> DeltaGenerator:
        ...

    @overload
    def dataframe(
        self,
        data: Data = None,
        width: int | None = None,
        height: int | None = None,
        *,
        use_container_width: bool = False,
        hide_index: bool | None = None,
        column_order: Iterable[str] | None = None,
        column_config: ColumnConfigMappingInput | None = None,
        key: Key | None = None,
        on_select: Callable[..., None] | Literal[True] = True,
        selection_mode: Literal["single-row", "multi-row"] = "single-row",
    ) -> SelectionState:
        ...

    @gather_metrics("dataframe")
    def dataframe(
        self,
        data: Data = None,
        width: int | None = None,
        height: int | None = None,
        *,
        use_container_width: bool = False,
        hide_index: bool | None = None,
        column_order: Iterable[str] | None = None,
        column_config: ColumnConfigMappingInput | None = None,
        key: Key | None = None,
        on_select: Callable[..., None] | bool = False,
        selection_mode: Literal["single-row", "multi-row"] = "single-row",
    ) -> DeltaGenerator | SelectionState:
        """Display a dataframe as an interactive table.

        This command works with dataframes from Pandas, PyArrow, Snowpark, and PySpark.
        It can also display several other types that can be converted to dataframes,
        e.g. numpy arrays, lists, sets and dictionaries.

        Parameters
        ----------
        data : pandas.DataFrame, pandas.Series, pandas.Styler, pandas.Index, pyarrow.Table, numpy.ndarray, pyspark.sql.DataFrame, snowflake.snowpark.dataframe.DataFrame, snowflake.snowpark.table.Table, Iterable, dict, or None
            The data to display.

            If 'data' is a pandas.Styler, it will be used to style its
            underlying DataFrame. Streamlit supports custom cell
            values and colors. It does not support some of the more exotic
            pandas styling features, like bar charts, hovering, and captions.

        width : int or None
            Desired width of the dataframe expressed in pixels. If None, the width
            will be automatically calculated based on the column content.

        height : int or None
            Desired height of the dataframe expressed in pixels. If None, a
            default height is used.

        use_container_width : bool
            If True, set the dataframe width to the width of the parent container.
            This takes precedence over the width argument.

        hide_index : bool or None
            Whether to hide the index column(s). If None (default), the visibility of
            index columns is automatically determined based on the data.

        column_order : Iterable of str or None
            Specifies the display order of columns. This also affects which columns are
            visible. For example, ``column_order=("col2", "col1")`` will display 'col2'
            first, followed by 'col1', and will hide all other non-index columns. If
            None (default), the order is inherited from the original data structure.

        column_config : dict or None
            Configures how columns are displayed, e.g. their title, visibility, type, or
            format. This needs to be a dictionary where each key is a column name and
            the value is one of:

            * ``None`` to hide the column.

            * A string to set the display label of the column.

            * One of the column types defined under ``st.column_config``, e.g.
              ``st.column_config.NumberColumn("Dollar values”, format=”$ %d")`` to show
              a column as dollar amounts. See more info on the available column types
              and config options `here <https://docs.streamlit.io/library/api-reference/data/st.column_config>`_.

            To configure the index column(s), use ``_index`` as the column name.

        Examples
        --------
        >>> import streamlit as st
        >>> import pandas as pd
        >>> import numpy as np
        >>>
        >>> df = pd.DataFrame(np.random.randn(50, 20), columns=("col %d" % i for i in range(20)))
        >>>
        >>> st.dataframe(df)  # Same as st.write(df)

        .. output::
           https://doc-dataframe.streamlit.app/
           height: 410px

        You can also pass a Pandas Styler object to change the style of
        the rendered DataFrame:

        >>> import streamlit as st
        >>> import pandas as pd
        >>> import numpy as np
        >>>
        >>> df = pd.DataFrame(np.random.randn(10, 20), columns=("col %d" % i for i in range(20)))
        >>>
        >>> st.dataframe(df.style.highlight_max(axis=0))

        .. output::
           https://doc-dataframe1.streamlit.app/
           height: 410px

        Or you can customize the dataframe via ``column_config``, ``hide_index``, or ``column_order``:

        >>> import random
        >>> import pandas as pd
        >>> import streamlit as st
        >>>
        >>> df = pd.DataFrame(
        >>>     {
        >>>         "name": ["Roadmap", "Extras", "Issues"],
        >>>         "url": ["https://roadmap.streamlit.app", "https://extras.streamlit.app", "https://issues.streamlit.app"],
        >>>         "stars": [random.randint(0, 1000) for _ in range(3)],
        >>>         "views_history": [[random.randint(0, 5000) for _ in range(30)] for _ in range(3)],
        >>>     }
        >>> )
        >>> st.dataframe(
        >>>     df,
        >>>     column_config={
        >>>         "name": "App name",
        >>>         "stars": st.column_config.NumberColumn(
        >>>             "Github Stars",
        >>>             help="Number of stars on GitHub",
        >>>             format="%d ⭐",
        >>>         ),
        >>>         "url": st.column_config.LinkColumn("App URL"),
        >>>         "views_history": st.column_config.LineChartColumn(
        >>>             "Views (past 30 days)", y_min=0, y_max=5000
        >>>         ),
        >>>     },
        >>>     hide_index=True,
        >>> )

        .. output::
           https://doc-dataframe-config.streamlit.app/
           height: 350px

        """
        import pyarrow as pa

        key = to_key(key)
        if on_select:
            if callable(on_select):
                check_callback_rules(self.dg, on_select)
            check_session_state_rules(default_value=None, key=key, writes_allowed=False)

        # Convert the user provided column config into the frontend compatible format:
        column_config_mapping = process_config_mapping(column_config)

        proto = ArrowProto()
        proto.use_container_width = use_container_width
        if width:
            proto.width = width
        if height:
            proto.height = height

        if column_order:
            proto.column_order[:] = column_order

        proto.editing_mode = ArrowProto.EditingMode.READ_ONLY

        if isinstance(data, pa.Table):
            # For pyarrow tables, we can just serialize the table directly
            proto.data = type_util.pyarrow_table_to_bytes(data)
        else:
            # For all other data formats, we need to convert them to a pandas.DataFrame
            # thereby, we also apply some data specific configs

            # Determine the input data format
            data_format = type_util.determine_data_format(data)

            if type_util.is_pandas_styler(data):
                # If pandas.Styler uuid is not provided, a hash of the position
                # of the element will be used. This will cause a rerender of the table
                # when the position of the element is changed.
                delta_path = self.dg._get_delta_path_str()
                default_uuid = str(hash(delta_path))
                marshall_styler(proto, data, default_uuid)

            # Convert the input data into a pandas.DataFrame
            data_df = type_util.convert_anything_to_df(data, ensure_copy=False)
            apply_data_specific_configs(
                column_config_mapping,
                data_df,
                data_format,
                check_arrow_compatibility=False,
            )
            # Serialize the data to bytes:
            proto.data = type_util.data_frame_to_bytes(data_df)

        if hide_index is not None:
            update_column_config(
                column_config_mapping, INDEX_IDENTIFIER, {"hidden": hide_index}
            )
        marshall_column_config(proto, column_config_mapping)

        if on_select:
            proto.row_selection_mode = (
                ArrowProto.RowSelectionMode.MULTI
                if selection_mode == "multi-row"
                else ArrowProto.RowSelectionMode.SINGLE
            )

            # We want to do this as early as possible to avoid introducing nondeterminism,
            # but it isn't clear how much processing is needed to have the data in a
            # format that will hash consistently, so we do it late here to have it
            # as close as possible to how it used to be.
            ctx = get_script_run_ctx()
            proto.id = compute_widget_id(
                "dataframe",
                user_key=key,
                data=proto.data,
                width=width,
                height=height,
                use_container_width=use_container_width,
                column_order=column_order,
                column_config_mapping=str(column_config_mapping),
                key=key,
                form_id=current_form_id(self.dg),
                page=ctx.page_script_hash if ctx else None,
            )
            proto.form_id = current_form_id(self.dg)

            serde = DataframeSelectionSerde()
            widget_state = register_widget(
                "dataframe",
                proto,
                user_key=key,
                on_change_handler=on_select if callable(on_select) else None,
                deserializer=serde.deserialize,
                serializer=serde.serialize,
                ctx=ctx,
            )
            self.dg._enqueue("arrow_data_frame", proto)
            return widget_state.value
        else:
            proto.row_selection_mode = ArrowProto.RowSelectionMode.NONE
            return self.dg._enqueue("arrow_data_frame", proto)

    @gather_metrics("table")
    def table(self, data: Data = None) -> DeltaGenerator:
        """Display a static table.

        This differs from ``st.dataframe`` in that the table in this case is
        static: its entire contents are laid out directly on the page.

        Parameters
        ----------
        data : pandas.DataFrame, pandas.Styler, pyarrow.Table, numpy.ndarray, pyspark.sql.DataFrame, snowflake.snowpark.dataframe.DataFrame, snowflake.snowpark.table.Table, Iterable, dict, or None
            The table data.

        Example
        -------
        >>> import streamlit as st
        >>> import pandas as pd
        >>> import numpy as np
        >>>
        >>> df = pd.DataFrame(np.random.randn(10, 5), columns=("col %d" % i for i in range(5)))
        >>>
        >>> st.table(df)

        .. output::
           https://doc-table.streamlit.app/
           height: 480px

        """

        # Check if data is uncollected, and collect it but with 100 rows max, instead of 10k rows, which is done in all other cases.
        # Avoid this and use 100 rows in st.table, because large tables render slowly, take too much screen space, and can crush the app.
        if type_util.is_snowpark_data_object(data) or type_util.is_type(
            data, type_util._PYSPARK_DF_TYPE_STR
        ):
            data = type_util.convert_anything_to_df(data, max_unevaluated_rows=100)

        # If pandas.Styler uuid is not provided, a hash of the position
        # of the element will be used. This will cause a rerender of the table
        # when the position of the element is changed.
        delta_path = self.dg._get_delta_path_str()
        default_uuid = str(hash(delta_path))

        proto = ArrowProto()
        marshall(proto, data, default_uuid)
        return self.dg._enqueue("arrow_table", proto)

    @gather_metrics("add_rows")
    def add_rows(self, data: Data = None, **kwargs) -> DeltaGenerator | None:
        """Concatenate a dataframe to the bottom of the current one.

        Parameters
        ----------
        data : pandas.DataFrame, pandas.Styler, pyarrow.Table, numpy.ndarray, pyspark.sql.DataFrame, snowflake.snowpark.dataframe.DataFrame, Iterable, dict, or None
            Table to concat. Optional.

        **kwargs : pandas.DataFrame, numpy.ndarray, Iterable, dict, or None
            The named dataset to concat. Optional. You can only pass in 1
            dataset (including the one in the data parameter).

        Example
        -------
        >>> import streamlit as st
        >>> import pandas as pd
        >>> import numpy as np
        >>>
        >>> df1 = pd.DataFrame(np.random.randn(50, 20), columns=("col %d" % i for i in range(20)))
        >>>
        >>> my_table = st.table(df1)
        >>>
        >>> df2 = pd.DataFrame(np.random.randn(50, 20), columns=("col %d" % i for i in range(20)))
        >>>
        >>> my_table.add_rows(df2)
        >>> # Now the table shown in the Streamlit app contains the data for
        >>> # df1 followed by the data for df2.

        You can do the same thing with plots. For example, if you want to add
        more data to a line chart:

        >>> # Assuming df1 and df2 from the example above still exist...
        >>> my_chart = st.line_chart(df1)
        >>> my_chart.add_rows(df2)
        >>> # Now the chart shown in the Streamlit app contains the data for
        >>> # df1 followed by the data for df2.

        And for plots whose datasets are named, you can pass the data with a
        keyword argument where the key is the name:

        >>> my_chart = st.vega_lite_chart({
        ...     'mark': 'line',
        ...     'encoding': {'x': 'a', 'y': 'b'},
        ...     'datasets': {
        ...       'some_fancy_name': df1,  # <-- named dataset
        ...      },
        ...     'data': {'name': 'some_fancy_name'},
        ... }),
        >>> my_chart.add_rows(some_fancy_name=df2)  # <-- name used as keyword

        """
        return self.dg._arrow_add_rows(data, **kwargs)

    @property
    def dg(self) -> DeltaGenerator:
        """Get our DeltaGenerator."""
        return cast("DeltaGenerator", self)


def marshall(proto: ArrowProto, data: Data, default_uuid: str | None = None) -> None:
    """Marshall pandas.DataFrame into an Arrow proto.

    Parameters
    ----------
    proto : proto.Arrow
        Output. The protobuf for Streamlit Arrow proto.

    data : pandas.DataFrame, pandas.Styler, pyarrow.Table, numpy.ndarray, pyspark.sql.DataFrame, snowflake.snowpark.DataFrame, Iterable, dict, or None
        Something that is or can be converted to a dataframe.

    default_uuid : str | None
        If pandas.Styler UUID is not provided, this value will be used.
        This attribute is optional and only used for pandas.Styler, other elements
        (e.g. charts) can ignore it.

    """
    import pyarrow as pa

    if type_util.is_pandas_styler(data):
        # default_uuid is a string only if the data is a `Styler`,
        # and `None` otherwise.
        assert isinstance(
            default_uuid, str
        ), "Default UUID must be a string for Styler data."
        marshall_styler(proto, data, default_uuid)

    if isinstance(data, pa.Table):
        proto.data = type_util.pyarrow_table_to_bytes(data)
    else:
        df = type_util.convert_anything_to_df(data)
        proto.data = type_util.data_frame_to_bytes(df)
