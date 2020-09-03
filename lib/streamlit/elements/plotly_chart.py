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

"""Streamlit support for Plotly charts."""

import json
import urllib.parse

from streamlit import caching
from streamlit import type_util

from streamlit.logger import get_logger
from streamlit.proto.PlotlyChart_pb2 import PlotlyChart as PlotlyChartProto

LOGGER = get_logger(__name__)

SHARING_MODES = set(
    [
        # This means the plot will be sent to the Streamlit app rather than to
        # Plotly.
        "streamlit",
        # The three modes below are for plots that should be hosted in Plotly.
        # These are the names Plotly uses for them.
        "private",
        "public",
        "secret",
    ]
)


class PlotlyMixin:
    def plotly_chart(
        dg,
        figure_or_data,
        width=0,
        height=0,
        use_container_width=False,
        sharing="streamlit",
        **kwargs,
    ):
        """Display an interactive Plotly chart.

        Plotly is a charting library for Python. The arguments to this function
        closely follow the ones for Plotly's `plot()` function. You can find
        more about Plotly at https://plot.ly/python.

        Parameters
        ----------
        figure_or_data : plotly.graph_objs.Figure, plotly.graph_objs.Data,
            dict/list of plotly.graph_objs.Figure/Data

            See https://plot.ly/python/ for examples of graph descriptions.

        width : int
            Deprecated. If != 0 (default), will show an alert.
            From now on you should set the width directly in the figure.
            Please refer to the Plotly documentation for details.

        height : int
            Deprecated. If != 0 (default), will show an alert.
            From now on you should set the height directly in the figure.
            Please refer to the Plotly documentation for details.

        use_container_width : bool
            If True, set the chart width to the column width. This takes
            precedence over the figure's native `width` value.

        sharing : {'streamlit', 'private', 'secret', 'public'}
            Use 'streamlit' to insert the plot and all its dependencies
            directly in the Streamlit app, which means it works offline too.
            This is the default.
            Use any other sharing mode to send the app to Plotly's servers,
            and embed the result into the Streamlit app. See
            https://plot.ly/python/privacy/ for more. Note that these sharing
            modes require a Plotly account.

        **kwargs
            Any argument accepted by Plotly's `plot()` function.


        To show Plotly charts in Streamlit, just call `st.plotly_chart`
        wherever you would call Plotly's `py.plot` or `py.iplot`.

        Example
        -------

        The example below comes straight from the examples at
        https://plot.ly/python:

        >>> import streamlit as st
        >>> import plotly.figure_factory as ff
        >>> import numpy as np
        >>>
        >>> # Add histogram data
        >>> x1 = np.random.randn(200) - 2
        >>> x2 = np.random.randn(200)
        >>> x3 = np.random.randn(200) + 2
        >>>
        >>> # Group data together
        >>> hist_data = [x1, x2, x3]
        >>>
        >>> group_labels = ['Group 1', 'Group 2', 'Group 3']
        >>>
        >>> # Create distplot with custom bin_size
        >>> fig = ff.create_distplot(
        ...         hist_data, group_labels, bin_size=[.1, .25, .5])
        >>>
        >>> # Plot!
        >>> st.plotly_chart(fig, use_container_width=True)

        .. output::
           https://share.streamlit.io/0.56.0-xTAd/index.html?id=TuP96xX8JnsoQeUGAPjkGQ
           height: 400px

        """
        dg = dg._active_dg
        # NOTE: "figure_or_data" is the name used in Plotly's .plot() method
        # for their main parameter. I don't like the name, but it's best to
        # keep it in sync with what Plotly calls it.
        import streamlit.elements.plotly_chart as plotly_chart

        if width != 0 and height != 0:
            import streamlit as st

            st.warning(
                "The `width` and `height` arguments in `st.plotly_chart` are deprecated and will be removed on 2020-03-04. To set these values, you should instead use Plotly's native arguments as described at https://plot.ly/python/setting-graph-size/"
            )
        elif width != 0:
            import streamlit as st

            st.warning(
                "The `width` argument in `st.plotly_chart` is deprecated and will be removed on 2020-03-04. To set the width, you should instead use Plotly's native `width` argument as described at https://plot.ly/python/setting-graph-size/"
            )
        elif height != 0:
            import streamlit as st

            st.warning(
                "The `height` argument in `st.plotly_chart` is deprecated and will be removed on 2020-03-04. To set the height, you should instead use Plotly's native `height` argument as described at https://plot.ly/python/setting-graph-size/"
            )

        plotly_chart_proto = PlotlyChartProto()
        marshall(
            plotly_chart_proto, figure_or_data, use_container_width, sharing, **kwargs
        )
        return dg._enqueue("plotly_chart", plotly_chart_proto)  # type: ignore


def marshall(proto, figure_or_data, use_container_width, sharing, **kwargs):
    """Marshall a proto with a Plotly spec.

    See DeltaGenerator.plotly_chart for docs.
    """
    # NOTE: "figure_or_data" is the name used in Plotly's .plot() method
    # for their main parameter. I don't like the name, but its best to keep
    # it in sync with what Plotly calls it.

    import plotly.tools

    if type_util.is_type(figure_or_data, "matplotlib.figure.Figure"):
        figure = plotly.tools.mpl_to_plotly(figure_or_data)

    else:
        figure = plotly.tools.return_figure_from_figure_or_data(
            figure_or_data, validate_figure=True
        )

    if not isinstance(sharing, str) or sharing.lower() not in SHARING_MODES:
        raise ValueError("Invalid sharing mode for Plotly chart: %s" % sharing)

    proto.use_container_width = use_container_width

    if sharing == "streamlit":
        import plotly.utils

        config = dict(kwargs.get("config", {}))
        # Copy over some kwargs to config dict. Plotly does the same in plot().
        config.setdefault("showLink", kwargs.get("show_link", False))
        config.setdefault("linkText", kwargs.get("link_text", False))

        proto.figure.spec = json.dumps(figure, cls=plotly.utils.PlotlyJSONEncoder)
        proto.figure.config = json.dumps(config)

    else:
        url = _plot_to_url_or_load_cached_url(
            figure, sharing=sharing, auto_open=False, **kwargs
        )
        proto.url = _get_embed_url(url)


@caching.cache
def _plot_to_url_or_load_cached_url(*args, **kwargs):
    """Call plotly.plot wrapped in st.cache.

    This is so we don't unecessarily upload data to Plotly's SASS if nothing
    changed since the previous upload.
    """
    try:
        # Plotly 4 changed its main package.
        import chart_studio.plotly as ply
    except ImportError:
        import plotly.plotly as ply

    return ply.plot(*args, **kwargs)


def _get_embed_url(url):
    parsed_url = urllib.parse.urlparse(url)

    # Plotly's embed URL is the normal URL plus ".embed".
    # (Note that our use namedtuple._replace is fine because that's not a
    # private method! It just has an underscore to avoid clashing with the
    # tuple field names)
    parsed_embed_url = parsed_url._replace(path=parsed_url.path + ".embed")

    return urllib.parse.urlunparse(parsed_embed_url)
