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

describe("tooltips on widgets", () => {
  before(() => {
    cy.visit("http://localhost:3000/");
  });

  it("displays tooltip on text_input", () => {
    cy.get(".stTextInput .stTooltipIcon").should("have.length", 1);
  });

  it("displays tooltip on number_input", () => {
    cy.get(".stNumberInput .stTooltipIcon").should("have.length", 1);
  });

  it("displays tooltip on checkbox", () => {
    cy.get(".stCheckbox .stTooltipIcon").should("have.length", 1);
  });

  it("displays tooltip on radio", () => {
    cy.get(".stRadio .stTooltipIcon").should("have.length", 1);
  });

  it("displays tooltip on button", () => {
    cy.get(".stButton .stTooltipIcon").should("have.length", 1);
  });

  it("displays tooltip on selectbox", () => {
    cy.get(".stSelectbox .stTooltipIcon").should("have.length", 1);
  });

  it("displays tooltip on time_input", () => {
    cy.get(".stTimeInput .stTooltipIcon").should("have.length", 1);
  });

  it("displays tooltip on date_input", () => {
    cy.get(".stDateInput .stTooltipIcon").should("have.length", 1);
  });

  it("displays tooltip on image", () => {
    cy.get(".stImage .stTooltipIcon").should("have.length", 1);
  });

  it("displays tooltip on line_chart", () => {
    cy.get(".stVegaLiteChart .stTooltipIcon").should("have.length", 1);
  });

  it("displays tooltip on plotly_chart", () => {
    cy.get(".stPlotlyChartWrapper .stTooltipIcon").should("have.length", 1);
  });

  /*
  it("displays tooltip on write", () => {});
  it("displays tooltip on markdown", () => {});
  it("displays tooltip on header", () => {});
  it("displays tooltip on subheader", () => {});
  it("displays tooltip on code", () => {});
  it("displays tooltip on latex", () => {});
  */
});
