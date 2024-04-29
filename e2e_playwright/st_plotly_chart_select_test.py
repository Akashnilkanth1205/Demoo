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

import pytest
from playwright.sync_api import Page, expect

from e2e_playwright.conftest import ImageCompareFunction, wait_for_app_run

# def test_box_select_on_scatter_chart_displays_a_df(app: Page):
#     chart = app.locator(".stPlotlyChart").nth(0)
#     expect(chart).to_be_visible()
#     chart.hover()
#     app.mouse.down()
#     app.mouse.move(50, 50)
#     app.mouse.down()
#     app.mouse.move(150, 150)
#     app.mouse.up()
#     wait_for_app_run(app)
#     expect(app.get_by_test_id("stDataFrame")).to_have_count(1)


# def test_lasso_select_on_line_chart_displays_a_df(app: Page):
#     chart = app.locator(".stPlotlyChart").nth(1)
#     chart.scroll_into_view_if_needed()
#     expect(chart).to_be_visible()
#     chart.hover()
#     app.mouse.down()
#     app.mouse.move(350, 350)
#     app.mouse.move(375, 375)
#     app.mouse.move(400, 400)
#     app.mouse.move(435, 500)
#     app.mouse.up()
#     wait_for_app_run(app)
#     expect(app.get_by_test_id("stDataFrame")).to_have_count(1)


# # This test could be flakey because https://github.com/plotly/plotly.js/issues/6898
# def test_click_on_bar_chart_displays_a_df_and_double_click_resets_properly(
#     app: Page, assert_snapshot: ImageCompareFunction
# ):
#     chart = app.locator(".stPlotlyChart").nth(2)
#     chart.scroll_into_view_if_needed()
#     expect(chart).to_be_visible()
#     chart.hover()
#     app.mouse.down()
#     app.mouse.up()
#     wait_for_app_run(app, wait_delay=3000)
#     expect(app.get_by_test_id("stDataFrame")).to_have_count(1)
#     assert_snapshot(
#         app.get_by_test_id("stDataFrame"), name="st_plotly_chart-single_select_df"
#     )
#     assert_snapshot(chart, name="st_plotly_chart-single_select")

#     app.keyboard.down("Shift")
#     app.mouse.move(445, 375)
#     app.mouse.down()
#     app.mouse.up()
#     wait_for_app_run(app, wait_delay=3000)
#     assert_snapshot(chart, name="st_plotly_chart-double_select")
#     assert_snapshot(
#         app.get_by_test_id("stDataFrame"), name="st_plotly_chart-double_select_df"
#     )

#     chart.scroll_into_view_if_needed()
#     chart.hover()
#     app.mouse.dblclick(400, 400)
#     wait_for_app_run(app, 3000)
#     expect(app.get_by_test_id("stDataFrame")).to_have_count(0)
#     assert_snapshot(chart, name="st_plotly_chart-bar_chart_reset")


# def test_box_select_on_stacked_bar_chart_displays_a_df(app: Page):
#     chart = app.locator(".stPlotlyChart").nth(3)
#     chart.scroll_into_view_if_needed()
#     expect(chart).to_be_visible()
#     chart.hover()
#     app.mouse.down()
#     app.mouse.move(50, 50)
#     app.mouse.down()
#     app.mouse.move(150, 150)
#     app.mouse.up()
#     wait_for_app_run(app)
#     expect(app.get_by_test_id("stDataFrame")).to_have_count(1)


# This test could be flakey because https://github.com/plotly/plotly.js/issues/6898
# Mapbox doesn't load on firefox so just test on chrome for now
@pytest.mark.only_browser("chromium")
def test_box_select_on_choroleth_chart_displays_a_df(app: Page):
    chart = app.locator(".stPlotlyChart").nth(4)
    chart.scroll_into_view_if_needed()
    expect(chart).to_be_visible()
    chart.hover()
    app.mouse.down()
    app.mouse.move(50, 50)
    app.mouse.move(150, 150)
    app.mouse.up()
    expect(app.get_by_test_id("stDataFrame")).to_have_count(1)


# TODO(willhuang1997): Looks like webkit is not working but it is working locally
# @pytest.mark.only_browser("chromium")
def test_lasso_select_on_histogram_chart_displays_a_df_and_resets_when_double_clicked(
    app: Page, assert_snapshot: ImageCompareFunction
):
    chart = app.locator(".stPlotlyChart").nth(5)
    chart.scroll_into_view_if_needed()
    expect(chart).to_be_visible()
    chart.hover()
    app.mouse.down()
    app.mouse.move(350, 350)
    app.mouse.move(375, 375)
    app.mouse.move(400, 400)
    app.mouse.move(435, 500)
    app.mouse.up()
    wait_for_app_run(app, 3000)
    expect(app.get_by_test_id("stDataFrame")).to_have_count(1)

    chart = app.locator(".stPlotlyChart").nth(5)
    chart.scroll_into_view_if_needed()

    app.mouse.dblclick(400, 400)
    wait_for_app_run(app, 3000)
    chart = app.locator(".stPlotlyChart").nth(5)
    chart.scroll_into_view_if_needed()
    assert_snapshot(chart, name="st_plotly_chart-reset")


# def test_double_click_select_mode_doesnt_reset_zoom(
#     app: Page, assert_snapshot: ImageCompareFunction
# ):
#     chart = app.locator(".stPlotlyChart").nth(0)
#     expect(chart).to_be_visible()
#     chart.hover()
#     app.mouse.down()
#     app.mouse.move(50, 50)
#     app.mouse.down()
#     app.mouse.move(150, 150)
#     app.mouse.up()
#     wait_for_app_run(app)
#     expect(app.get_by_test_id("stDataFrame")).to_have_count(1)

#     app.locator('[data-title="Zoom in"]').nth(0).click()
#     app.mouse.dblclick(350, 350)
#     wait_for_app_run(app, 3000)
#     assert_snapshot(chart, name="st_plotly_chart-zoomed_in_reset")


# def test_double_click_pan_mode_resets_zoom_and_doesnt_rerun(
#     app: Page, assert_snapshot: ImageCompareFunction
# ):
#     chart = app.locator(".stPlotlyChart").nth(0)
#     expect(chart).to_be_visible()
#     chart.hover()
#     app.mouse.down()
#     app.mouse.move(50, 50)
#     app.mouse.down()
#     app.mouse.move(150, 150)
#     app.mouse.up()
#     wait_for_app_run(app)
#     expect(app.get_by_test_id("stDataFrame")).to_have_count(1)

#     app.locator('[data-title="Zoom in"]').nth(0).click()
#     app.locator('[data-title="Pan"]').nth(0).click()
#     app.mouse.down()
#     app.mouse.move(450, 450)
#     app.mouse.move(350, 350)
#     app.mouse.up()
#     assert_snapshot(chart, name="st_plotly_chart-panned")
#     app.mouse.dblclick(675, 400)
#     assert_snapshot(chart, name="st_plotly_chart-panned_reset")


# def test_selection_state_remains_after_unmounting(
#     app: Page, assert_snapshot: ImageCompareFunction
# ):
#     chart = app.locator(".stPlotlyChart").nth(6)
#     expect(chart).to_be_visible()
#     chart.scroll_into_view_if_needed()
#     chart.hover()
#     app.mouse.down()
#     app.mouse.move(350, 350)
#     app.mouse.move(450, 450)
#     app.mouse.up()
#     wait_for_app_run(app)

#     app.get_by_test_id("stButton").locator("button").click()
#     wait_for_app_run(app, 4000)

#     chart = app.locator(".stPlotlyChart").nth(6)
#     expect(chart).to_be_visible()
#     assert_snapshot(chart, name="st_plotly_chart-unmounted_still_has_selection")
