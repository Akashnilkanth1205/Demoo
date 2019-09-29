# -*- coding: utf-8 -*-
# Copyright 2018-2019 Streamlit Inc.
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

"""A "Hello World" app."""
from __future__ import division

import streamlit as st
from streamlit.logger import get_logger
import inspect
from collections import OrderedDict
import urllib
import textwrap

LOGGER = get_logger(__name__)


def intro():
    import requests
    from PIL import Image
    from io import BytesIO

    @st.cache(show_spinner=False)
    def load_image(url):
        img = Image.open(BytesIO(requests.get(url).content))
        old_width, old_height = img.size
        new_width = 1024
        new_height = int(old_height * new_width / old_width)
        return img.resize((new_width, new_height), Image.BICUBIC)

    st.sidebar.success("Select a demo above.")

    st.markdown(
        """
            Streamlit is a completely free and open-source library to create
            web tools for Machine Learning and Data Science projects.

            **Select a demo from the menu on the left** to see Streamlit in action.
        """
    )

    image_location = st.empty()

    st.markdown(
        """
            ### Want to learn more?

            - [Get started with help](https://streamlit.io/docs)
            - [Ask our community a question](https://discuss.streamlit.io)

            ### See more complex demos

            - Use a neural net to [analyze the Udacity Self-driving Car Image Dataset]
              (https://github.com/streamlit/demo-self-driving)
            - Explore a [New York City rideshare dataset]
              (https://github.com/streamlit/demo-uber-nyc-pickups)
        """
    )

    try:
        img_url = (
            "https://streamlit-demo-data.s3-us-west-2.amazonaws.com/hello-welcome.png"
        )
        img = load_image(img_url)
        image_location.image(img, use_column_width=True)
    except Exception as e:
        LOGGER.warning(e)
        LOGGER.warning(img_url)


# Turn off black formatting for this funtion to present the user with more compact code.
# fmt: off
def mapping_demo():
    """
    This demo shows how to use
    [`st.deck_gl_chart`](https://streamlit.io/docs/api.html#streamlit.deck_gl_chart)
    to display geospatial data.
    """
    import pandas as pd
    import copy, os
    from collections import OrderedDict

    @st.cache
    def from_data_file(filename):
        GITHUB_DATA = "https://raw.githubusercontent.com/streamlit/streamlit/develop/examples/"
        return pd.read_json(os.path.join(GITHUB_DATA, "data", filename))

    ALL_LAYERS = {
        "Bike Rentals": {
            "type": "HexagonLayer",
            "data": from_data_file("bike_rental_stats.json"),
            "radius": 200,
            "elevationScale": 4,
            "elevationRange": [0, 1000],
            "pickable": True,
            "extruded": True,
        },
        "Bart Stop Exits": {
            "type": "ScatterplotLayer",
            "data": from_data_file("bart_stop_stats.json"),
            "radiusScale": 0.05,
            "getRadius": "exits",
        },
        "Bart Stop Names": {
            "type": "TextLayer",
            "data": from_data_file("bart_stop_stats.json"),
            "getText": "name",
            "getColor": [0, 0, 0, 200],
            "getSize": 15,
        },
        "Outbound Flow": {
            "type": "ArcLayer",
            "data": from_data_file("bart_path_stats.json"),
            "pickable": True,
            "autoHighlight": True,
            "getStrokeWidth": 10,
            "widthScale": 0.0001,
            "getWidth": "outbound",
            "widthMinPixels": 3,
            "widthMaxPixels": 30,
        }
    }

    st.sidebar.markdown('### Map Layers')
    selected_layers = [layer for layer_name, layer in ALL_LAYERS.items()
        if st.sidebar.checkbox(layer_name, True)]
    if selected_layers:
        viewport={"latitude": 37.76, "longitude": -122.4, "zoom": 11, "pitch": 50}
        st.deck_gl_chart(viewport=viewport, layers=selected_layers)
    else:
        st.error("Please choose at least one layer above.")
# fmt: on

# Turn off black formatting for this funtion to present the user with more compact code.
# fmt: off
def fractal_demo():
    """
    This app shows how you can use Streamlit to build cool animations.
    It displays an animated fractal based on the the Julia Set. Use the slider
    to tune the level of detail.
    """
    import numpy as np

    # Interactive Streamlit elements, like these sliders, return thier value.
    # This gives you an extremely simple interaction model.
    iterations = st.sidebar.slider("Level of detail", 1, 100, 70, 1)
    separation = st.sidebar.slider("Separation", 0.7, 2.0, 0.7885)

    # Non-interactive elements return a placeholder to thier location
    # in the app. Here we're storing progress_bar to update it later.
    progress_bar = st.sidebar.progress(0)

    # These two elements will be filled in later, so we create a placeholder
    # for them using st.empty()
    frame_text = st.sidebar.empty()
    image = st.empty()

    m, n, s = 480, 320, 200
    x = np.linspace(-m / s, m / s, num=m).reshape((1, m))
    y = np.linspace(-n / s, n / s, num=n).reshape((n, 1))

    for frame_num, a in enumerate(np.linspace(0.0, 4 * np.pi, 100)):
        # Here were setting value for these two elements.
        progress_bar.progress(frame_num)
        frame_text.text("Frame %i/100" % (frame_num + 1))

        # Performing some fractal wizardry.
        c = separation * np.exp(1j * a)
        Z = np.tile(x, (n, 1)) + 1j * np.tile(y, (1, m))
        C = np.full((n, m), c)
        M = np.full((n, m), True, dtype=bool)
        N = np.zeros((n, m))

        for i in range(iterations):
            Z[M] = Z[M] * Z[M] + C[M]
            M[np.abs(Z) > 2] = False
            N[M] = i

        # Update the image placeholder by calling the image() function on it.
        image.image(1.0 - (N / N.max()), use_column_width=True)

    # We clear elements by calling empty on them.
    progress_bar.empty()
    frame_text.empty()

    # Streamlit buttons automatically run the script from top to bottom.
    st.button("Re-run")


# fmt: on

# Turn off black formatting for this funtion to present the user with more compact code.
# fmt: off
def plotting_demo():
    """
    This demo illustrates a combination of plotting and animation with Streamlit.
    We're generating a bunch of random numbers in a loop for around 10 seconds.
    Enjoy!.
    """
    import time
    import numpy as np

    progress_bar = st.sidebar.progress(0)
    status_text = st.sidebar.empty()
    last_rows = np.random.randn(1, 1)
    chart = st.line_chart(last_rows)
    for i in range(1, 101):
        new_rows = last_rows[-1, :] + np.random.randn(5, 1).cumsum(axis=0)
        status_text.text("%i%% Complete" % i)
        chart.add_rows(new_rows)
        progress_bar.progress(i)
        last_rows = new_rows
        time.sleep(0.05)
    progress_bar.empty()

    # Streamlit buttons automatically run the script from top to bottom.
    st.button("Re-run")


# fmt: on

# Turn off black formatting for this funtion to present the user with more compact code.
# fmt: off
def data_frame_demo():
    """
    This demo shows how to use `st.write` to visualize Pandas DataFrames.

    (Data courtesy of the [UN Data Exlorer](http://data.un.org/Explorer.aspx).)
    """
    import sys
    import pandas as pd
    import altair as alt

    if sys.version_info[0] < 3:
        reload(sys)
        sys.setdefaultencoding("utf-8")

    @st.cache
    def get_UN_data():
        AWS_BUCKET_URL = "https://streamlit-demo-data.s3-us-west-2.amazonaws.com"
        df = pd.read_csv(AWS_BUCKET_URL + "/agri.csv.gz")
        return df.set_index("Region")

    try:
        df = get_UN_data()
    except urllib.error.URLError:
        st.error("Connection Error. This demo requires internet access")
        return

    countries = st.multiselect(
        "Choose countries", list(df.index), ["China", "United States of America"]
    )
    if not countries:
        st.error("Please select at least one country.")
        return

    "### Gross Agricultural Production ($)", df.loc[countries].sort_index()

    data = df.loc[countries].T.reset_index()
    data = pd.melt(data, id_vars=["index"]).rename(
        columns={"index": "year", "value": "Gross Agricultural Product ($)"}
    )
    chart = (
        alt.Chart(data)
        .mark_area(opacity=0.3)
        .encode(
            x="year:T",
            y=alt.Y("Gross Agricultural Product ($):Q", stack=None),
            color="Region:N",
        )
    )
    "", "", chart


# fmt: on

DEMOS = OrderedDict(
    {
        "---": intro,
        "Mapping Demo": mapping_demo,
        "DataFrame Demo": data_frame_demo,
        "Plotting Demo": plotting_demo,
        "Animation Demo": fractal_demo,
    }
)


def run():
    demo_name = st.sidebar.selectbox("Choose a demo", list(DEMOS.keys()), 0)
    demo = DEMOS[demo_name]

    if demo_name != "---":
        show_code = st.sidebar.checkbox("Show code", True)
        st.markdown("# %s" % demo_name)
        st.write(inspect.getdoc(demo))
    else:
        show_code = False
        st.write(
            """
            # Welcome to Streamlit
            ## The fastest way to build custom ML tools
            """
        )
    demo()
    if show_code:
        st.markdown("## Code")
        sourcelines, n_lines = inspect.getsourcelines(demo)
        sourcelines = remove_docstring(sourcelines)
        st.code(textwrap.dedent("".join(sourcelines)))


# This function parses the lines of a function and removes the docstring
# if found. If no docstring is found, it returns None.
def remove_docstring(lines):
    if len(lines) < 3 and '"""' not in lines[1]:
        return lines
    #  lines[2] is the first line of the docstring, past the inital """
    index = 2
    while '"""' not in lines[index]:
        index += 1
        # limit to ~100 lines, if the docstring is longer, just bail
        if index > 100:
            return lines
    # lined[index] is the closing """
    return lines[index + 1 :]


if __name__ == "__main__":
    run()
