/**
 * @license
 * Copyright 2018-2020 Streamlit Inc.
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

import React, { ReactElement, useEffect } from "react"
import { embed as BokehEmbed } from "@bokeh/bokehjs"
import withFullScreenWrapper from "hocs/withFullScreenWrapper"
import { BokehChart as BokehChartProto } from "autogen/proto"

export interface BokehChartProps {
  width: number
  element: BokehChartProto
  index: number
  height?: number
}

interface Dimensions {
  chartWidth: number
  chartHeight: number
}

export function BokehChart({
  width,
  element,
  index,
  height,
}: BokehChartProps): ReactElement {
  const chartId = `bokeh-chart-${index}`

  const getChartData = (): any => {
    return JSON.parse(element.figure)
  }

  const getChartDimensions = (plot: any): Dimensions => {
    // Default values
    let chartWidth: number = plot.attributes.plot_width
    let chartHeight: number = plot.attributes.plot_height

    // if is not fullscreen and useContainerWidth==false, we should use default values
    if (height) {
      // fullscreen
      chartWidth = width
      chartHeight = height
    } else if (element.useContainerWidth) {
      chartWidth = width
    }

    return { chartWidth, chartHeight }
  }

  const removeAllChildNodes = (element: Node): void => {
    while (element.lastChild) {
      element.lastChild.remove()
    }
  }

  const updateChart = (data: any): void => {
    const chart = document.getElementById(chartId)

    /**
     * When you create a bokeh chart in your python script, you can specify
     * the width: p = figure(title="simple line example", x_axis_label="x", y_axis_label="y", plot_width=200);
     * In that case, the json object will contains an attribute called
     * plot_width (or plot_heigth) inside the plot reference.
     * If that values are missing, we can set that values to make the chart responsive.
     */
    const plot =
      data && data.doc && data.doc.roots && data.doc.roots.references
        ? data.doc.roots.references.find((e: any) => e.type === "Plot")
        : undefined

    if (plot) {
      const { chartWidth, chartHeight } = getChartDimensions(plot)

      if (chartWidth > 0) {
        plot.attributes.plot_width = chartWidth
      }
      if (chartHeight > 0) {
        plot.attributes.plot_height = chartHeight
      }
    }

    if (chart !== null) {
      removeAllChildNodes(chart)
      BokehEmbed.embed_item(data, chartId)
    }
  }

  useEffect(() => {
    updateChart(getChartData())
  }, [width, height, element, index, getChartData, updateChart])

  return <div id={chartId} className="stBokehChart" />
}

export default withFullScreenWrapper(BokehChart)
