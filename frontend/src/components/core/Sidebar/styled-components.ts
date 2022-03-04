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

import { transparentize } from "color2k"

export const StyledSidebar = styled.section(({ theme }) => ({
  [`@media (max-width: ${theme.breakpoints.md})`]: {
    marginLeft: theme.spacing.none,
    // Instead of 100% width and height, we want to make sure
    // the sidebar takes all available space when viewports change
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
  },

  // Scrollbars can look ugly, so we try to style them to look better
  [`::-webkit-scrollbar-thumb:vertical,
  ::-webkit-scrollbar-thumb:horizontal,
  ::-webkit-scrollbar-thumb:vertical:active,
  ::-webkit-scrollbar-thumb:horizontal:active`]: {
    background: theme.colors.transparent,
  },

  "&:hover": {
    [`::-webkit-scrollbar-thumb:vertical,
    ::-webkit-scrollbar-thumb:horizontal`]: {
      background: "rgba(0, 0, 0, 0.5)",
    },

    [`::-webkit-scrollbar-thumb:vertical:active,
    ::-webkit-scrollbar-thumb:horizontal:active`]: {
      background: "rgba(0, 0, 0, 0.61)",
      borderRadius: "100px",
    },
  },
}))

export const StyledSidebarNavContainer = styled.div(({ expanded, theme }) => ({
  // TODO(vdonato): FIXME (add proper styling)
}))

export interface StyledSidebarNavItemsProps {
  expanded: boolean
}

export const StyledSidebarNavItems = styled.ul<StyledSidebarNavItemsProps>(
  ({ expanded, theme }) => ({
    listStyle: "none",
    maxHeight: expanded ? "75vh" : "25vh",
    overflow: "auto",
    // TODO(vdonato): FIXME (add proper styling)
  })
)

export const StyledSidebarNavSeparator = styled.hr(({ theme }) => ({
  // TODO(vdonato): FIXME
  // * add proper styling
  // * increase clickable area for the separator
  // * add dynamic styling behavior for mouse hover
}))

export const StyledSidebarNavLinkContainer = styled.div(({ theme }) => ({
  // TODO(vdonato): FIXME (add proper styling and make the full container clickable)
}))

export const StyledSidebarNavLink = styled.a(({ theme }) => ({
  // TODO(vdonato): FIXME (add proper styling)
}))

export interface StyledSidebarContentProps {
  isCollapsed: boolean
}

export const StyledSidebarContent = styled.div<StyledSidebarContentProps>(
  ({ isCollapsed, theme }) => ({
    backgroundColor: theme.colors.bgColor,
    backgroundAttachment: "fixed",
    flexShrink: 0,
    // Nudge the sidebar by 2px so the header decoration doesn't go below it
    height: "calc(100vh - 2px)",
    top: "2px",
    overflow: "auto",
    padding: `6rem ${theme.spacing.lg}`,
    position: "relative",
    transition: "margin-left 300ms, box-shadow 300ms",
    width: theme.sizes.sidebar,
    zIndex: theme.zIndices.header + 1,
    marginLeft: isCollapsed ? `-${theme.sizes.sidebar}` : theme.spacing.none,

    "&:focus": {
      outline: "none",
    },

    [`@media (max-width: ${theme.breakpoints.md})`]: {
      boxShadow: `-2rem 0 2rem 2rem ${
        isCollapsed ? "transparent" : "#00000029"
      }`,
      zIndex: theme.zIndices.sidebarMobile,
    },

    "& h1": {
      fontSize: theme.fontSizes.xl,
      fontWeight: 600,
    },

    "& h2": {
      fontSize: theme.fontSizes.lg,
      fontWeight: 600,
    },

    "& h3": {
      fontSize: theme.fontSizes.mdLg,
      fontWeight: 600,
    },

    "& h4": {
      fontSize: theme.fontSizes.md,
      fontWeight: 600,
    },

    "& h5": {
      fontSize: theme.fontSizes.sm,
      fontWeight: 600,
    },

    "& h6": {
      fontSize: theme.fontSizes.twoSm,
      fontWeight: 600,
    },
  })
)

export const StyledSidebarCloseButton = styled.div(({ theme }) => ({
  position: "absolute",
  top: theme.spacing.sm,
  right: theme.spacing.sm,
  zIndex: 1,
  color: theme.colors.fadedText40,

  "&:hover button": {
    backgroundColor: transparentize(theme.colors.fadedText60, 0.5),
  },
}))

export interface StyledSidebarCollapsedControlProps {
  chevronDownshift: number
  isCollapsed: boolean
}
export const StyledSidebarCollapsedControl = styled.div<
  StyledSidebarCollapsedControlProps
>(({ chevronDownshift, isCollapsed, theme }) => ({
  position: "fixed",
  top: chevronDownshift ? `${chevronDownshift}px` : theme.spacing.sm,
  left: isCollapsed ? theme.spacing.sm : `-${theme.spacing.sm}`,
  zIndex: theme.zIndices.header,

  transition: "left 300ms",
  transitionDelay: "left 300ms",

  color: theme.colors.fadedText40,

  [`@media (max-width: ${theme.breakpoints.md})`]: {
    color: theme.colors.bodyText,
  },
}))
