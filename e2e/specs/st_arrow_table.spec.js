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

describe("st._arrow_table", () => {
  before(() => {
    cy.loadApp("http://localhost:3000/");

    cy.prepForElementSnapshots();

    // Wait for all the tables to be loaded.
    cy.get("[data-testid='stTable']").should("have.length", 11);
  });

  it("has consistent visuals", () => {
    cy.get("[data-testid='stTable']").each(($element, index) => {
      return cy
        .wrap($element)
        .matchThemedSnapshots("arrow-table-visuals" + index);
    });
  });
});
