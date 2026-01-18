// psych-app/src/pages/Dashboard.jsx
import { useEffect, useState, useMemo } from 'react';
import api from '../api/axios';
import { listResults } from '../api/testing';
import { Link } from 'react-router-dom';
import clsx from 'clsx';

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
      <span className="inline-flex items-center rounded-full bg-indigo-100 px-3 py-1 text-xs font-semibold text-indigo-700">
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

export default function Dashboard() {
  const [tests, setTests] = useState([]);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState('all'); // 'all', 'completed', 'in_progress'

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      try {
        // Load available tests
        api.get('/testing/tests/')
          .then(r => setTests(r.data))
          .catch(() => setTests([]));

        // Load test results
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
      return results.filter(r => r.completed === true);
    }
    if (filter === 'in_progress') {
      return results.filter(r => r.in_progress === true && r.completed === false);
    }
    return results;
  }, [results, filter]);

  return (
    <div className="mx-auto max-w-7xl px-4 py-10">
      {/* Header */}
      <div className="mb-8">
        <h1 className="text-3xl font-semibold text-slate-900">Dashboard</h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          View your test results and start new assessments.
        </p>
      </div>

      {/* Available Tests Section */}
      <div className="mb-10 rounded-2xl bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-slate-900 mb-4">Available Tests</h2>
        {tests.length === 0 ? (
          <p className="text-sm text-slate-500">No tests available at the moment.</p>
        ) : (
          <div className="grid md:grid-cols-2 gap-4">
            {tests.map(t => (
              <div
                key={t.id}
                className="flex flex-col gap-4 rounded-2xl border border-slate-200 bg-white p-6 transition hover:border-indigo-200 hover:shadow"
              >
                <h3 className="text-lg font-semibold text-slate-900">{t.test_name}</h3>
                <div className="flex flex-wrap gap-3">
                  <Link
                    to={`/test/start/${t.id}`}
                    className="inline-flex items-center justify-center rounded-xl bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-500 transition"
                  >
                    Standard runner
                  </Link>
                  <Link
                    to={`/test/start/${t.id}/alt`}
                    className="inline-flex items-center justify-center rounded-xl border border-indigo-200 px-4 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-50 transition"
                  >
                    Alternative runner
                  </Link>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Test Results Section */}
      <div className="rounded-2xl bg-white p-6 shadow-sm">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 mb-6">
          <div>
            <h2 className="text-xl font-semibold text-slate-900">Your Test Results</h2>
            <p className="mt-1 text-sm text-slate-600">
              View and manage all your psychometric test results
            </p>
          </div>

          {/* Filter Buttons */}
          <div className="flex gap-2">
            <button
              onClick={() => setFilter('all')}
              className={clsx(
                'inline-flex items-center justify-center rounded-xl px-4 py-2 text-sm font-semibold transition',
                filter === 'all'
                  ? 'bg-indigo-600 text-white'
                  : 'border border-slate-200 text-slate-700 hover:border-indigo-200 hover:text-indigo-700'
              )}
            >
              All Tests
            </button>
            <button
              onClick={() => setFilter('completed')}
              className={clsx(
                'inline-flex items-center justify-center rounded-xl px-4 py-2 text-sm font-semibold transition',
                filter === 'completed'
                  ? 'bg-indigo-600 text-white'
                  : 'border border-slate-200 text-slate-700 hover:border-indigo-200 hover:text-indigo-700'
              )}
            >
              Completed
            </button>
            <button
              onClick={() => setFilter('in_progress')}
              className={clsx(
                'inline-flex items-center justify-center rounded-xl px-4 py-2 text-sm font-semibold transition',
                filter === 'in_progress'
                  ? 'bg-indigo-600 text-white'
                  : 'border border-slate-200 text-slate-700 hover:border-indigo-200 hover:text-indigo-700'
              )}
            >
              In Progress
            </button>
          </div>
        </div>

        {loading ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mb-4 mx-auto"></div>
            <p className="text-slate-600">Loading your test results...</p>
          </div>
        ) : filteredResults.length === 0 ? (
          <div className="rounded-2xl border border-dashed border-slate-300 p-8 bg-slate-50 text-center">
            <p className="text-slate-600">
              {filter === 'completed'
                ? 'No completed tests yet.'
                : filter === 'in_progress'
                ? 'No tests in progress.'
                : 'No test results found. Start a test above to begin.'}
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b border-slate-200">
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
              <tbody className="divide-y divide-slate-200">
                {filteredResults.map(result => (
                  <tr key={result.uuid} className="hover:bg-slate-50 transition">
                    <td className="py-4 px-4 text-sm font-medium text-slate-900">
                      {result.test_name || 'Unknown Test'}
                    </td>
                    <td className="py-4 px-4">
                      <StatusBadge completed={result.completed} inProgress={result.in_progress} />
                    </td>
                    <td className="py-4 px-4 text-sm text-slate-900">
                      #{result.attempt_number}
                    </td>
                    <td className="py-4 px-4 text-sm text-slate-600">
                      {formatDate(result.created_at)}
                    </td>
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
                          className="inline-flex items-center justify-center rounded-lg bg-indigo-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-indigo-500 transition"
                        >
                          View Result
                        </Link>
                        {result.has_report && (
                          <Link
                            to={`/report/${result.uuid}`}
                            className="inline-flex items-center justify-center rounded-lg border border-indigo-200 px-3 py-1.5 text-xs font-semibold text-indigo-700 hover:bg-indigo-50 transition"
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
        )}
      </div>
    </div>
  );
}
