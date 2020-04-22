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

import { Map as ImmutableMap } from "immutable"
import { logError, logWarning } from "lib/log"
import { Source, WidgetStateManager } from "lib/WidgetStateManager"
import React, { createRef, ReactNode } from "react"
import { ComponentRegistry } from "./ComponentRegistry"

/** Messages from Component -> Streamlit */
export enum ComponentBackMsgType {
  // A component sends this message when it's ready to receive messages
  // from Streamlit. Streamlit won't send any messages until it gets this.
  // No data.
  COMPONENT_READY = "componentReady",

  // The component has a new widget value. Send it back to Streamlit, which
  // will then re-run the app.
  // Data: { value: any }
  SET_WIDGET_VALUE = "setWidgetValue",

  // The component has a new height for its iframe.
  // Data: { height: number }
  SET_FRAME_HEIGHT = "setFrameHeight",
}

/** Messages from Streamlit -> Component */
export enum ComponentForwardMsgType {
  // Sent by Streamlit when the component should re-render.
  // Data: { args: any, disabled: boolean }
  RENDER = "render",
}

interface Props {
  registry: ComponentRegistry
  widgetMgr: WidgetStateManager

  disabled: boolean
  element: ImmutableMap<string, any>
  width: number
}

interface State {
  frameHeight?: number
}

// TODO: catch errors and display them in render()

export class ComponentInstance extends React.PureComponent<Props, State> {
  private iframeRef = createRef<HTMLIFrameElement>()
  // True when we've received the COMPONENT_READY message
  private componentReady = false
  private pendingRenderArgs = {}
  private pendingRenderDfs = []

  public constructor(props: Props) {
    super(props)
    this.state = { frameHeight: undefined }
  }

  public componentDidMount = (): void => {
    if (this.iframeRef.current == null) {
      // This should not be possible.
      logError(
        `ComponentInstance does not have an iframeRef, and will not receive messages!`
      )
      return
    }

    if (this.iframeRef.current.contentWindow == null) {
      // Nor should this.
      logError(
        `ComponentInstance iframe does not have an iframeRef, and will not receive messages!`
      )
      return
    }

    this.props.registry.registerListener(
      this.iframeRef.current.contentWindow,
      this.onBackMsg
    )
  }

  public componentWillUnmount = (): void => {
    if (
      this.iframeRef.current == null ||
      this.iframeRef.current.contentWindow == null
    ) {
      return
    }

    this.props.registry.deregisterListener(
      this.iframeRef.current.contentWindow
    )
  }

  /**
   * Receive a ComponentBackMsg from our component iframe.
   */
  private onBackMsg = (type: string, data: any): void => {
    switch (type) {
      case ComponentBackMsgType.COMPONENT_READY:
        if (this.componentReady) {
          logWarning(`Got multiple COMPONENT_READY messages!`)
        } else {
          // Our component is ready to begin receiving messages. Send off its
          // first render message!
          this.componentReady = true
          this.sendForwardMsg(ComponentForwardMsgType.RENDER, {
            args: this.pendingRenderArgs,
            dfs: this.pendingRenderDfs,
          })
        }
        break

      case ComponentBackMsgType.SET_WIDGET_VALUE:
        if (!this.componentReady) {
          logWarning(
            `Got ${type} before ${ComponentBackMsgType.COMPONENT_READY}!`
          )
        } else {
          this.handleSetWidgetValue(data, { fromUi: true })
        }
        break

      case ComponentBackMsgType.SET_FRAME_HEIGHT:
        if (!this.componentReady) {
          logWarning(
            `Got ${type} before ${ComponentBackMsgType.COMPONENT_READY}!`
          )
        } else {
          this.handleSetFrameHeight(data)
        }
        break

      default:
        logWarning(`Unrecognized ComponentBackMsgType: ${type}`)
    }
  }

  /** The component set a new widget value. Send it back to Streamlit. */
  private handleSetWidgetValue = (data: any, source: Source): void => {
    const value = tryGetValue(data, "value")
    if (value === undefined) {
      logWarning(`handleSetWidgetValue: missing 'value' prop`)
      return
    }

    const widgetId: string = this.props.element.get("id")

    // TODO: handle debouncing, or expose some debouncing primitives?
    // TODO: ints, arrays, "button triggers", ... dataframes?

    if (typeof value === "boolean") {
      this.props.widgetMgr.setBoolValue(widgetId, Boolean(value), source)
    } else if (typeof value === "number") {
      this.props.widgetMgr.setFloatValue(widgetId, Number(value), source)
    } else if (typeof value === "string") {
      this.props.widgetMgr.setStringValue(widgetId, String(value), source)
    } else {
      logWarning(`ComponentInstance: unsupported value type! ${value}`)
    }
  }

  /** The component has a new height. We'll resize the iframe. */
  private handleSetFrameHeight = (data: any): void => {
    const height: number | undefined = tryGetValue(data, "height")
    if (height === undefined) {
      logWarning(`handleSetFrameHeight: missing 'height' prop`)
      return
    }

    this.setState({ frameHeight: height })
  }

  private sendForwardMsg = (
    type: ComponentForwardMsgType,
    data: any
  ): void => {
    if (this.iframeRef.current == null) {
      // This should never happen
      logWarning("Can't send ForwardMsg; missing our iframe!")
      return
    }

    if (this.iframeRef.current.contentWindow == null) {
      // Nor should this!
      logWarning("Can't send ForwardMsg; iframe has no contentWindow!")
      return
    }

    this.iframeRef.current.contentWindow.postMessage(
      {
        isStreamlitMessage: true,
        type: type,
        ...data,
      },
      "*"
    )
  }

  public render = (): ReactNode => {
    const componentId = this.props.element.get("componentId")
    const src = this.props.registry.getComponentURL(componentId, "index.html")

    const renderArgs = JSON.parse(this.props.element.get("argsJson"))
    const renderDfs = this.props.element.get("argsDataframe").toJS()

    if (this.componentReady) {
      // The component has loaded. Send it a new render message immediately.
      this.sendForwardMsg(ComponentForwardMsgType.RENDER, {
        args: renderArgs,
        dfs: renderDfs,
        disabled: this.props.disabled,
      })
    } else {
      // The component hasn't yet loaded. Save these render args; we'll
      // send the RENDER message as soon as the component is ready.
      // It is *not* an error for a component to never send the ready message.
      this.pendingRenderArgs = renderArgs
      this.pendingRenderDfs = renderDfs
    }

    // Render the iframe. We set scrolling="no", because we don't want
    // scrollbars to appear; instead, we want components to properly auto-size
    // themselves.
    //
    // Without this, there is a potential for a scrollbar to
    // appear for a brief moment after an iframe's content gets bigger,
    // and before it sends the "setFrameHeight" message back to Streamlit.
    //
    // We may ultimately want to give components control over the "scrolling"
    // property.
    //
    // TODO: make sure horizontal scrolling still works!
    return (
      <iframe
        ref={this.iframeRef}
        src={src}
        width={this.props.width}
        height={this.state.frameHeight}
        allowFullScreen={false}
        seamless={true}
        scrolling="no"
        sandbox="allow-forms allow-popups allow-scripts"
      />
    )
  }
}

/** Return the property with the given name, if it exists. */
function tryGetValue(
  obj: any,
  name: string,
  defaultValue: any = undefined
): any {
  return obj.hasOwnProperty(name) ? obj[name] : defaultValue
}
