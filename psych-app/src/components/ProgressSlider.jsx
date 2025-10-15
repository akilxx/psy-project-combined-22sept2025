// psych-app/src/components/ProgressSlider.jsx
import { useMemo } from 'react';

export default function ProgressSlider({
  value,
  min = 0,
  max = 100,
  onChange,
  disabled = false,
  minLabel,
  maxLabel,
  bubbleContent,
  fillPercent,
  ariaLabel = 'Progress slider',
}) {
  const { positionPercent, trackFillPercent, displayValue, computedMinLabel, computedMaxLabel } = useMemo(() => {
    const safeMin = Number.isFinite(min) ? min : 0;
    const safeMax = Number.isFinite(max) && max > safeMin ? max : safeMin + 1;
    const safeValue = Number.isFinite(value) ? value : safeMin;

    const range = safeMax - safeMin;
    const normalized = range === 0 ? 0 : ((safeValue - safeMin) / range) * 100;
    const position = Math.min(100, Math.max(0, normalized));

    const fill = typeof fillPercent === 'number' && Number.isFinite(fillPercent)
      ? Math.min(100, Math.max(0, fillPercent))
      : position;

    return {
      positionPercent: position,
      trackFillPercent: fill,
      displayValue: bubbleContent ?? `${Math.round(fill)}%`,
      computedMinLabel: minLabel ?? `${safeMin}`,
      computedMaxLabel: maxLabel ?? `${safeMax}`,
    };
  }, [bubbleContent, fillPercent, max, min, minLabel, maxLabel, value]);

  return (
    <div className={`rounded-2xl bg-slate-900 px-5 py-5 text-white ${disabled ? 'opacity-60' : ''}`}>
      <div className="flex items-center justify-between text-[10px] font-semibold uppercase tracking-wide text-slate-300">
        <span>{computedMinLabel}</span>
        <span>{computedMaxLabel}</span>
      </div>
      <div className="relative mt-6">
        <input
          type="range"
          min={min}
          max={max}
          step={1}
          value={value}
          onChange={disabled ? undefined : onChange}
          disabled={disabled}
          aria-label={ariaLabel}
          className="progress-slider"
          style={{ '--progress-percent': `${trackFillPercent}%` }}
        />
        <div
          className="pointer-events-none absolute -top-12 flex flex-col items-center"
          style={{ left: `${positionPercent}%`, transform: 'translateX(-50%)' }}
        >
          <div className="flex min-w-[2.5rem] items-center justify-center rounded-full bg-indigo-500 px-3 py-1 text-sm font-semibold text-white shadow-lg">
            {displayValue}
          </div>
          <div className="mt-[3px] h-2 w-2 rotate-45 bg-indigo-500" />
        </div>
      </div>
    </div>
  );
}
