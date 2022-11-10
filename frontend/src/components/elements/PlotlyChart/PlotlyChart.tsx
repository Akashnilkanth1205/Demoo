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

import React, { ReactElement, useEffect, useState } from "react"
import { useTheme } from "@emotion/react"
import {
  Theme,
  getCategoricalColorsArray,
  getSequentialColorsArray,
} from "src/theme"
import {
  Figure as FigureProto,
  PlotlyChart as PlotlyChartProto,
} from "src/autogen/proto"
import withFullScreenWrapper from "src/hocs/withFullScreenWrapper"
import Plot from "react-plotly.js"
import { applyStreamlitTheme, layoutWithThemeDefaults } from "./CustomTheme"

export interface PlotlyChartProps {
  width: number
  element: PlotlyChartProto
  height: number | undefined
}

export interface PlotlyIFrameProps {
  width: number
  height: number | undefined
  url: string
}

export const DEFAULT_HEIGHT = 450

function renderIFrame({
  url,
  width,
  height: propHeight,
}: PlotlyIFrameProps): ReactElement {
  const height = propHeight || DEFAULT_HEIGHT
  return <iframe title="Plotly" src={url} style={{ width, height }} />
}

function renderFigure({
  element,
  width,
  height,
}: PlotlyChartProps): ReactElement {
  const figure = element.figure as FigureProto
  const isFullScreen = (): boolean => !!height

  const theme: Theme = useTheme()

  const generateSpec = (figure: FigureProto): any => {
    if (element.theme === "streamlit") {
      const categoryColors = getCategoricalColorsArray(theme)
      figure.spec = figure.spec.replaceAll("#000001", categoryColors[0])
      figure.spec = figure.spec.replaceAll("#000002", categoryColors[1])
      figure.spec = figure.spec.replaceAll("#000003", categoryColors[2])
      figure.spec = figure.spec.replaceAll("#000004", categoryColors[3])
      figure.spec = figure.spec.replaceAll("#000005", categoryColors[4])
      figure.spec = figure.spec.replaceAll("#000006", categoryColors[5])
      figure.spec = figure.spec.replaceAll("#000007", categoryColors[6])
      figure.spec = figure.spec.replaceAll("#000008", categoryColors[7])
      figure.spec = figure.spec.replaceAll("#000009", categoryColors[8])
      figure.spec = figure.spec.replaceAll("#000010", categoryColors[9])

      const sequentialColors = getSequentialColorsArray(theme)
      figure.spec = figure.spec.replaceAll("#000011", sequentialColors[0])
      figure.spec = figure.spec.replaceAll("#000012", sequentialColors[1])
      figure.spec = figure.spec.replaceAll("#000013", sequentialColors[2])
      figure.spec = figure.spec.replaceAll("#000014", sequentialColors[3])
      figure.spec = figure.spec.replaceAll("#000015", sequentialColors[4])
      figure.spec = figure.spec.replaceAll("#000016", sequentialColors[5])
      figure.spec = figure.spec.replaceAll("#000017", sequentialColors[6])
      figure.spec = figure.spec.replaceAll("#000018", sequentialColors[7])
      figure.spec = figure.spec.replaceAll("#000019", sequentialColors[8])
      figure.spec = figure.spec.replaceAll("#000020", sequentialColors[9])
    } else {
      figure.spec = figure.spec.replaceAll("#000001", "#636efa")
      figure.spec = figure.spec.replaceAll("#000002", "#EF553B")
      figure.spec = figure.spec.replaceAll("#000003", "#00cc96")
      figure.spec = figure.spec.replaceAll("#000004", "#ab63fa")
      figure.spec = figure.spec.replaceAll("#000005", "#FFA15A")
      figure.spec = figure.spec.replaceAll("#000006", "#19d3f3")
      figure.spec = figure.spec.replaceAll("#000007", "#FF6692")
      figure.spec = figure.spec.replaceAll("#000008", "#B6E880")
      figure.spec = figure.spec.replaceAll("#000009", "#FF97FF")
      figure.spec = figure.spec.replaceAll("#000010", "#FECB52")

      figure.spec = figure.spec.replaceAll("#000011", "#0d0887")
      figure.spec = figure.spec.replaceAll("#000012", "#46039f")
      figure.spec = figure.spec.replaceAll("#000013", "#7201a8")
      figure.spec = figure.spec.replaceAll("#000014", "#9c179e")
      figure.spec = figure.spec.replaceAll("#000015", "#bd3786")
      figure.spec = figure.spec.replaceAll("#000016", "#d8576b")
      figure.spec = figure.spec.replaceAll("#000017", "#ed7953")
      figure.spec = figure.spec.replaceAll("#000018", "#fb9f3a")
      figure.spec = figure.spec.replaceAll("#000019", "#fdca26")
      figure.spec = figure.spec.replaceAll("#000020", "#f0f921")
    }

    const spec = JSON.parse(figure.spec)

    const initialHeight = DEFAULT_HEIGHT

    if (isFullScreen()) {
      spec.layout.width = width
      spec.layout.height = height
    } else if (element.useContainerWidth) {
      spec.layout.width = width
    } else {
      spec.layout.width = width
      spec.layout.height = initialHeight
    }
    if (element.theme === "streamlit") {
      applyStreamlitTheme(spec, theme)
    } else {
      // Apply minor theming improvements to work better with Streamlit
      spec.layout = layoutWithThemeDefaults(spec.layout, theme)
    }

    return spec
  }

  const [config, setConfig] = useState(JSON.parse(figure.config))
  const [spec, setSpec] = useState(generateSpec(figure))

  // Update config and spec references iff the theme or props change
  useEffect(() => {
    setConfig(JSON.parse(figure.config))
    setSpec(generateSpec(figure))
  }, [element, theme, height, width])

  const { data, layout, frames } = spec

  return (
    <Plot
      key={isFullScreen() ? "fullscreen" : "original"}
      className="stPlotlyChart"
      data={data}
      layout={layout}
      config={config}
      frames={frames}
    />
  )
}

export function PlotlyChart({
  width,
  element,
  height,
}: PlotlyChartProps): ReactElement {
  switch (element.chart) {
    case "url":
      return renderIFrame({
        url: element.url as string,
        height,
        width,
      })
    case "figure":
      return renderFigure({ element, height, width })
    default:
      throw new Error(`Unrecognized PlotlyChart type: ${element.chart}`)
  }
}

export default withFullScreenWrapper(PlotlyChart)
