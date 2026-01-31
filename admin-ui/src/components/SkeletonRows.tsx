"use client";

/**
 * Skeleton placeholders for a Mantine `<Table>` body (DoD §9.7).
 *
 * Renders `<rows>` `<tr>` elements, each with `<columns>` `<td>` cells
 * containing a Mantine `<Skeleton>` block. Drop into the `<tbody>` of
 * any list while data is loading instead of showing a raw spinner —
 * preserves layout (no jumping rows when data arrives) and signals
 * "the page is alive, content on the way" without screaming.
 *
 * Usage:
 *   <Table.Tbody>
 *     {loading
 *       ? <SkeletonRows columns={3} rows={5} />
 *       : items.map(...)}
 *   </Table.Tbody>
 */
import { Skeleton, Table } from "@mantine/core";

export interface SkeletonRowsProps {
  /** Number of `<td>` cells per row. */
  columns: number;
  /** Number of placeholder rows to render. Defaults to 5. */
  rows?: number;
  /** Optional extra cells (e.g. trailing actions column). */
  trailingColumns?: number;
}

export default function SkeletonRows({
  columns, rows = 5, trailingColumns = 0,
}: SkeletonRowsProps) {
  const totalCols = columns + trailingColumns;
  return (
    <>
      {Array.from({ length: rows }).map((_, ri) => (
        <Table.Tr key={`skeleton-${ri}`}>
          {Array.from({ length: totalCols }).map((__, ci) => (
            <Table.Td key={ci}>
              <Skeleton
                height={14}
                width={ci === 0 ? "70%" : ci === totalCols - 1 ? "40%" : "85%"}
                radius="sm"
              />
            </Table.Td>
          ))}
        </Table.Tr>
      ))}
    </>
  );
}
