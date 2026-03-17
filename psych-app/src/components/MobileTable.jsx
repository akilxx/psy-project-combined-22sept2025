import { useRef, useState, useEffect, useCallback } from 'react';
import { Link } from 'react-router-dom';

/* ─── helpers ─── */

function formatDate(value) {
  if (!value) return '—';
  const d = new Date(value);
  if (Number.isNaN(d.getTime())) return '—';
  return d.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function StatusBadge({ completed, inProgress }) {
  if (completed) {
    return (
      <span className="inline-flex items-center rounded-full bg-green-100 px-2.5 py-0.5 text-[11px] font-semibold text-green-700">
        Completed
      </span>
    );
  }
  if (inProgress) {
    return (
      <span className="inline-flex items-center rounded-full bg-amber-100 px-2.5 py-0.5 text-[11px] font-semibold text-amber-700">
        In Progress
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-semibold text-slate-700">
      Not Started
    </span>
  );
}

function ReportAccessBadge({ hasReport }) {
  if (hasReport) {
    return (
      <span className="inline-flex items-center rounded-full bg-[#210AA11a] px-2.5 py-0.5 text-[11px] font-semibold text-[#210AA1]">
        Available
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded-full bg-slate-100 px-2.5 py-0.5 text-[11px] font-semibold text-slate-600">
      Not Available
    </span>
  );
}

/* ─── card ─── */

function ResultCard({ result, height }) {
  const fixedStyle = height != null
    ? { height, flexShrink: 0, display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }
    : {};

  return (
    <div
      className="rounded-lg bg-white overflow-hidden"
      style={{ border: '1px solid #dfe3e8', padding: '14px 16px', ...fixedStyle }}
    >
      <div className="flex items-start justify-between gap-2">
        <h3 className="text-sm font-semibold text-slate-900 leading-snug">
          {result.test_name || 'Unknown Test'}
        </h3>
        <StatusBadge completed={result.completed} inProgress={result.in_progress} />
      </div>

      <div className="grid grid-cols-3 gap-y-2 gap-x-4 text-[12px]">
        <div>
          <span className="block text-slate-400 font-medium uppercase tracking-wider text-[10px] mb-0.5">
            Attempt
          </span>
          <span className="text-slate-800 font-medium">#{result.attempt_number}</span>
        </div>
        <div>
          <span className="block text-slate-400 font-medium uppercase tracking-wider text-[10px] mb-0.5">
            Started
          </span>
          <span className="text-slate-600">{formatDate(result.created_at)}</span>
        </div>
        <div>
          <span className="block text-slate-400 font-medium uppercase tracking-wider text-[10px] mb-0.5">
            Completed
          </span>
          <span className="text-slate-600">
            {result.completed ? formatDate(result.created_at) : '—'}
          </span>
        </div>
      </div>

      <div className="flex items-center justify-between gap-2">
        <div className="flex items-center gap-1.5">
          <span className="text-[10px] text-slate-400 font-medium uppercase tracking-wider">
            Report
          </span>
          <ReportAccessBadge hasReport={result.has_report} />
        </div>
        <div className="flex gap-2">
          <Link
            to={`/results/${result.uuid}`}
            className="inline-flex items-center justify-center rounded bg-[#210AA1] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#280CC2] transition active:scale-95"
          >
            View Result
          </Link>
          {result.has_report && (
            <Link
              to={`/report/${result.uuid}`}
              className="inline-flex items-center justify-center rounded px-3 py-1.5 text-xs font-semibold text-[#210AA1] hover:bg-[#210AA10d] transition active:scale-95"
              style={{ border: '1px solid #210AA144' }}
            >
              Report
            </Link>
          )}
        </div>
      </div>
    </div>
  );
}

/* ─── keyboard scroll handler ─── */

function handleScrollKeyDown(e) {
  const el = e.currentTarget;
  const smallScroll = 100;
  const largeScroll = el.clientHeight * 0.9;

  const keyActions = {
    ArrowDown: smallScroll,
    ArrowUp: -smallScroll,
    PageDown: largeScroll,
    PageUp: -largeScroll,
    ' ': e.shiftKey ? -largeScroll : largeScroll,
    Home: 'top',
    End: 'bottom',
  };

  const action = keyActions[e.key];
  if (action !== undefined) {
    e.preventDefault();
    if (action === 'top') {
      el.scrollTo({ top: 0, behavior: 'smooth' });
    } else if (action === 'bottom') {
      el.scrollTo({ top: el.scrollHeight, behavior: 'smooth' });
    } else {
      el.scrollBy({ top: action, behavior: 'smooth' });
    }
  }
}

/* ─── layout constants ─── */

const GAP = 32;
const PADDING = 32;
const TOP_FADE = 55;


/* ─── main component ─── */

export default function MobileTable({ results }) {
  const containerRef = useRef(null);
  const probeRef = useRef(null);
  const scrollRef = useRef(null);
  const [layout, setLayout] = useState(null);

  const measure = useCallback(() => {
    const container = containerRef.current;
    const probe = probeRef.current;
    if (!container || !probe) return;

    const available = window.innerHeight - container.getBoundingClientRect().top;
    if (available <= 0) return;

    const naturalHeight = probe.getBoundingClientRect().height;
    if (naturalHeight <= 0) return;

    const fullCards = Math.max(Math.floor((available - PADDING) / (naturalHeight + GAP)), 1);
    const cardHeight = (available - PADDING - fullCards * GAP) / (fullCards + 0.5);

    setLayout({ cardHeight, containerHeight: available });
  }, []);

  useEffect(() => {
    let raf = requestAnimationFrame(() => {
      raf = requestAnimationFrame(measure);
    });

    window.addEventListener('resize', measure);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', measure);
    };
  }, [measure, results]);

  // Auto-focus the scrollable div once layout is measured so keyboard
  // navigation works without requiring a click first
  useEffect(() => {
    if (layout && scrollRef.current) {
      scrollRef.current.focus({ preventScroll: true });
    }
  }, [layout]);

  const cardHeight = layout?.cardHeight ?? null;
  const containerHeight = layout?.containerHeight ?? null;

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        height: containerHeight ?? '100%',
        overflow: 'hidden',
        flex: '1 1 0%',
        minHeight: 0,
        /* Top fade only via mask — bottom is handled by the overlay */
        maskImage: `linear-gradient(to bottom, transparent 0px, black ${TOP_FADE}px, black 100%)`,
        WebkitMaskImage: `linear-gradient(to bottom, transparent 0px, black ${TOP_FADE}px, black 100%)`,
      }}
    >
      {/* Hidden probe card rendered at natural height for measurement */}
      {results.length > 0 && (
        <div
          ref={probeRef}
          aria-hidden="true"
          style={{
            position: 'absolute',
            visibility: 'hidden',
            pointerEvents: 'none',
            left: PADDING,
            right: PADDING,
            top: 0,
            zIndex: -1,
          }}
        >
          <ResultCard result={results[0]} height={undefined} />
        </div>
      )}

      {/* Scrollable card list */}
      <div
        ref={scrollRef}
        tabIndex={0}
        onKeyDown={handleScrollKeyDown}
        style={{
          position: 'absolute',
          inset: 0,
          overflowY: 'auto',
          overscrollBehavior: 'contain',
          padding: `${PADDING}px ${PADDING}px 0`,
          outline: 'none',
        }}
      >
        {results.map((result) => (
          <div key={result.uuid} style={{ marginBottom: GAP }}>
            <ResultCard result={result} height={cardHeight} />
          </div>
        ))}
        {/* Tail spacer — lets the last card scroll fully into view */}
        <div style={{ height: cardHeight != null ? cardHeight * 0.5 + PADDING : 16 }} />
      </div>

    </div>
  );
}