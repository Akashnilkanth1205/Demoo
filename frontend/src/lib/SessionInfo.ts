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

interface Args {
  streamlitVersion: string
  pythonVersion: string
  installationId: string
  authorEmail: string
  commandLine: string[]
  maxCachedMessageAge: number
}

export class SessionInfo {
  // Fields that don't change during the lifetime of a session (i.e. a browser tab).
  public readonly streamlitVersion: string
  public readonly pythonVersion: string
  public readonly installationId: string
  public readonly authorEmail: string
  public readonly maxCachedMessageAge: number

  // Fields that can change during the lifetime of a session.
  public commandLine: string[] = []

  /**
   * Singleton SessionInfo object. The reasons we're using a singleton here
   * instead of just exporting a module-level instance are:
   * - So we can easily override it in tests.
   * - So we throw a loud error when some code tries to use it before it's
   *   initialized.
   */
  private static singleton?: SessionInfo

  public static get current(): SessionInfo {
    if (!SessionInfo.singleton) {
      throw new Error("Tried to use SessionInfo before it was initialized")
    }
    return SessionInfo.singleton
  }

  public static set current(sm: SessionInfo) {
    SessionInfo.singleton = sm
  }

  public static isSet(): boolean {
    return SessionInfo.singleton != null
  }

  public constructor({
    streamlitVersion,
    pythonVersion,
    installationId,
    authorEmail,
    maxCachedMessageAge,
  }: Args) {
    this.streamlitVersion = streamlitVersion
    this.pythonVersion = pythonVersion
    this.installationId = installationId
    this.authorEmail = authorEmail
    this.maxCachedMessageAge = maxCachedMessageAge
  }
}
