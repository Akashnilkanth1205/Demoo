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

import React, { ReactElement } from "react"

import { AppPage } from "src/autogen/proto"

import {
  StyledSidebarNavContainer,
  StyledSidebarNavLinkContainer,
  StyledSidebarNavLink,
  StyledSidebarNavSeparator,
} from "./styled-components"

export interface Props {
  pages: AppPage[]
  sidebarHasElements: boolean
}

// TODO(vdonato): somehow indicate the current page and make it unclickable
// TODO(vdonato): make the full container for each link clickable
// TODO(vdonato): set links correctly
// TODO(vdonato): actually add an onClick handler
// TODO(vdonato): Toggle between expanded and collapsed page selector state
//                based on separator click
// TODO(vdonato): Toggle between expanded and collapsed page selector state
//                based on mouse over / out (stretch goal).
const SidebarNav = ({
  appPages,
  sidebarHasElements,
}: Props): ReactElement | null => {
  if (appPages.length < 2) {
    return null
  }

  return (
    <StyledSidebarNavContainer>
      <ul>
        {appPages.map(({ pageName }: AppPage) => (
          <li key={pageName}>
            <StyledSidebarNavLinkContainer>
              <StyledSidebarNavLink href={"http://example.com"}>
                {pageName.replace(/_/g, " ")}
              </StyledSidebarNavLink>
            </StyledSidebarNavLinkContainer>
          </li>
        ))}
      </ul>
      {sidebarHasElements && <StyledSidebarNavSeparator />}
    </StyledSidebarNavContainer>
  )
}

export default SidebarNav
