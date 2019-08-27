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

import streamlit as st
import pandas as pd
import numpy as np

coords = np.random.randn(1000, 2) / [50, 50] + [37.76, -122.4]
df = pd.DataFrame(coords, columns=['lat', 'lon'])

# Basic syntax for a basic scatterplot map using deck_gl:
# st.map(df)
st.map(df)

# Similar test but specifying a custom zoom level:
# st.map(df)
st.map(df, zoom=8)
