/**
 * @license
 * Copyright 2018-2022 Streamlit Inc.
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

import { matchers } from "@emotion/jest"
import { ExpandMore, ExpandLess } from "@emotion-icons/material-outlined"
import React from "react"
import { act } from "react-dom/test-utils"

import Icon from "src/components/shared/Icon"
import { useIsOverflowing } from "src/lib/Hooks"
import { mount, shallow } from "src/lib/test_util"

import SidebarNav, { Props } from "./SidebarNav"
import {
  StyledSidebarNavItems,
  StyledSidebarNavSeparatorContainer,
  StyledSidebarNavLink,
} from "./styled-components"

expect.extend(matchers)

jest.mock("src/lib/Hooks", () => ({
  __esModule: true,
  ...jest.requireActual("src/lib/Hooks"),
  useIsOverflowing: jest.fn(),
}))

const getProps = (props: Partial<Props> = {}): Props => ({
  appPages: [
    { pageName: "streamlit_app", scriptPath: "streamlit_app.py" },
    { pageName: "my_other_page", scriptPath: "my_other_page.py" },
  ],
  hasSidebarElements: false,
  onPageChange: jest.fn(),
  hideParentScrollbar: jest.fn(),
  ...props,
})

describe("SidebarNav", () => {
  afterEach(() => {
    useIsOverflowing.mockReset()
  })

  it("returns null if 0 appPages (may be true before the first script run)", () => {
    const wrapper = shallow(<SidebarNav {...getProps({ appPages: [] })} />)
    expect(wrapper.getElement()).toBeNull()
  })

  it("returns null if 1 appPage", () => {
    const wrapper = shallow(
      <SidebarNav
        {...getProps({ appPages: [{ pageName: "streamlit_app" }] })}
      />
    )
    expect(wrapper.getElement()).toBeNull()
  })

  it("replaces underscores with spaces in pageName", () => {
    const wrapper = shallow(<SidebarNav {...getProps()} />)

    const links = wrapper.find(StyledSidebarNavLink)

    expect(links.at(0).text()).toBe("streamlit app")
    expect(links.at(1).text()).toBe("my other page")
  })

  it("does not add separator below if there are no sidebar elements", () => {
    const wrapper = shallow(
      <SidebarNav {...getProps({ hasSidebarElements: false })} />
    )
    expect(wrapper.find(StyledSidebarNavSeparatorContainer).exists()).toBe(
      false
    )
  })

  it("adds separator below if the sidebar also has elements", () => {
    const wrapper = shallow(
      <SidebarNav {...getProps({ hasSidebarElements: true })} />
    )
    expect(wrapper.find(StyledSidebarNavSeparatorContainer).exists()).toBe(
      true
    )
  })

  it("does not render an icon when not expanded and not overflowing", () => {
    const wrapper = shallow(
      <SidebarNav {...getProps({ hasSidebarElements: true })} />
    )
    expect(wrapper.find(Icon).exists()).toBe(false)
  })

  it("renders ExpandMore icon when not expanded and overflowing", () => {
    useIsOverflowing.mockReturnValueOnce(true)
    const wrapper = shallow(
      <SidebarNav {...getProps({ hasSidebarElements: true })} />
    )

    expect(wrapper.find(Icon).props()).toHaveProperty("content", ExpandMore)
  })

  it("renders ExpandLess icon when expanded and not overflowing", () => {
    useIsOverflowing.mockReturnValueOnce(true)
    const wrapper = shallow(
      <SidebarNav {...getProps({ hasSidebarElements: true })} />
    )

    wrapper.find(StyledSidebarNavSeparatorContainer).prop("onClick")()
    expect(wrapper.find(Icon).props()).toHaveProperty("content", ExpandLess)
  })

  it("renders ExpandLess icon when expanded and overflowing", () => {
    // Have useIsOverflowing return true both before and after the nav is
    // expanded.
    useIsOverflowing.mockReturnValueOnce(true).mockReturnValueOnce(true)
    const wrapper = shallow(
      <SidebarNav {...getProps({ hasSidebarElements: true })} />
    )

    wrapper.find(StyledSidebarNavSeparatorContainer).prop("onClick")()
    expect(wrapper.find(Icon).props()).toHaveProperty("content", ExpandLess)
  })

  it("changes cursor to pointer above separator when overflowing", () => {
    useIsOverflowing.mockReturnValueOnce(true)
    // Need mount > shallow here so that toHaveStyleRule can be used.
    const wrapper = mount(
      <SidebarNav {...getProps({ hasSidebarElements: true })} />
    )

    expect(wrapper.find(StyledSidebarNavSeparatorContainer)).toHaveStyleRule(
      "cursor",
      "pointer"
    )
  })

  it("is unexpanded by default", () => {
    // Need mount > shallow here so that toHaveStyleRule can be used.
    const wrapper = mount(
      <SidebarNav {...getProps({ hasSidebarElements: true })} />
    )

    expect(wrapper.find(StyledSidebarNavItems).prop("expanded")).toBe(false)
    expect(wrapper.find("StyledSidebarNavItems")).toHaveStyleRule(
      "max-height",
      "33vh"
    )
  })

  it("does not expand when you click on the separator if there is no overflow", () => {
    const wrapper = shallow(
      <SidebarNav {...getProps({ hasSidebarElements: true })} />
    )

    wrapper.find(StyledSidebarNavSeparatorContainer).prop("onClick")()
    expect(wrapper.find(StyledSidebarNavItems).prop("expanded")).toBe(false)
  })

  it("toggles to expanded and back when the separator is clicked", () => {
    useIsOverflowing.mockReturnValueOnce(true)

    // Need mount > shallow here so that toHaveStyleRule can be used.
    const wrapper = mount(
      <SidebarNav {...getProps({ hasSidebarElements: true })} />
    )

    act(() => {
      wrapper.find(StyledSidebarNavSeparatorContainer).prop("onClick")()
    })
    wrapper.update()

    expect(wrapper.find(StyledSidebarNavItems).prop("expanded")).toBe(true)
    expect(wrapper.find(StyledSidebarNavItems)).toHaveStyleRule(
      "max-height",
      "75vh"
    )

    act(() => {
      wrapper.find(StyledSidebarNavSeparatorContainer).prop("onClick")()
    })
    wrapper.update()

    expect(wrapper.find(StyledSidebarNavItems).prop("expanded")).toBe(false)
    expect(wrapper.find(StyledSidebarNavItems)).toHaveStyleRule(
      "max-height",
      "33vh"
    )
  })

  it("passes the empty string to onPageChange if the main page link is clicked", () => {
    const props = getProps()
    const wrapper = shallow(<SidebarNav {...props} />)

    const preventDefault = jest.fn()
    const links = wrapper.find(StyledSidebarNavLink)
    links.at(0).simulate("click", { preventDefault })

    expect(preventDefault).toHaveBeenCalled()
    expect(props.onPageChange).toHaveBeenCalledWith("")
  })

  it("passes the page name to onPageChange if any other link is clicked", () => {
    const props = getProps()
    const wrapper = shallow(<SidebarNav {...props} />)

    const preventDefault = jest.fn()
    const links = wrapper.find(StyledSidebarNavLink)
    links.at(1).simulate("click", { preventDefault })

    expect(preventDefault).toHaveBeenCalled()
    expect(props.onPageChange).toHaveBeenCalledWith("my_other_page")
  })

  it("calls hideParentScrollbar onMouseOut", () => {
    const props = getProps()
    const wrapper = shallow(<SidebarNav {...props} />)

    wrapper.find(StyledSidebarNavItems).simulate("mouseOut")

    expect(props.hideParentScrollbar).toHaveBeenCalledWith(false)
  })

  it("does not call hideParentScrollbar on mouseOver if not overflowing", () => {
    const props = getProps()
    const wrapper = shallow(<SidebarNav {...props} />)

    wrapper.find(StyledSidebarNavItems).simulate("mouseOver")

    expect(props.hideParentScrollbar).not.toHaveBeenCalled()
  })

  it("does call hideParentScrollbar on mouseOver if overflowing", () => {
    useIsOverflowing.mockReturnValueOnce(true)
    const props = getProps()
    const wrapper = shallow(<SidebarNav {...props} />)

    wrapper.find(StyledSidebarNavItems).simulate("mouseOver")

    expect(props.hideParentScrollbar).toHaveBeenCalledWith(true)
  })
})
