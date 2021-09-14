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

describe("the typography in the main block", () => {
  // Doesn't have to run before each, since these tests are stateless.
  before(() => {
    cy.visit("http://localhost:3000/");

    // Wait for 'data-stale' attr to go away, so the snapshot looks right.
    cy.get(".element-container")
      .should("have.attr", "data-stale", "false")
      .invoke("css", "opacity", "1");
  });

  it("matches the snapshot", () => {
    cy.get(".main").matchThemedSnapshots("main-block");
  });
});

describe("the typography in the sidebar", () => {
  it("matches the snapshot", () => {
    cy.get("[data-testid='stSidebar']").matchThemedSnapshots("sidebar-block");
  });
});
