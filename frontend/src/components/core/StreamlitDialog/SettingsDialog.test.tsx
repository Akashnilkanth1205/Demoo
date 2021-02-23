/**
 * @license
 * Copyright 2018-2021 Streamlit Inc.
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *    http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import React from "react"
import PropTypes from "prop-types"
import { createPresetThemes, lightTheme, darkTheme } from "theme"
import { shallow } from "lib/test_util"
import { Props as ContextProps } from "components/core/PageLayoutContext"
import UISelectbox from "components/shared/Dropdown"

import { SettingsDialog, Props } from "./SettingsDialog"

const mockSetTheme = jest.fn()
const mockAddThemes = jest.fn()

const getContext = (
  extend?: Partial<ContextProps>
): Partial<ContextProps> => ({
  activeTheme: lightTheme,
  setTheme: mockSetTheme,
  availableThemes: [],
  addThemes: mockAddThemes,
  ...extend,
})

// This is a workaround since enzyme does not support context yet
// https://github.com/enzymejs/enzyme/issues/2189
// @ts-ignore
SettingsDialog.contextTypes = {
  availableThemes: PropTypes.array,
  activeTheme: PropTypes.shape,
  setTheme: PropTypes.func,
  addThemes: PropTypes.func,
}

const getProps = (extend?: Partial<Props>): Props => ({
  isServerConnected: true,
  onClose: jest.fn(),
  onSave: jest.fn(),
  settings: { wideMode: false, runOnSave: false },
  allowRunOnSave: false,
  developerMode: true,
  ...extend,
})

describe("SettingsDialog", () => {
  it("renders without crashing", () => {
    const availableThemes = [lightTheme, darkTheme]
    const props = getProps()
    const context = getContext({ availableThemes })

    const wrapper = shallow(<SettingsDialog {...props} />, { context })

    expect(wrapper).toMatchSnapshot()
  })

  it("should render run on save checkbox", () => {
    const props = getProps({
      allowRunOnSave: true,
    })
    const context = getContext()
    const wrapper = shallow(<SettingsDialog {...props} />, { context })
    const checkboxes = wrapper.find("input[type='checkbox']")

    expect(checkboxes).toHaveLength(2)
    expect(wrapper.state("runOnSave")).toBe(false)

    checkboxes
      .at(0)
      .simulate("change", { target: { name: "runOnSave", checked: true } })
    wrapper.update()

    expect(wrapper.state("runOnSave")).toBe(true)
    expect(props.onSave).toHaveBeenCalled()
    // @ts-ignore
    expect(props.onSave.mock.calls[0][0].runOnSave).toBe(true)
  })

  it("should render wide mode checkbox", () => {
    const props = getProps()
    const context = getContext()
    const wrapper = shallow(<SettingsDialog {...props} />, { context })
    const checkboxes = wrapper.find("input[type='checkbox']")

    expect(checkboxes).toHaveLength(1)
    expect(wrapper.state("wideMode")).toBe(false)

    checkboxes
      .at(0)
      .simulate("change", { target: { name: "wideMode", checked: true } })
    wrapper.update()

    expect(wrapper.state("wideMode")).toBe(true)
    expect(props.onSave).toHaveBeenCalled()
    // @ts-ignore
    expect(props.onSave.mock.calls[0][0].wideMode).toBe(true)
  })

  it("should render theme selector", () => {
    const availableThemes = [lightTheme, darkTheme]
    const props = getProps()
    const context = getContext({ availableThemes })
    const wrapper = shallow(<SettingsDialog {...props} />, { context })
    const selectbox = wrapper.find(UISelectbox)
    const { options } = selectbox.props()

    expect(options).toHaveLength(2)

    expect(options).toEqual(availableThemes.map(theme => theme.name))

    selectbox.prop("onChange")(1)
    wrapper.update()
    expect(mockSetTheme).toHaveBeenCalled()
    // @ts-ignore
    expect(mockSetTheme.mock.calls[0][0]).toBe(darkTheme)
  })

  it("should show custom theme exists", () => {
    const presetThemes = createPresetThemes()
    const availableThemes = [...presetThemes, lightTheme]
    const props = getProps()
    const context = getContext({ availableThemes })
    const wrapper = shallow(<SettingsDialog {...props} />, { context })
    const selectbox = wrapper.find(UISelectbox)
    const { options } = selectbox.props()

    expect(options).toHaveLength(presetThemes.length + 1)

    expect(wrapper.find("ThemeCreator").prop("hasCustomTheme")).toBe(true)
  })

  it("should show custom theme does not exists", () => {
    const presetThemes = createPresetThemes()
    const availableThemes = [...presetThemes]
    const props = getProps()
    const context = getContext({ availableThemes })
    const wrapper = shallow(<SettingsDialog {...props} />, { context })
    const selectbox = wrapper.find(UISelectbox)
    const { options } = selectbox.props()

    expect(options).toHaveLength(presetThemes.length)

    expect(wrapper.find("ThemeCreator").prop("hasCustomTheme")).toBe(false)
  })

  it("should hide theme creator if not developer mode", () => {
    const availableThemes = [lightTheme, darkTheme]
    const props = getProps({ developerMode: false })
    const context = getContext({ availableThemes })
    const wrapper = shallow(<SettingsDialog {...props} />, { context })
    expect(wrapper.find("ThemeCreator").exists()).toBe(false)

    expect(wrapper).toMatchSnapshot()
  })
})
