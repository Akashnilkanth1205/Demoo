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

import styled from "@emotion/styled"

export const StyledText = styled.div(({ theme }) => ({
  overflowWrap: "normal",
  fontFamily: theme.genericFonts.bodyFont,
  fontSize: theme.fontSizes.twoXS,
  color: "grey",
  textOverflow: "ellipsis",
  width: "calc(100%)",
  overflow: "hidden",
  whiteSpace: "nowrap",
  paddingTop: theme.spacing.none,
  paddingBottom: theme.spacing.none,
  marginTop: theme.spacing.md,
}))

export const StyledText2 = styled.div(({ theme }) => ({
  wordWrap: "break-word",
  fontFamily: theme.genericFonts.bodyFont,
  fontSize: theme.fontSizes.twoXL,
  color: theme.colors.textColor,
  textOverflow: "ellipsis",
  fontWeight: theme.fontWeights.medium,
  width: "calc(100%)",
  overflow: "hidden",
  whiteSpace: "nowrap",
  paddingTop: theme.spacing.none,
  paddingBottom: theme.spacing.none,
}))

export const DeltaText = styled.div(({ theme }) => ({
  wordWrap: "break-word",
  fontFamily: theme.genericFonts.bodyFont,
  fontSize: theme.fontSizes.smDefault,
  textOverflow: "ellipsis",
  width: "calc(100%)",
  overflow: "hidden",
  whiteSpace: "nowrap",
  paddingTop: theme.spacing.none,
  paddingBottom: theme.spacing.none,
  marginBottom: theme.spacing.md,
}))
