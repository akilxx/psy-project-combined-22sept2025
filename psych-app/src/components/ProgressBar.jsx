// psych-app/src/components/ProgressBar.jsx
import React, { useRef, useEffect, useCallback } from "react";

const BLUE_400 = "#60A5FA";   // Tailwind 'blue-400'
const GRAY_DISABLED = "#DEDEDE";

/* Mini tear badge with internal visual-centering + scalable path */
function TearBadgeMini({
  value = 60,
  width = 64,           // mobile default; desktop passes its own width
  fill = BLUE_400,
  stroke = BLUE_400,
  strokeWidth = 4,
  scale = 0.7,          // matches your original
  className = "",
}) {
  const VIEW_CENTER = 25;   // center of 50-wide viewBox
  const TEXT_CENTER = 17.8; // label center in original
  const dx = VIEW_CENTER - TEXT_CENTER; // shift so visual center == viewBox center

  return (
    <svg width={width} viewBox="0 0 50 42" aria-label={`Score ${value}`} className={className}>
      {/* shift to center the tear visually */}
      <g transform={`translate(${dx},0)`}>
        {/* scale the tear around center; text remains crisp */}
        <g transform={`translate(${VIEW_CENTER},0) scale(${scale}) translate(${-VIEW_CENTER},0)`}>
          <path
            d="M15 6
               Q 15 6, 25 18
               A 12.8 12.8 0 1 1 5 18
               Q 15 6 15 6z"
            fill={fill}
            stroke={stroke}
            strokeWidth={strokeWidth}
          />
        </g>
        <text
          x="17.8"
          y="18.7"
          textAnchor="middle"
          dominantBaseline="middle"
          fontSize={7}
          fontFamily="system-ui, sans-serif"
          fontWeight={700}
          fill="white"
        >
          {value}
        </text>
      </g>
    </svg>
  );
}

export default function ProgressBar({
  current,
  total,
  idx,
  maxIdx,
  onSeek,
  disabled = false,
}) {
  /* ── percentages (robust + aligned) ── */
  const safeTotal = Number.isFinite(total) ? Math.max(1, total) : 1;
  const clampIdx = (n) => Math.min(Math.max(0, n ?? 0), safeTotal - 1);
  const toPct = (i) => (safeTotal <= 1 ? 100 : (i / (safeTotal - 1)) * 100);

  const progressIndex = clampIdx(current);
  const thumbIndex = clampIdx(idx != null ? idx : progressIndex);

  const pct = toPct(progressIndex);
  const thumbPct = toPct(thumbIndex);

  /* ── dragging helpers ── */
  const barRef = useRef(null);
  const draggingRef = useRef(false);

  const posToIdx = useCallback(
    (clientX) => {
      const bar = barRef.current;
      if (!bar) return 0;
      const { left, width } = bar.getBoundingClientRect();
      const ratio = Math.min(Math.max(0, (clientX - left) / width), 1);
      return Math.round(ratio * (safeTotal - 1));
    },
    [safeTotal]
  );

  const handleDown = (e) => {
    if (!onSeek || disabled) return;
    draggingRef.current = true;
    const clientX = e.clientX ?? e.touches?.[0]?.clientX ?? 0;
    const wanted = posToIdx(clientX);
    if (wanted <= maxIdx) onSeek(wanted);
  };

  const handleMove = useCallback(
    (e) => {
      if (!draggingRef.current || !onSeek || disabled) return;
      const clientX = e.clientX ?? e.touches?.[0]?.clientX ?? 0;
      const wanted = posToIdx(clientX);
      if (wanted <= maxIdx) onSeek(wanted);
    },
    [onSeek, posToIdx, maxIdx, disabled]
  );

  const stopDrag = () => { draggingRef.current = false; };

  useEffect(() => {
    if (!onSeek) return;
    window.addEventListener("pointermove", handleMove);
    window.addEventListener("pointerup", stopDrag);
    return () => {
      window.removeEventListener("pointermove", handleMove);
      window.removeEventListener("pointerup", stopDrag);
    };
  }, [handleMove, onSeek]);

  /* ── render ── */
  return (
    <div className="w-full overflow-visible">
      {/* Keep bar unchanged; removing mobile scale keeps width aligned with question/grid columns */}
      <div className="w-full bg-[#F7F7F7] rounded-lg sm:rounded-xl overflow-visible px-3 sm:px-6 py-2 sm:py-4">
        <div
          ref={barRef}
          onPointerDown={handleDown}
          className={
            "relative z-20 w-full h-2 bg-[#E6E6E6] rounded-md sm:rounded-full select-none " +
            (disabled ? "cursor-not-allowed" : "cursor-pointer")
          }
          style={{ touchAction: "none" }}
        >
          {/* filled track */}
          <div
            className="absolute left-0 top-0 h-2 bg-blue-400 rounded-md sm:rounded-full transition-[width]"
            style={{ width: `${pct}%` }}
          />

          {/* thumb + tear */}
          {onSeek && !Number.isNaN(thumbPct) && (
            <div
              role="slider"
              aria-valuemin={0}
              aria-valuemax={maxIdx}
              aria-valuenow={thumbIndex}
              aria-disabled={disabled}
              tabIndex={disabled ? -1 : 0}
              onPointerDown={handleDown}
              className={
                "absolute top-1/2 rounded-full " +
                "h-3 w-3 sm:h-4 sm:w-4 border-2 " +
                "transition-[left] outline-none " +
                (disabled
                  ? "cursor-not-allowed"
                  : "shadow cursor-grab active:cursor-grabbing")
              }
              style={{
                left: `${Math.max(0, Math.min(100, thumbPct))}%`,
                transform: "translate(-50%, -50%)",
                backgroundColor: disabled ? GRAY_DISABLED : BLUE_400, // solid color, no opacity
                borderColor: disabled ? GRAY_DISABLED : BLUE_400,
              }}
            >
                {/* tear: top edge just below thumb; bottom hangs outside gray rectangle */}
                {/* Mobile tear */}
                <div
                  className={
                    "absolute left-1/2 top-full mt-0.5 sm:hidden " +
                    (disabled ? "pointer-events-none" : "pointer-events-auto")
                  }
                  style={{ transform: "translateX(-50%)" }}
                  onPointerDown={handleDown}
                >
                  <TearBadgeMini
                    value={thumbIndex + 1}
                    width={64}       /* mobile */
                    fill={disabled ? GRAY_DISABLED : BLUE_400}
                    stroke={disabled ? GRAY_DISABLED : BLUE_400}
                    strokeWidth={4}
                    scale={0.7}
                  />
                </div>

                {/* Desktop tear */}
                <div
                  className={
                    "absolute left-1/2 top-full sm:mt-1 hidden sm:block " +
                    (disabled ? "pointer-events-none" : "pointer-events-auto")
                  }
                  style={{ transform: "translateX(-50%)" }}
                  onPointerDown={handleDown}
                >
                  <TearBadgeMini
                    value={thumbIndex + 1}
                    width={84}       /* desktop */
                    fill={disabled ? GRAY_DISABLED : BLUE_400}
                    stroke={disabled ? GRAY_DISABLED : BLUE_400}
                    strokeWidth={4}
                    scale={0.7}
                  />
                </div>
              </div>
            )}
        </div>
      </div>
    </div>
  );
}
