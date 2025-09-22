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
          <Link
            key={t.id}
            to={`/test/start/${t.id}`}
            className="p-6 bg-white shadow rounded-2xl hover:shadow-lg transition"
          >
            {t.test_name}
          </Link>
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
