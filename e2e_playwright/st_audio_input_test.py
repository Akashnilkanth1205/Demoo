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
from e2e_playwright.shared.app_utils import (
    check_top_level_class,
    click_form_button,
    get_element_by_key,
)


def test_audio_input_renders(app: Page):
    audio_input_elements = app.get_by_test_id("stAudioInput")
    expect(audio_input_elements).to_have_count(3)

    expect(audio_input_elements.nth(0)).to_be_visible()
    expect(audio_input_elements.nth(1)).to_be_visible()
    expect(audio_input_elements.nth(2)).to_be_visible()


def test_check_top_level_class(app: Page):
    """Check that the top level class is correctly set."""
    check_top_level_class(app, "stAudioInput")


def test_custom_css_class_via_key(app: Page):
    """Test that the element can have a custom css class via the key argument."""
    expect(get_element_by_key(app, "the_audio_input")).to_be_visible()


def test_snapshots(themed_app: Page, assert_snapshot: ImageCompareFunction):
    audio_input_element = themed_app.get_by_test_id("stAudioInput").first

    assert_snapshot(audio_input_element, name="st_audio_input_default")


@pytest.mark.only_browser("chromium")
def test_audio_input_works_in_forms(app: Page):
    app.context.grant_permissions(["microphone"])

    expect(app.get_by_text("Audio Input in Form: None")).to_be_visible()

    form_audio_input = app.get_by_test_id("stAudioInput").nth(1)
    form_audio_input.get_by_role("button", name="Record").click()
    app.wait_for_timeout(1000)
    form_audio_input.get_by_role("button", name="Stop recording").click()

    expect(app.get_by_text("Audio Input in Form: None")).to_be_visible()

    click_form_button(app, "Submit")
    wait_for_app_run(app)

    expect(app.get_by_text("Audio Input in Form: None")).not_to_be_visible()


@pytest.mark.only_browser("chromium")
def test_audio_input_works_with_fragments(app: Page):
    app.context.grant_permissions(["microphone"])

    expect(app.get_by_text("Runs: 1")).to_be_visible()
    expect(app.get_by_text("Audio Input in Fragment: None")).to_be_visible()

    fragment_audio_input = app.get_by_test_id("stAudioInput").nth(2)
    fragment_audio_input.get_by_role("button", name="Record").click()
    app.wait_for_timeout(1000)
    fragment_audio_input.get_by_role("button", name="Stop recording").click()
    wait_for_app_run(app)

    expect(app.get_by_text("Audio Input in Fragment: None")).not_to_be_visible()
    expect(app.get_by_text("Runs: 1")).to_be_visible()

    fragment_audio_input.get_by_role("button", name="Clear recording").click()
    wait_for_app_run(app)

    expect(app.get_by_text("Runs: 1")).to_be_visible()


@pytest.mark.only_browser("chromium")
def test_audio_input_basic_flow(app: Page):
    app.context.grant_permissions(["microphone"])

    app.get_by_text("Audio Input 1: False").to_be_visible()
    audio_input = app.get_by_test_id("stAudioInput").first

    expect(
        app.get_by_text("This app would like to use your microphone.").first
    ).not_to_be_visible()

    record_button = app.get_by_role("button", name="Record").first
    clock = audio_input.get_by_test_id("stAudioInputWaveformTimeCode")

    expect(clock).to_have_text("00:00")

    record_button.click()

    stop_button = audio_input.get_by_role("button", name="Stop recording").first
    expect(stop_button).to_be_visible()

    app.wait_for_timeout(1000)

    stop_button.click()

    wait_for_app_run(app)
    app.get_by_text("Audio Input 1: True").to_be_visible()

    play_button = audio_input.get_by_role("button", name="Play").first

    expect(clock).not_to_have_text("00:00")

    play_button.click()

    pause_button = audio_input.get_by_role("button", name="Pause").first
    expect(pause_button).to_be_visible()

    pause_button.click()

    expect(play_button).to_be_visible()

    audio_input.hover()

    clear_button = audio_input.get_by_role("button", name="Clear recording").first
    expect(clear_button).to_be_visible()

    clear_button.click()

    expect(audio_input.get_by_role("button", name="Record").first).to_be_visible()
    expect(clock).to_have_text("00:00")
