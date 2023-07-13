/**
 * Copyright (c) Streamlit Inc. (2018-2022) Snowflake Inc. (2022)
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 *     http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distributed on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */

import StreamlitMarkdown from "@streamlit/lib/src/components/shared/StreamlitMarkdown"
import { mount } from "@streamlit/lib/src/test_util"
import { StatelessAccordion } from "baseui/accordion"
import React, { ComponentType } from "react"
import { Block } from "src/proto"
import withExpandable, { ExpandableProps } from "./withExpandable"
import ExpandableState = Block.Expandable.ExpandableState

const testComponent: ComponentType = () => <div>test</div>

const getProps = (props?: Partial<ExpandableProps>): ExpandableProps =>
  Object({
    label: "hi",
    expandable: true,
    expanded: true,
    ...props,
  })

describe("withExpandable HOC", () => {
  it("renders without crashing", () => {
    const props = getProps()
    const WithHoc = withExpandable(testComponent)
    const wrapper = mount(<WithHoc {...props} />)
    expect(wrapper.find(StatelessAccordion).exists()).toBe(true)
  })

  it("renders expander label as expected", () => {
    const props = getProps()
    const WithHoc = withExpandable(testComponent)
    const wrapper = mount(<WithHoc {...props} />)
    const wrappedExpandLabel = wrapper.find(StreamlitMarkdown)

    expect(wrappedExpandLabel.props().source).toBe(getProps().label)
    expect(wrappedExpandLabel.props().isLabel).toBe(true)
  })

  it("should render a expanded component", () => {
    const props = getProps()
    const WithHoc = withExpandable(testComponent)
    const wrapper = mount(<WithHoc {...props} />)
    const accordion = wrapper.find(StatelessAccordion)

    expect(accordion.prop("expanded").length).toBe(1)
  })

  it("should render a collapsed component", () => {
    const props = getProps({
      expandableState: ExpandableState.COLLAPSED,
    })
    const WithHoc = withExpandable(testComponent)
    const wrapper = mount(<WithHoc {...props} />)
    const accordion = wrapper.find(StatelessAccordion)

    expect(accordion.prop("expanded").length).toBe(0)
  })

  it("should become stale", () => {
    const props = getProps({
      isStale: true,
    })
    const WithHoc = withExpandable(testComponent)
    const wrapper = mount(<WithHoc {...props} />)
    const accordion = wrapper.find(StatelessAccordion)
    const overrides = accordion.prop("overrides")

    // @ts-expect-error
    expect(overrides.Header.props.isStale).toBeTruthy()
  })
})
