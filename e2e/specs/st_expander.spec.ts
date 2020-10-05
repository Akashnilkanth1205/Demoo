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

/// <reference types="cypress" />

const expanderHeaderIdentifier = ".streamlit-expanderHeader";

describe("st.expander", () => {
  before(() => {
    cy.visit("http://localhost:3000/");
  });

  it("displays epxander + regular containers properly", () => {
    cy.get(".stBlock")
      .first()
      .within(() => {
        cy.get(expanderHeaderIdentifier).should("not.exist");
      });
    cy.get(".stBlock")
      .eq(1)
      .within(() => {
        cy.get(expanderHeaderIdentifier).should("exist");
      });
    cy.get(".stBlock")
      .eq(2)
      .within(() => {
        cy.get(expanderHeaderIdentifier).should("exist");
      });
  });

  it("collapses + expands", () => {
    // Starts expanded
    cy.get(".stBlock")
      .eq(1)
      .within(() => {
        const expanderHeader = cy.get(expanderHeaderIdentifier);
        expanderHeader.should("exist");

        let toggle = cy.get("svg[title='Collapse']");
        toggle.should("exist");
        expanderHeader.click();

        toggle = cy.get("svg[title='Expand']");
        toggle.should("exist");
      });
    // Starts collapsed
    cy.get(".stBlock")
      .eq(2)
      .within(() => {
        let expanderHeader = cy.get(expanderHeaderIdentifier);
        expanderHeader.should("exist");

        let toggle = cy.get("svg[title='Expand']");
        toggle.should("exist");
        expanderHeader.click();

        toggle = cy.get("svg[title='Collapse']");
        toggle.should("exist");
      });
  });
});
