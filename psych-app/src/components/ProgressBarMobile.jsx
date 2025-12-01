// psych-app/src/components/ProgressBarMobile.jsx
import React, { useRef, useEffect, useCallback } from "react";

const GREEN = "#10B982"; // Tailwind 'blue-400'
const GRAY_DISABLED = "#DEDEDE";

function ProgressBarMobile({
  current,
  total,
  idx,
  maxIdx,
  onSeek,
  disabled = false,
}) {
  const safeTotal = Number.isFinite(total) ? Math.max(1, total) : 1;
  const clampIdx = (n) => Math.min(Math.max(0, n ?? 0), safeTotal - 1);
  const toPct = (i) => (safeTotal <= 1 ? 100 : (i / (safeTotal - 1)) * 100);

  const progressIndex = clampIdx(current);
  const thumbIndex = clampIdx(idx != null ? idx : progressIndex);

  const pct = toPct(progressIndex);
  const thumbPct = toPct(thumbIndex);
  const displayValue = thumbIndex + 1; // 1-based for display

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

  const stopDrag = () => {
    draggingRef.current = false;
  };

  useEffect(() => {
    if (!onSeek) return;
    window.addEventListener("pointermove", handleMove);
    window.addEventListener("pointerup", stopDrag);
    return () => {
      window.removeEventListener("pointermove", handleMove);
      window.removeEventListener("pointerup", stopDrag);
    };
  }, [handleMove, onSeek]);

  return (
    <div className="w-full overflow-visible">
      {/* Increased padding here to create more breathing room for the thumb */}
      <div className="w-full bg-[#F7F7F7] rounded-xl sm:rounded-2xl overflow-visible px-4 sm:px-8 py-3 sm:py-5">
        <div
          ref={barRef}
          onPointerDown={handleDown}
          className={
            "relative z-20 w-full h-2 bg-[#E6E6E6] rounded-md sm:rounded-full select-none " +
            (disabled ? "cursor-not-allowed" : "cursor-pointer")
          }
          style={{ touchAction: "none" }}
        >
          <div
            className="absolute left-0 top-0 h-2 bg-[#10B982] rounded-md sm:rounded-full transition-[width]"
            style={{ width: `${pct}%` }}
          />

          {onSeek && !Number.isNaN(thumbPct) && (
            <div
              role="slider"
              aria-valuemin={1}
              aria-valuemax={maxIdx + 1}
              aria-valuenow={displayValue}
              aria-disabled={disabled}
              tabIndex={disabled ? -1 : 0}
              onPointerDown={handleDown}
              className={
                "absolute top-1/2 rounded-full border-2 transition-[left] outline-none " +
                "flex items-center justify-center " +
                "h-6 w-6 sm:h-7 sm:w-7 text-[10px] sm:text-xs font-semibold text-white select-none " +
                (disabled
                  ? "cursor-not-allowed"
                  : "shadow cursor-grab active:cursor-grabbing")
              }
              style={{
                left: `${Math.max(0, Math.min(100, thumbPct))}%`,
                transform: "translate(-50%, -50%)",
                backgroundColor: disabled ? GRAY_DISABLED : GREEN,
                borderColor: disabled ? GRAY_DISABLED : GREEN,
              }}
            >
              {displayValue}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

export default ProgressBarMobile;
