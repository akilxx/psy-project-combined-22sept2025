import { useRef, useState, useEffect } from 'react';
import { Link } from 'react-router-dom';

/* ─── helpers ─── */
function formatDate(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleDateString(undefined, {
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

/* ─── single card ─── */
function ResultCard({ result, cardHeight }) {
  return (
    <div
      className="rounded-lg bg-white overflow-hidden"
      style={{
        border: '1px solid #dfe3e8',
        padding: '14px 16px',
        ...(cardHeight != null
          ? {
              height: cardHeight,
              flexShrink: 0,
              display: 'flex',
              flexDirection: 'column',
              justifyContent: 'space-between',
            }
          : {}),
      }}
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

/*
 * ─── LAYOUT MATH ───
 *
 * Available height = window.innerHeight − container.getBoundingClientRect().top
 * This bypasses the entire flex chain and gives us the real pixel space.
 *
 * We want: PAD + N × cardH + N × GAP + cardH/2 = availableH
 * Solve:   cardH = (availableH − PAD − N × GAP) / (N + 0.5)
 */

const GAP = 12;
const PAD = 12;
const FADE_HEIGHT = 32;

export default function MobileTable({ results }) {
  const wrapperRef = useRef(null);
  const measureRef = useRef(null);
  const scrollRef = useRef(null);
  const [cardHeight, setCardHeight] = useState(null);
  const [containerH, setContainerH] = useState(null);
  const [scrollPos, setScrollPos] = useState({ atTop: true, atBottom: false });

  useEffect(() => {
    function compute() {
      const wrapper = wrapperRef.current;
      const measureCard = measureRef.current;
      if (!wrapper || !measureCard) return;

      // Get real available pixels: from this element's top to the bottom of the screen
      const top = wrapper.getBoundingClientRect().top;
      const available = window.innerHeight - top;

      if (available <= 0) return;

      // Measure natural card height from the hidden card
      const naturalH = measureCard.getBoundingClientRect().height;
      if (naturalH <= 0) return;

      // How many full cards fit at natural size?
      const step = naturalH + GAP;
      const n = Math.max(Math.floor((available - PAD) / step), 1);

      // Solve for card height that makes N + 0.5 cards fill exactly
      const h = (available - PAD - n * GAP) / (n + 0.5);

      setCardHeight(h);
      setContainerH(available);
    }

    // Wait for layout to settle
    const raf = requestAnimationFrame(() => {
      requestAnimationFrame(compute);
    });

    window.addEventListener('resize', compute);
    return () => {
      cancelAnimationFrame(raf);
      window.removeEventListener('resize', compute);
    };
  }, [results]);

  /* Track scroll position to show/hide fades */
  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;

    function onScroll() {
      const atTop = el.scrollTop <= 2;
      const atBottom = el.scrollTop + el.clientHeight >= el.scrollHeight - 2;
      setScrollPos({ atTop, atBottom });
    }

    // Re-check after layout settles (cardHeight may have changed DOM sizes)
    const raf = requestAnimationFrame(() => {
      requestAnimationFrame(onScroll);
    });

    el.addEventListener('scroll', onScroll, { passive: true });
    return () => {
      cancelAnimationFrame(raf);
      el.removeEventListener('scroll', onScroll);
    };
  }, [results, cardHeight]);

  return (
    <div
      ref={wrapperRef}
      style={{
        position: 'relative',
        height: containerH != null ? containerH : '100%',
        overflow: 'hidden',
        flex: '1 1 0%',
        minHeight: 0,
      }}
    >
      {/* Hidden measure card — always at natural height */}
      {results.length > 0 && (
        <div
          ref={measureRef}
          aria-hidden="true"
          style={{
            position: 'absolute',
            visibility: 'hidden',
            pointerEvents: 'none',
            left: PAD,
            right: PAD,
            top: 0,
            zIndex: -1,
          }}
        >
          <ResultCard result={results[0]} cardHeight={undefined} />
        </div>
      )}

      {/* Top fade */}
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          height: FADE_HEIGHT,
          background: 'linear-gradient(to bottom, #ffffff 0%, rgba(255,255,255,0) 100%)',
          pointerEvents: 'none',
          zIndex: 2,
          opacity: scrollPos.atTop ? 0 : 1,
          transition: 'opacity 200ms ease',
        }}
      />

      {/* Bottom fade */}
      <div
        aria-hidden="true"
        style={{
          position: 'absolute',
          bottom: 0,
          left: 0,
          right: 0,
          height: FADE_HEIGHT,
          background: 'linear-gradient(to top, #ffffff 0%, rgba(255,255,255,0) 100%)',
          pointerEvents: 'none',
          zIndex: 2,
          opacity: scrollPos.atBottom ? 0 : 1,
          transition: 'opacity 200ms ease',
        }}
      />

      {/* Scrollable list */}
      <div
        ref={scrollRef}
        style={{
          position: 'absolute',
          top: 0,
          left: 0,
          right: 0,
          bottom: 0,
          overflowY: 'auto',
          overscrollBehavior: 'contain',
          WebkitOverflowScrolling: 'touch',
          padding: `${PAD}px ${PAD}px 0`,
        }}
      >
        {results.map((result) => (
          <div key={result.uuid} style={{ marginBottom: GAP }}>
            <ResultCard result={result} cardHeight={cardHeight} />
          </div>
        ))}
        {/* Spacer so the last card can be fully scrolled into view */}
        <div style={{ height: cardHeight != null ? cardHeight * 0.5 + PAD : 16 }} />
      </div>
    </div>
  );
}