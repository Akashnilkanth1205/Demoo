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

import { SessionInfo } from "lib/SessionInfo"
import { IS_DEV_ENV, IS_SHARED_REPORT } from "./baseconsts"
import { logAlways } from "./log"
import { initializeSegment } from "./Segment"

/**
 * The analytics is the Segment.io object. It is initialized in Segment.ts
 * It is loaded with global scope (window.analytics) to integrate with the segment.io api
 * @global
 * */
declare const analytics: any

/**
 * A mapping of [delta type] -> [count] which is used to upload delta stats
 * when the app is idle.
 */
interface DeltaCounter {
  [name: string]: number
}

/**
 * A mapping of [component instance name] -> [count] which is used to upload
 * custom component stats when the app is idle.
 */
interface CustomComponentCounter {
  [name: string]: number
}

type Event = [string, Record<string, unknown>]

export class MetricsManager {
  private initialized = false

  /**
   * Whether to send metrics to the server.
   */
  private actuallySendMetrics = false

  /**
   * Queue of metrics events that were enqueued before this MetricsManager was
   * initialized.
   */
  private pendingEvents: Event[] = []

  /**
   * Object used to count the number of delta types seen in a given report.
   * Maps type of delta (string) to count (number).
   */
  private pendingDeltaCounter: DeltaCounter = {}

  /**
   * Object used to count the number of custom instance names seen in a given report.
   * Maps type of custom instance name (string) to count (number).
   */
  private pendingCustomComponentCounter: CustomComponentCounter = {}

  /**
   * Report hash uniquely identifies "projects" so we can tell
   * how many projects are being created with Streamlit while still keeping
   * possibly-sensitive info like the scriptPath outside of our metrics
   * services.
   */
  private reportHash = "Not initialized"

  /**
   * Singleton MetricsManager object. The reason we're using a singleton here
   * instead of just exporting a module-level instance is so we can easily
   * override it in tests.
   */
  public static current: MetricsManager = new MetricsManager()

  public initialize({
    gatherUsageStats,
  }: {
    gatherUsageStats: boolean
  }): void {
    this.initialized = true
    this.actuallySendMetrics = gatherUsageStats

    if (this.actuallySendMetrics || IS_SHARED_REPORT) {
      // Segment will not initialize if this is rendered with SSR
      initializeSegment()
      // Only record the user's email if they entered a non-empty one.
      const userTraits: any = {}
      if (SessionInfo.current.authorEmail !== "") {
        userTraits.authoremail = SessionInfo.current.authorEmail
      }
      MetricsManager.identify(SessionInfo.current.installationId, userTraits)
      this.sendPendingEvents()
    }

    logAlways("Gather usage stats: ", this.actuallySendMetrics)
  }

  public enqueue(evName: string, evData: Record<string, unknown> = {}): void {
    if (!this.initialized) {
      this.pendingEvents.push([evName, evData])
      return
    }

    if (!this.actuallySendMetrics) {
      return
    }

    this.send(evName, evData)
  }

  public clearDeltaCounter(): void {
    this.pendingDeltaCounter = {}
  }

  public incrementDeltaCounter(deltaType: string): void {
    if (this.pendingDeltaCounter[deltaType] == null) {
      this.pendingDeltaCounter[deltaType] = 1
    } else {
      this.pendingDeltaCounter[deltaType]++
    }
  }

  public getAndResetDeltaCounter(): DeltaCounter {
    const deltaCounter = this.pendingDeltaCounter
    this.clearDeltaCounter()
    return deltaCounter
  }

  public clearCustomComponentCounter(): void {
    this.pendingCustomComponentCounter = {}
  }

  public incrementCustomComponentCounter(customInstanceName: string): void {
    if (this.pendingCustomComponentCounter[customInstanceName] == null) {
      this.pendingCustomComponentCounter[customInstanceName] = 1
    } else {
      this.pendingCustomComponentCounter[customInstanceName]++
    }
  }

  public getAndResetCustomComponentCounter(): CustomComponentCounter {
    const customComponentCounter = this.pendingCustomComponentCounter
    this.clearCustomComponentCounter()
    return customComponentCounter
  }

  // Report hash gets set when update report happens.
  // This means that it will be attached to most, but not all, metrics events.
  // The viewReport and createReport events are sent before updateReport happens,
  // so they will not include the reportHash.
  public setReportHash = (reportHash: string): void => {
    this.reportHash = reportHash
  }

  private send(evName: string, evData: Record<string, unknown> = {}): void {
    const data = {
      ...evData,
      reportHash: this.reportHash,
      dev: IS_DEV_ENV,
      source: "browser",
      streamlitVersion: SessionInfo.current.streamlitVersion,
    }

    // Don't actually track events when in dev mode, just print them instead.
    // This is just to keep us from tracking too many events and having to pay
    // for all of them.
    if (IS_DEV_ENV) {
      logAlways("[Dev mode] Not tracking stat datapoint: ", evName, data)
    } else {
      MetricsManager.track(evName, data)
    }
  }

  private sendPendingEvents(): void {
    this.pendingEvents.forEach(([evName, evData]) => {
      this.send(evName, evData)
    })
    this.pendingEvents = []
  }

  // Wrap analytics methods for mocking:

  private static identify(id: string, data: Record<string, unknown>): void {
    analytics.identify(id, data)
  }

  private static track(evName: string, data: Record<string, unknown>): void {
    analytics.track(evName, data)
  }
}
