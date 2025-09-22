// psych-app/src/pages/TestStart.jsx
import { useNavigate, useParams } from 'react-router-dom';
import { useEffect, useState, useRef } from 'react';
import { startTest } from '../api/testing';
import useAuth from '../hooks/useAuth';
import { addAnonTest } from '../utils/anonTests';

export default function TestStart() {
  const { testId }  = useParams();
  const { user }    = useAuth();          // null when anonymous
  const navigate    = useNavigate();

  const [error, setError] = useState(null);
  const firedRef          = useRef(false);  // guard against double-execution

  /* ───────────────────── auto-start on mount ───────────────────── */
  useEffect(() => {
    if (firedRef.current) return;          // already ran once (StrictMode, etc.)
    firedRef.current = true;

    (async () => {
      try {
        // (1️)  create a new TestResult (POST /testing/test/start/)
        const { data } = await startTest(testId);

        // (2️)  stash UUID locally if user is not authenticated
        if (!user) addAnonTest(data.test_result_id);

        // (3️)  hand off to the live runner
        navigate(`/test/${data.test_result_id}`);
      } catch (err) {
        setError(
          err.response?.data?.detail ||
          'Could not start the test — please try again.'
        );
      }
    })();
  }, [testId, user, navigate]);

  /* ────────────────────────── UI states ────────────────────────── */
  if (error)
    return <p className="mt-20 text-center text-red-600">{error}</p>;

  return <p className="mt-20 text-center">Loading…</p>;
}
