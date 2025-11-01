// psych-app/src/components/ProgressBar.jsx

/*  Draggable ProgressBar
    – mobile scales down uniformly; desktop is full size
    – less-rounded rectangle on mobile; full rounding on desktop
    – smaller mobile thumb (unchanged); slightly larger mobile side gap
    – thumb: dark-blue outline when active, unanswered-colour outline when disabled  */
import { useRef, useEffect, useCallback } from 'react';
import {
  ChevronLeftIcon,
  ChevronRightIcon,
} from '@heroicons/react/24/outline';

export default function ProgressBar({
  current,
  total,
  idx,
  maxIdx,
  onSeek,
  disabled = false,
}) {
  /* ─────────── percentages (robust + aligned) ─────────── */
  const safeTotal = Number.isFinite(total) ? Math.max(1, total) : 1;
  const clampIdx = (n) => Math.min(Math.max(0, n ?? 0), safeTotal - 1);
  const toPct = (i) => (safeTotal <= 1 ? 100 : (i / (safeTotal - 1)) * 100);

  const progressIndex = clampIdx(current);
  const thumbIndex = clampIdx(idx != null ? idx : progressIndex);

  const pct = toPct(progressIndex);
  const thumbPct = toPct(thumbIndex);

  /* ─────────── dragging helpers ─────────── */
  const barRef      = useRef(null);
  const draggingRef = useRef(false);

  const posToIdx = useCallback(
    (clientX) => {
      const bar = barRef.current;
      if (!bar) return 0;
      const { left, width } = bar.getBoundingClientRect();
      const ratio = Math.min(Math.max(0, (clientX - left) / width), 1);
      return Math.round(ratio * (safeTotal - 1));
    },
    [safeTotal],
  );

  const handleDown = (e) => {
    if (!onSeek || disabled) return;
    draggingRef.current = true;
    const wanted = posToIdx(e.clientX);
    if (wanted <= maxIdx) onSeek(wanted);
  };

  const handleMove = useCallback(
    (e) => {
      if (!draggingRef.current || !onSeek || disabled) return;
      const wanted = posToIdx(e.clientX);
      if (wanted <= maxIdx) onSeek(wanted);
    },
    [onSeek, posToIdx, maxIdx, disabled],
  );

  const stopDrag = () => { draggingRef.current = false; };

  useEffect(() => {
    if (!onSeek) return;
    window.addEventListener('pointermove', handleMove);
    window.addEventListener('pointerup',   stopDrag);
    return () => {
      window.removeEventListener('pointermove', handleMove);
      window.removeEventListener('pointerup',   stopDrag);
    };
  }, [handleMove, onSeek]);

  /* ─────────── render ─────────── */
  return (
    <div className="w-full overflow-visible">
      {/* Mobile-scaling wrapper: keep proportions but smaller on <sm */}
      <div className="transform-gpu origin-left scale-[0.88] sm:scale-100 will-change-transform">
        {/* Slightly increased mobile side gap: px-3; desktop unchanged */}
        <div className={`w-full bg-[#F7F7F7] rounded-lg sm:rounded-xl px-3 sm:px-6 py-2 sm:py-4 ${disabled ? 'opacity-70' : ''}`}>
          <div
            ref={barRef}
            onPointerDown={handleDown}
            className={
              "relative z-20 w-full h-2 bg-[#E6E6E6] rounded-md sm:rounded-full select-none " +
              (disabled ? "cursor-not-allowed" : "cursor-pointer")
            }
            style={{ touchAction: 'none' }}
          >
            {/* filled track */}
            <div
              className="absolute left-0 top-0 h-2 bg-blue-400 rounded-md sm:rounded-full transition-[width]"
              style={{ width: `${pct}%` }}
            />

            {/* draggable thumb (mobile size unchanged) */}
            {onSeek && !Number.isNaN(thumbPct) && (
              <div
                className={
                  "absolute top-1/2 rounded-full " +
                  "h-5 w-5 sm:h-7 sm:w-7 bg-white border-2 sm:border-4 " +
                  "transition-[left] " +
                  (disabled
                    ? "border-[#DEDEDE] cursor-not-allowed"
                    : "border-[black] shadow cursor-grab active:cursor-grabbing")
                }
                style={{
                  left: `${Math.max(0, Math.min(100, thumbPct))}%`,
                  transform: 'translate(-50%, -50%)',
                }}
              >
                <div className="absolute inset-0 flex items-center justify-center gap-0.5 pointer-events-none">
                  <ChevronLeftIcon
                    className={"w-2 h-2 sm:w-3 sm:h-3 " + (disabled ? "text-black" : "text-primary")}
                    strokeWidth={3}
                  />
                  <ChevronRightIcon
                    className={"w-2 h-2 sm:w-3 sm:h-3 " + (disabled ? "text-black" : "text-primary")}
                    strokeWidth={3}
                  />
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
