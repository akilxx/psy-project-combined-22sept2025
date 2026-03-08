import { useRef, useEffect, useState, useCallback } from 'react';
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
      <span className="inline-flex items-center rounded-full bg-green-100 px-3 py-1 text-xs font-semibold text-green-700">
        Completed
      </span>
    );
  }
  if (inProgress) {
    return (
      <span className="inline-flex items-center rounded-full bg-amber-100 px-3 py-1 text-xs font-semibold text-amber-700">
        In Progress
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-700">
      Not Started
    </span>
  );
}

function ReportAccessBadge({ hasReport }) {
  if (hasReport) {
    return (
      <span className="inline-flex items-center rounded-full bg-[#210AA11a] px-3 py-1 text-xs font-semibold text-[#210AA1]">
        Available
      </span>
    );
  }
  return (
    <span className="inline-flex items-center rounded-full bg-slate-100 px-3 py-1 text-xs font-semibold text-slate-600">
      Not Available
    </span>
  );
}

/* ─── custom scrollbar ─── */
function SwiperScrollbar({ scrollRef }) {
  const trackRef = useRef(null);
  const [thumbRatio, setThumbRatio] = useState(0);
  const [scrollRatio, setScrollRatio] = useState(0);
  const [trackHeight, setTrackHeight] = useState(0);
  const [isDragging, setIsDragging] = useState(false);
  const [isHovered, setIsHovered] = useState(false);
  const dragStartY = useRef(0);
  const dragStartScroll = useRef(0);

  const update = useCallback(() => {
    const el = scrollRef.current;
    const track = trackRef.current;
    if (!el) return;
    if (track) setTrackHeight(track.getBoundingClientRect().height);
    const { scrollTop, scrollHeight, clientHeight } = el;
    if (scrollHeight <= clientHeight) {
      setThumbRatio(0);
      setScrollRatio(0);
    } else {
      setThumbRatio(clientHeight / scrollHeight);
      setScrollRatio(scrollTop / (scrollHeight - clientHeight));
    }
  }, [scrollRef]);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    update();
    el.addEventListener('scroll', update, { passive: true });
    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => {
      el.removeEventListener('scroll', update);
      ro.disconnect();
    };
  }, [scrollRef, update]);

  useEffect(() => {
    if (!isDragging) return;
    const onMove = (e) => {
      const el = scrollRef.current;
      const track = trackRef.current;
      if (!el || !track) return;
      const clientY = e.touches ? e.touches[0].clientY : e.clientY;
      const delta = clientY - dragStartY.current;
      const h = track.getBoundingClientRect().height;
      const thumbH = Math.max(h * thumbRatio, 30);
      const scrollableTrack = h - thumbH;
      if (scrollableTrack <= 0) return;
      const scrollFraction = delta / scrollableTrack;
      const maxScroll = el.scrollHeight - el.clientHeight;
      el.scrollTop = dragStartScroll.current + scrollFraction * maxScroll;
    };
    const onUp = () => setIsDragging(false);
    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
    window.addEventListener('touchmove', onMove, { passive: false });
    window.addEventListener('touchend', onUp);
    return () => {
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
      window.removeEventListener('touchmove', onMove);
      window.removeEventListener('touchend', onUp);
    };
  }, [isDragging, scrollRef, thumbRatio]);

  const onThumbDown = (e) => {
    e.preventDefault();
    const clientY = e.touches ? e.touches[0].clientY : e.clientY;
    dragStartY.current = clientY;
    dragStartScroll.current = scrollRef.current?.scrollTop || 0;
    setIsDragging(true);
  };

  const onTrackClick = (e) => {
    const el = scrollRef.current;
    const track = trackRef.current;
    if (!el || !track || e.target !== track) return;
    const rect = track.getBoundingClientRect();
    const clickY = e.clientY - rect.top;
    const fraction = clickY / rect.height;
    el.scrollTop = fraction * (el.scrollHeight - el.clientHeight);
  };

  if (thumbRatio === 0 || thumbRatio >= 1) return null;

  const thumbHeight = Math.max(thumbRatio * trackHeight, 30);
  const maxTop = trackHeight - thumbHeight;
  const thumbTopPx = scrollRatio * maxTop;

  return (
    <div
      ref={trackRef}
      onClick={onTrackClick}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
      style={{
        position: 'absolute',
        top: 0,
        right: 0,
        bottom: 0,
        width: 12,
        background: '#e8e8e8',
        cursor: 'pointer',
        zIndex: 20,
        transition: 'opacity 0.2s',
        opacity: isDragging || isHovered ? 1 : 0.7,
      }}
    >
      <div
        onMouseDown={onThumbDown}
        onTouchStart={onThumbDown}
        style={{
          position: 'absolute',
          top: thumbTopPx,
          left: 0,
          right: 0,
          height: thumbHeight,
          background: isDragging
            ? 'rgba(0,0,0,0.55)'
            : isHovered
            ? 'rgba(0,0,0,0.45)'
            : 'rgba(0,0,0,0.35)',
          cursor: 'grab',
          transition: isDragging ? 'none' : 'background 0.15s',
          userSelect: 'none',
        }}
      />
    </div>
  );
}

/* ─── DesktopTable ─── */
export default function DesktopTable({ results }) {
  const tableScrollRef = useRef(null);

  // Keyboard-driven scrolling
  useEffect(() => {
    const SCROLL_AMOUNT = 60;
    const handleKeyDown = (e) => {
      const el = tableScrollRef.current;
      if (!el) return;
      if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;

      switch (e.key) {
        case 'ArrowDown':
          e.preventDefault();
          el.scrollTop += SCROLL_AMOUNT;
          break;
        case 'ArrowUp':
          e.preventDefault();
          el.scrollTop -= SCROLL_AMOUNT;
          break;
        case 'PageDown':
          e.preventDefault();
          el.scrollTop += el.clientHeight;
          break;
        case 'PageUp':
          e.preventDefault();
          el.scrollTop -= el.clientHeight;
          break;
        case 'Home':
          e.preventDefault();
          el.scrollTop = 0;
          break;
        case 'End':
          e.preventDefault();
          el.scrollTop = el.scrollHeight;
          break;
        default:
          break;
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return (
    <div className="flex-1 min-h-0 relative">
      <div
        ref={tableScrollRef}
        className="hide-native-scrollbar absolute overflow-auto focus:outline-none pr-3"
        style={{ top: 0, left: 0, right: 0, bottom: 0 }}
        tabIndex={0}
      >
        <table className="w-full">
          <thead className="thead-fade sticky top-0 z-20" style={{ background: '#fff' }}>
            <tr>
              <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wide">
                Test Name
              </th>
              <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wide">
                Status
              </th>
              <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wide">
                Attempt
              </th>
              <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wide">
                Started
              </th>
              <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wide">
                Completed
              </th>
              <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wide">
                Report
              </th>
              <th className="text-left py-3 px-4 text-xs font-semibold text-slate-600 uppercase tracking-wide">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            {results.map((result) => (
              <tr
                key={result.uuid}
                className="hover:bg-slate-50 transition"
                style={{ borderBottom: '1px solid #dfe3e8' }}
              >
                <td className="py-4 px-4 text-sm font-medium text-slate-900">
                  {result.test_name || 'Unknown Test'}
                </td>
                <td className="py-4 px-4">
                  <StatusBadge completed={result.completed} inProgress={result.in_progress} />
                </td>
                <td className="py-4 px-4 text-sm text-slate-900">#{result.attempt_number}</td>
                <td className="py-4 px-4 text-sm text-slate-600">{formatDate(result.created_at)}</td>
                <td className="py-4 px-4 text-sm text-slate-600">
                  {result.completed ? formatDate(result.created_at) : '—'}
                </td>
                <td className="py-4 px-4">
                  <ReportAccessBadge hasReport={result.has_report} />
                </td>
                <td className="py-4 px-4">
                  <div className="flex gap-2">
                    <Link
                      to={`/results/${result.uuid}`}
                      className="inline-flex items-center justify-center rounded bg-[#210AA1] px-3 py-1.5 text-xs font-semibold text-white hover:bg-[#280CC2] transition"
                    >
                      View Result
                    </Link>
                    {result.has_report && (
                      <Link
                        to={`/report/${result.uuid}`}
                        className="inline-flex items-center justify-center rounded px-3 py-1.5 text-xs font-semibold text-[#210AA1] hover:bg-[#210AA10d] transition"
                        style={{ border: '1px solid #210AA144' }}
                      >
                        View Report
                      </Link>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <SwiperScrollbar scrollRef={tableScrollRef} />

      {/* Top fade */}
      <div
        className="absolute left-0 right-0 pointer-events-none z-10"
        style={{
          top: 0,
          height: 60,
          background: 'linear-gradient(to bottom, rgba(255,255,255,1), rgba(255,255,255,0))',
        }}
      />
      {/* Bottom fade */}
      <div
        className="absolute left-0 right-0 pointer-events-none z-10"
        style={{
          bottom: 0,
          height: 8,
          background: 'linear-gradient(to top, rgba(0, 0, 0, 0.06), transparent)',
        }}
      />
    </div>
  );
}