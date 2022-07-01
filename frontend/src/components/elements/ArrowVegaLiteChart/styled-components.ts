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

import styled from "@emotion/styled"

export const StyledVegaLiteChartContainer = styled.div(({ theme }) => ({
  // These styles come from VegaLite Library
  "&.vega-embed": {
    ".vega-actions": {
      zIndex: theme.zIndices.popupMenu,
      // Customize menu UI to look like the Streamlit menu:
      backgroundColor: theme.colors.bgColor,
      boxShadow: "rgb(0 0 0 / 16%) 0px 4px 16px",
      border: `1px solid ${theme.colors.fadedText10}`,
      a: {
        fontFamily: theme.genericFonts.bodyFont,
        fontWeight: theme.fontWeights.normal,
        fontSize: theme.fontSizes.md,
        margin: 0,
        padding: `${theme.spacing.twoXS} ${theme.spacing.twoXL}`,
        color: theme.colors.bodyText,
      },
      "a:hover": {
        backgroundColor: theme.colors.secondaryBg,
        color: theme.colors.bodyText,
      },
      ":before": {
        content: "none",
      },
      ":after": {
        content: "none",
      },
    },
    summary: {
      // Fix weird floating button height issue in Vega Lite.
      height: "auto",
      // Fix floating button appearing above pop-ups.
      zIndex: theme.zIndices.menuButton,
    },
  },
}))
