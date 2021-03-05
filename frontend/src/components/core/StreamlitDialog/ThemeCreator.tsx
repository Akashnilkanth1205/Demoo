import React, { ReactElement } from "react"
import { toHex } from "color2k"
import humanizeString from "humanize-string"
import { Check } from "@emotion-icons/material-outlined"
import { CustomThemeConfig } from "autogen/proto"
import PageLayoutContext from "components/core/PageLayoutContext"
import Button, { Kind } from "components/shared/Button"
import UISelectbox from "components/shared/Dropdown"
import Icon from "components/shared/Icon"
import { createTheme, ThemeConfig, toThemeInput } from "theme"
import {
  StyledButtonContainer,
  StyledHeader,
  StyledHr,
  StyledPasteInstructions,
  StyledSmall,
  StyledThemeColorPicker,
  StyledThemeCreator,
  StyledThemeCreatorWrapper,
  StyledThemeDesc,
} from "./styled-components"

interface ThemeOptionBuilder {
  desc: string
  title: string
  component: any
  options?: any[]
  getValue: (value: string, config: ThemeOptionBuilder) => any
}

const valueToColor = (value: string, _config: ThemeOptionBuilder): string =>
  toHex(value).toUpperCase()

const displayFontOption = (
  font: CustomThemeConfig.FontFamily | string
): string =>
  // @ts-ignore
  humanizeString(CustomThemeConfig.FontFamily[font])

const themeBuilder: Record<string, ThemeOptionBuilder> = {
  primaryColor: {
    desc: "Used as an accent color for interface elements.",
    title: "Primary color",
    component: StyledThemeColorPicker,
    getValue: valueToColor,
  },
  backgroundColor: {
    desc: "Background color for the main container.",
    title: "Background color",
    component: StyledThemeColorPicker,
    getValue: valueToColor,
  },
  secondaryBackgroundColor: {
    desc: `
      Used as the background for the sidebar and most interactive widgets.
      Examples: st.text_input, st.date_input.
    `,
    title: "Secondary background color",
    component: StyledThemeColorPicker,
    getValue: valueToColor,
  },
  textColor: {
    desc: "Font color for the page.",
    title: "Text color",
    component: StyledThemeColorPicker,
    getValue: valueToColor,
  },
  font: {
    desc: "Font family for all text in the app, except code blocks.",
    title: "Font family",
    options: Object.keys(CustomThemeConfig.FontFamily).map(font =>
      humanizeString(font)
    ),
    getValue: (value: string, config: ThemeOptionBuilder): number =>
      (config.options &&
        config.options.findIndex(
          (font: string) => font === displayFontOption(value)
        )) ||
      0,
    component: UISelectbox,
  },
}

const ThemeCreator = (): ReactElement => {
  const [copied, updateCopied] = React.useState(false)
  const [isOpen, openCreator] = React.useState(false)
  const themeCreator = React.useRef<HTMLDivElement>(null)
  const { activeTheme, addThemes, setTheme } = React.useContext(
    PageLayoutContext
  )

  const themeInput = toThemeInput(activeTheme.emotion)

  const updateTheme = (customTheme: ThemeConfig): void => {
    addThemes([customTheme])
    setTheme(customTheme)
  }

  const onThemeOptionChange = (key: string, newVal: string): void => {
    const customTheme = createTheme({
      ...themeInput,
      [key]: newVal,
      name: "Custom Theme",
    })
    updateTheme(customTheme)
    updateCopied(false)
  }

  const config = `[theme]
primaryColor="${themeInput.primaryColor}"
secondaryColor="${themeInput.secondaryColor}"
backgroundColor="${themeInput.backgroundColor}"
secondaryBackgroundColor="${themeInput.secondaryBackgroundColor}"
textColor="${themeInput.textColor}"
font="${displayFontOption(
    themeInput.font || CustomThemeConfig.FontFamily.SANS_SERIF
  ).toLowerCase()}"
`

  const toggleCreatorUI = (): void => {
    openCreator(true)
  }

  React.useEffect(() => {
    if (isOpen && themeCreator.current) {
      themeCreator.current.scrollIntoView(true)
    }
  }, [isOpen])

  const copyConfig = (): void => {
    navigator.clipboard.writeText(config)
    updateCopied(true)
  }

  const renderThemeOption = (
    themeOption: string,
    value: string
  ): ReactElement | null => {
    const themeOptionConfig = themeBuilder[themeOption]
    if (themeOptionConfig === undefined) return null

    const isColor = themeOptionConfig.component === StyledThemeColorPicker
    // Props that vary based on component type
    const variableProps = {
      options: themeOptionConfig.options || undefined,
      showValue: isColor,
      value: themeOptionConfig.getValue(value, themeOptionConfig),
    }
    return (
      <React.Fragment key={themeOption}>
        <themeOptionConfig.component
          disabled={false}
          label={themeOptionConfig.title}
          onChange={(newVal: string) =>
            onThemeOptionChange(themeOption, newVal)
          }
          {...variableProps}
        />
        <StyledThemeDesc>{themeOptionConfig.desc}</StyledThemeDesc>
      </React.Fragment>
    )
  }
  return (
    <StyledThemeCreatorWrapper ref={themeCreator}>
      {isOpen ? (
        <>
          <StyledHr />
          <StyledHeader>Edit active theme</StyledHeader>
          <p>
            Changes exist for the duration of a session. To discard changes and
            recover the original themes, refresh the page.
          </p>
          <StyledThemeCreator>
            {Object.entries(themeInput).map(([themeOption, value]) =>
              renderThemeOption(themeOption, value as string)
            )}
          </StyledThemeCreator>

          <StyledPasteInstructions>
            <StyledSmall>
              To save as a Theme, paste settings in the 'theme' section in your
            </StyledSmall>
            <code>config.toml</code>
            <StyledSmall>file.</StyledSmall>
          </StyledPasteInstructions>
          <StyledButtonContainer>
            <Button onClick={copyConfig} kind={Kind.PRIMARY}>
              {copied ? (
                <>
                  {"Copied to clipboard "}
                  <Icon
                    content={Check}
                    size="lg"
                    color={activeTheme.emotion.colors.success}
                  />
                </>
              ) : (
                "Copy theme to clipboard"
              )}
            </Button>
          </StyledButtonContainer>
        </>
      ) : (
        <Button onClick={toggleCreatorUI} kind={Kind.PRIMARY}>
          Edit active theme
        </Button>
      )}
    </StyledThemeCreatorWrapper>
  )
}

export default ThemeCreator
