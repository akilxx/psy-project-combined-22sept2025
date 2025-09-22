// psych-app/src/components/ResultsTable.jsx
import React, { useState } from "react";

/**
 * ResultsTable
 * Each data row highlights and shows fully rounded corners on hover.
 * Technique:
 *  1. <tr> gets `group` so its children can respond to group‑hover.
 *  2. First & last <td> get the rounded corners and the hover background via `group-hover:`.
 *  3. Table is set to `border-separate border-spacing-y-1` so the roundness is actually visible.
 */
export default function ResultsTable({ items }) {
  const [openRow, setOpenRow] = useState(null);

  return (
    <div className="overflow-x-auto rounded-[20px] bg-[#F9F9F9]  w-full max-w-none pt-2 px-4 pb-4 sm:pt-3 sm:px-6 sm:pb-6">
      {/* `border-separate` + a tiny vertical gap lets the rounded outline peek through */}
      <table className="table-fixed w-full text-[11px] sm:text-base border-separate border-spacing-y-1">
        <colgroup>
          <col style={{ width: "40%" }} />
          <col style={{ width: "60%" }} />
        </colgroup>

        <thead>
          <tr>
            <th colSpan={2} className="py-2 px-4 sm:px-6">
              <span className="block w-full bg-[#EBEBEB] rounded-[5px] px-4 py-1">
                <div className="grid grid-cols-2 text-black text-xs sm:text-sm font-semibold">
                  <span className="text-left">Trait</span>
                  <span className="text-right">Percentile&nbsp;Score</span>
                </div>
              </span>
            </th>
          </tr>
        </thead>

        <tbody className="text-white">
          {items.map((item) => (
            <React.Fragment key={item.key}>
              {/* ───────── header row ───────── */}
              <tr
                className="group cursor-pointer select-none"
                onClick={() => setOpenRow(openRow === item.key ? null : item.key)}
              >
                {/* first cell → left corners */}
                <td className="py-1 px-2 sm:px-6 capitalize rounded-l-lg group-hover:bg-white transition-colors">
                  <div className="flex flex-col">
                    <span className="font-bold text-black">{item.trait}</span>
                    <span className="text-[10px] font-bold text-gray-400">Press&nbsp;to&nbsp;expand</span>
                  </div>
                </td>

                {/* last cell → right corners */}
                <td className="py-3 px-4 sm:px-6 text-right rounded-r-lg group-hover:bg-white transition-colors">
                  <div className="flex items-center justify-end gap-2 text-black">
                    {/* tiny progress bar */}
                    <div className="h-1 w-16 sm:h-2 sm:w-24  bg-[#D4EEFF]">
                      <div
                        className="h-full rounded bg-emerald-500"
                        style={{ width: `${Math.min(item.percentile, 100)}%` }}
                      />
                    </div>
                    {item.percentile}
                  </div>
                </td>
              </tr>

              {/* ───────── detail row ───────── */}
              {openRow === item.key && (
                <tr className="bg-[#F9F9F9]">
                  <td colSpan={2} className="p-4 sm:p-6">
                    <p className="mb-2 font-semibold text-sm text-black">Dimensions</p>
                    <ul className="space-y-1">
                      {Object.entries(item.dimScores).map(([dim, val]) => (
                        <li key={dim} className="flex justify-between text-sm pl-3">
                          <span className="capitalize text-black">⤷ {dim}</span>
                          <span className="text-black">
                            {val}
                            {item.dimPcts[dim] !== undefined && (
                              <span className="ml-2 text-emerald-400">({item.dimPcts[dim]}%)</span>
                            )}
                          </span>
                        </li>
                      ))}
                    </ul>
                  </td>
                </tr>
              )}
            </React.Fragment>
          ))}
        </tbody>
      </table>
    </div>
  );
}
