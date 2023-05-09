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

import React, { ReactElement } from "react"
import { ToasterContainer, PLACEMENT } from "baseui/toast"

import { AppContext } from "src/app/components/AppContext"

// Toasts should all be rendered under one ToasterContainer
export function ToastContainer(): ReactElement {
  const { communityCloud } = React.useContext(AppContext)

  return (
    <ToasterContainer
      placement={PLACEMENT.bottomRight}
      autoHideDuration={4000}
      overrides={{
        Root: {
          style: {
            // If deployed in Community Cloud, move toasts up to avoid blocking Manage App button
            bottom: communityCloud ? "45px" : "0px",
          },
          props: {
            "data-testid": "toastContainer",
          },
        },
      }}
    />
  )
}

export default ToastContainer
