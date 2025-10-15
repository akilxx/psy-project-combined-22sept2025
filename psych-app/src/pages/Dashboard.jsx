// psych-app/src/pages/Dashboard.jsx  
import { useEffect, useState } from 'react';
import api from '../api/axios';
import { listResults } from '../api/testing';
import { Link } from 'react-router-dom';

export default function Dashboard() {
  const [tests, setTests] = useState([]);
  const [results, setResults] = useState([]);

  useEffect(() => {
    api.get('/testing/tests/')              // only if you created this endpoint
       .then(r => setTests(r.data))
       .catch(() => setTests([]));

    listResults().then(r => setResults(r.data));
  }, []);

  return (
    <div className="p-6">
      <h1 className="text-2xl font-semibold mb-4">Available Tests</h1>
      <div className="grid md:grid-cols-2 gap-4 mb-10">
        {tests.map(t => (
          <div
            key={t.id}
            className="flex flex-col gap-4 rounded-2xl bg-white p-6 shadow transition hover:shadow-lg"
          >
            <h3 className="text-lg font-semibold text-slate-900">{t.test_name}</h3>
            <div className="flex flex-wrap gap-3">
              <Link
                to={`/test/start/${t.id}`}
                className="inline-flex items-center justify-center rounded-lg bg-indigo-600 px-4 py-2 text-sm font-semibold text-white hover:bg-indigo-700"
              >
                Standard runner
              </Link>
              <Link
                to={`/test/start/${t.id}/alt`}
                className="inline-flex items-center justify-center rounded-lg border border-indigo-200 px-4 py-2 text-sm font-semibold text-indigo-700 hover:bg-indigo-50"
              >
                Alternative runner
              </Link>
            </div>
          </div>
        ))}
      </div>

      <h2 className="text-xl font-semibold mb-2">Your results</h2>
      {results.map(r => (
        <Link
          key={r.uuid}
          to={`/results/${r.uuid}`}
          className="block p-4 bg-slate-50 rounded-xl mb-2"
        >
          {r.test} — {r.completed ? 'Completed' : 'In progress'}
        </Link>
      ))}
    </div>
  );
}
