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

"""radio unit tests."""

import numpy as np
import pandas as pd
from parameterized import parameterized

import streamlit as st
from tests import testutil


class RadioTest(testutil.DeltaGeneratorTestCase):
    """Test ability to marshall radio protos."""

    def test_just_label(self):
        """Test that it can be called with no value."""
        st.radio('the label', ('m', 'f'))

        c = self.get_delta_from_queue().new_element.radio
        self.assertEqual(c.label, 'the label')
        self.assertEqual(c.default, 0)

    def test_valid_value(self):
        """Test that valid value is an int."""
        st.radio('the label', ('m', 'f'), 1)

        c = self.get_delta_from_queue().new_element.radio
        self.assertEqual(c.label, 'the label')
        self.assertEqual(c.default, 1)

    @parameterized.expand([
        (('m', 'f'), ['m', 'f']),
        (['male', 'female'], ['male', 'female']),
        (np.array(['m', 'f']), ['m', 'f']),
        (pd.Series(np.array(['male', 'female'])), ['male', 'female']),
    ])
    def test_option_types(self, options, proto_options):
        """Test that it supports different types of options."""
        st.radio('the label', options)

        c = self.get_delta_from_queue().new_element.radio
        self.assertEqual(c.label, 'the label')
        self.assertEqual(c.default, 0)
        self.assertEqual(c.options, proto_options)

    def test_cast_options_to_string(self):
        """Test that it casts options to string."""
        arg_options = ['some str', 123, None, {}]
        proto_options = ['some str', '123', 'None', '{}']

        st.radio('the label', arg_options)

        c = self.get_delta_from_queue().new_element.radio
        self.assertEqual(c.label, 'the label')
        self.assertEqual(c.default, 0)
        self.assertEqual(c.options, proto_options)

    def test_format_function(self):
        """Test that it formats options."""
        arg_options = [{'name': 'john', 'height': 180},
                       {'name': 'lisa', 'height': 200}]
        proto_options = ['john', 'lisa']

        st.radio('the label', arg_options,
                 format_func=lambda x: x['name'])

        c = self.get_delta_from_queue().new_element.radio
        self.assertEqual(c.label, 'the label')
        self.assertEqual(c.default, 0)
        self.assertEqual(c.options, proto_options)

    @parameterized.expand([
        ((),),
        ([],),
        (np.array([]),),
        (pd.Series(np.array([])),)
    ])
    def test_no_options(self, options):
        """Test that it handles no options."""
        st.radio('the label', options)

        c = self.get_delta_from_queue().new_element.radio
        self.assertEqual(c.label, 'the label')
        self.assertEqual(c.default, 0)
        self.assertEqual(c.options, [])

    def test_invalid_value(self):
        """Test that value must be an int."""
        with self.assertRaises(TypeError):
            st.radio('the label', ('m', 'f'), '1')

    def test_invalid_value_range(self):
        """Test that value must be within the length of the options."""
        with self.assertRaises(ValueError):
            st.radio('the label', ('m', 'f'), 2)
