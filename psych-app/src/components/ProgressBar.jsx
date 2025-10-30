// psych-app/src/components/ProgressBar.jsx

/*  Draggable ProgressBar
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
  /* ─────────── percentages ─────────── */
  const pct =
    total <= 1 ? 100 : Math.min(100, (current / (total - 1)) * 100);
  const thumbPct =
    idx != null ? (idx / (total - 1)) * 100 : null;

  /* ─────────── dragging helpers ─────────── */
  const barRef      = useRef(null);
  const draggingRef = useRef(false);

  const posToIdx = useCallback(
    clientX => {
      const bar = barRef.current;
      if (!bar) return 0;
      const { left, width } = bar.getBoundingClientRect();
      const ratio = Math.min(Math.max(0, (clientX - left) / width), 1);
      return Math.round(ratio * (total - 1));
    },
    [total],
  );

  const handleDown = e => {
    if (!onSeek) return;
    draggingRef.current = true;
    const wanted = posToIdx(e.clientX);
    if (wanted <= maxIdx) onSeek(wanted);
  };

  const handleMove = useCallback(
    e => {
      if (!draggingRef.current || !onSeek) return;
      const wanted = posToIdx(e.clientX);
      if (wanted <= maxIdx) onSeek(wanted);
    },
    [onSeek, posToIdx, maxIdx],
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
    <div
      ref={barRef}
      onPointerDown={handleDown}
      className={`relative z-20 w-full h-2 bg-[#EBEBEB] rounded-full select-none cursor-not-allowed `}
      style={{ touchAction: 'none' }}
    >
      {/* filled track */}
      <div
        className={`absolute left-0 top-0 h-2 bg-blue-400  rounded-full transition-[width] ${disabled ? 'cursor-not-allowed' : 'cursor-pointer'}`}
        style={{ width: `${pct}%` }}
      />

      {/* draggable thumb */}
      {onSeek && thumbPct != null && (
        <div
          className={
            "absolute top-1/2 h-7 w-7 -translate-y-1/2 rounded-full " +
            "bg-white border-4 transition-[left] " +
            (disabled
              ? "border-[#DEDEDE]  cursor-not-allowed"       // disabled look
              : "border-[black] shadow cursor-grab active:cursor-grabbing")
          }
          style={{
            left: `${thumbPct}%`,
            transform: 'translate(-50%, -50%)',
          }}
        >
          {/* twin chevrons */}
          <div className="absolute inset-0 flex items-center justify-center gap-0.5 pointer-events-none">
            <ChevronLeftIcon
              className={
                "w-3 h-3 " + (disabled ? "text-black" : "text-primary")
              }
              strokeWidth={3}
            />
            <ChevronRightIcon
              className={
                "w-3 h-3 " + (disabled ? "text-black" : "text-primary")
              }
              strokeWidth={3}
            />
          </div>
        </div>
      )}
    </div>
  );
}
