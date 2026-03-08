import { useEffect, useState, useMemo } from 'react';
import { listResults } from '../api/testing';
import clsx from 'clsx';
import Navbar from '../components/Navbar';
import DesktopTable from '../components/DesktopTable';
import MobileTable from '../components/MobileTable';

export default function Dashboard() {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        const response = await listResults();
        setResults(response.data);
      } catch (err) {
        console.error('Error loading dashboard data:', err);
        setResults([]);
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, []);

  const filteredResults = useMemo(() => {
    if (filter === 'completed') {
      return results.filter((r) => r.completed === true);
    }
    if (filter === 'in_progress') {
      return results.filter((r) => r.in_progress === true && r.completed === false);
    }
    return results;
  }, [results, filter]);

  return (
    <div className="flex flex-col h-screen overflow-hidden">
      {/* Shared utility styles */}
      <style>{`
        .hide-native-scrollbar::-webkit-scrollbar { display: none; }
        .hide-native-scrollbar { -ms-overflow-style: none; scrollbar-width: none; }
        .thead-fade th { position: relative; }
        .thead-fade::after {
          content: '';
          position: absolute;
          left: 0;
          right: 0;
          bottom: 0;
          height: 8px;
          background: linear-gradient(to bottom, rgba(0, 0, 0, 0.06), transparent);
          pointer-events: none;
          translate: 0 100%;
        }
      `}</style>

      <Navbar />

      {/* Dashboard content */}
      <div
        className="flex-1 flex flex-col min-h-0 px-0 py-0 sm:px-4 sm:py-6"
        style={{ maxWidth: 1280, width: '100%', margin: '0 auto' }}
      >
        {/* Card container */}
        <div
          className="flex-1 flex flex-col min-h-0 overflow-hidden"
          style={{ background: '#fff', border: '1px solid #dfe3e8' }}
        >
          {/* Header */}
          <div className="flex-shrink-0 px-3 pt-2 pb-2 sm:px-6 sm:pt-6 sm:pb-4">
            <div className="flex items-center justify-between gap-2 sm:flex-row sm:gap-4">
              <div className="flex-shrink-0">
                <h2 className="text-base sm:text-xl font-semibold text-slate-900">
                  Your Test Results
                </h2>
                <p className="hidden sm:block mt-1 text-sm text-slate-600">
                  View and manage all your psychometric test results
                </p>
              </div>

              {/* Filter Buttons */}
              <div className="flex gap-1 sm:gap-2">
                {[
                  { key: 'all', label: 'All' },
                  { key: 'completed', label: 'Done' },
                  { key: 'in_progress', label: 'Active' },
                ].map(({ key, label }) => (
                  <button
                    key={key}
                    onClick={() => setFilter(key)}
                    className={clsx(
                      'inline-flex items-center justify-center rounded px-2 py-1 text-xs sm:px-4 sm:py-2 sm:text-sm font-semibold transition',
                      filter === key
                        ? 'bg-[#210AA1] text-white'
                        : 'text-slate-700 hover:text-[#210AA1]'
                    )}
                    style={filter !== key ? { border: '1px solid #dfe3e8' } : {}}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {/* Body */}
          {loading ? (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#210AA1] mb-4 mx-auto" />
                <p className="text-slate-600">Loading your test results...</p>
              </div>
            </div>
          ) : filteredResults.length === 0 ? (
            <div className="flex-1 flex items-center justify-center p-8">
              <div className="rounded-2xl border border-dashed border-slate-300 p-8 bg-slate-50 text-center w-full max-w-md">
                <p className="text-slate-600">
                  {filter === 'completed'
                    ? 'No completed tests yet.'
                    : filter === 'in_progress'
                    ? 'No tests in progress.'
                    : 'No test results found. Start a test above to begin.'}
                </p>
              </div>
            </div>
          ) : (
            <>
              {/* Desktop: hidden on mobile, visible sm+ */}
              <div className="hidden sm:flex flex-1 min-h-0">
                <DesktopTable results={filteredResults} />
              </div>

              {/* Mobile: visible on small screens, hidden sm+ */}
              <div
                className="flex flex-col sm:hidden flex-1 min-h-0 overflow-hidden"
                style={{
                  maskImage: 'linear-gradient(to bottom, transparent 0%, black 32px, black calc(100% - 32px), transparent 100%)',
                  WebkitMaskImage: 'linear-gradient(to bottom, transparent 0%, black 32px, black calc(100% - 32px), transparent 100%)',
                }}
              >
                <MobileTable results={filteredResults} />
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}