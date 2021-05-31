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

import { Quiver } from "lib/Quiver"
import { range } from "lodash"
import React, { ReactElement } from "react"

import withFullScreenWrapper from "src/hocs/withFullScreenWrapper"
import { Quiver } from "src/lib/Quiver"
import {
  StyledEmptyTableCell,
  StyledTable,
  StyledTableCell,
  StyledTableCellHeader,
  StyledTableContainer,
} from "./styled-components"

export interface TableProps {
  element: Quiver
}

export function BetaTable(props: TableProps): ReactElement {
  const table = props.element
  const { tableId, tableStyles, caption } = table
  const { headerRows, rows, columns } = table.dimensions
  const allRows = range(rows)
  const columnHeaders = allRows.slice(0, headerRows)
  const dataRows = allRows.slice(headerRows)

  return (
    <StyledTableContainer data-testid="stTable">
      {tableStyles && <style>{tableStyles}</style>}
      <StyledTable id={tableId}>
        {caption && <caption>{caption}</caption>}
        {columnHeaders.length > 0 && (
          <thead>
            {columnHeaders.map(rowIndex =>
              generateTableRow(table, rowIndex, columns)
            )}
          </thead>
        )}
        <tbody>
          {dataRows.length === 0 ? (
            <tr>
              <StyledEmptyTableCell colSpan={columns || 1}>
                empty
              </StyledEmptyTableCell>
            </tr>
          ) : (
            dataRows.map(rowIndex =>
              generateTableRow(table, rowIndex, columns)
            )
          )}
        </tbody>
      </StyledTable>
    </StyledTableContainer>
  )
}

function generateTableRow(
  table: Quiver,
  rowIndex: number,
  columns: number
): ReactElement {
  return (
    <tr key={rowIndex}>
      {range(columns).map(columnIndex =>
        generateTableCell(table, rowIndex, columnIndex)
      )}
    </tr>
  )
}

function generateTableCell(
  table: Quiver,
  rowIndex: number,
  columnIndex: number
): ReactElement {
  const { type, id, classNames, content } = table.getCell(
    rowIndex,
    columnIndex
  )

  switch (type) {
    case "blank": {
      return <th key={columnIndex} className={classNames}></th>
    }
    case "index": {
      return (
        <StyledTableCellHeader
          key={columnIndex}
          scope="row"
          id={id}
          className={classNames}
        >
          {content}
        </StyledTableCellHeader>
      )
    }
    case "columns": {
      return (
        <StyledTableCellHeader
          key={columnIndex}
          scope="col"
          className={classNames}
        >
          {content}
        </StyledTableCellHeader>
      )
    }
    case "data": {
      return (
        <StyledTableCell key={columnIndex} id={id} className={classNames}>
          {content}
        </StyledTableCell>
      )
    }
    default: {
      throw new Error(`Cannot parse type "${type}".`)
    }
  }
}

export default withFullScreenWrapper(BetaTable)
