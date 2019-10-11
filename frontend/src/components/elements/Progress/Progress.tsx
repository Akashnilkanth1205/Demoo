/**
 * @license
 * Copyright 2018-2019 Streamlit Inc.
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
import { Map as ImmutableMap } from "immutable"
import { Progress as RProgress } from "reactstrap"

import "./Progress.scss"

interface Props {
  width: number
  element: ImmutableMap<string, any>
}

class Progress extends React.PureComponent<Props> {
  public render(): React.ReactNode {
    const { element, width } = this.props

    return (
      <RProgress
        value={element.get("value")}
        className="stProgress"
        style={{ width }}
      />
    )
  }
}

export default Progress
