// psych-app/src/pages/Results.jsx
import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';

import { fetchResult, markComplete } from '../api/testing';
import ModifiedCard from '../components/ModifiedCard';
import ResultsTable from '../components/ResultsTable';

export default function Results() {
  /* ───────── state ───────── */
  const { resultId }          = useParams();
  const nav                   = useNavigate(); // FIX: Initialize navigation hook
  const [tr, setTr]           = useState(null);
  const [working, setWorking] = useState(false);
  const [error, setError]     = useState(null);

  /* ───────── helpers ───────── */
  const loadResult = async () => {
    try {
      // FIX: Await the fetch so we can catch the error
      const r = await fetchResult(resultId);
      setTr(r.data);
    } catch (err) {
      console.error("Load Result Error:", err);
      // FIX: Check for 404 and redirect
      if (err.response && err.response.status === 404) {
        nav('/login', { replace: true });
        return;
      }
      // Fallback: Set error message to display in UI
      setError(err.response?.data?.detail || 'Failed to load results.');
    }
  };

  const handleComplete = async () => {
    try {
      setWorking(true);
      await markComplete(resultId);
      await loadResult();
    } catch (e) {
      setError(e.response?.data?.detail || 'Could not mark complete');
    } finally {
      setWorking(false);
    }
  };

  /* ───────── fetch once ───────── */
  useEffect(() => {
    const timer = setTimeout(() => {
      loadResult();
    }, 0);

    return () => clearTimeout(timer);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resultId]);

  /* ───────── loading / not-ready states ───────── */
  if (!tr) {
    // FIX: If there is a non-404 error, show it instead of the spinner
    if (error) {
      return (
        <div className="min-h-screen w-full flex justify-center items-start px-4 pt-4">
          <ModifiedCard className="w-full max-w-lg mx-auto p-6 bg-[#fafafb] text-center">
             <h2 className="text-xl font-bold text-red-600 mb-2">Error</h2>
             <p className="mb-4 text-gray-700">{error}</p>
             <button 
                onClick={() => nav('/')} 
                className="px-4 py-2 bg-black text-white rounded-lg text-sm font-bold"
             >
                Return to Dashboard
             </button>
          </ModifiedCard>
        </div>
      );
    }

    return (
      <div className="">
        <ModifiedCard
          className="relative w-full max-w-2xl max-w-[80vw] max-h-[80vh]
                     overflow-hidden flex flex-col bg-[#fafafb] cursor-default"
        >
          {/* 1️⃣  Invisible skeleton */}
          <div className="px-6 pt-6 pb-0 invisible">
            <div className="h-4 w-4/5 md:w-7/8 mb-6 bg-transparent" />
          </div>
          <div className="flex-1 px-7 pt-0 pb-6 space-y-6 invisible">
            <div className="h-[120px] bg-transparent" />
            <div className="h-[240px] bg-transparent" />
          </div>
          <div className="px-7 pt-6 pb-6 invisible">
            <div className="h-10 bg-transparent" />
          </div>

          {/* 2️⃣  Spinner overlay */}
          <div className="absolute inset-0 grid place-items-center">
            <div role="status" aria-label="Loading" className="loader" />
          </div>
        </ModifiedCard>
      </div>
    );
  }

  const scores      = tr.scores      ?? [];
  const percentiles = tr.percentiles ?? [];

  /* ───────── derive per-row data for the table ───────── */
  const items = scores.map((sc) => {
    const p = percentiles.find((x) => x.trait === sc.trait) ?? {};
    return {
      key:        sc.trait,
      trait:      sc.trait,
      percentile: p.total_percentile ?? '—',
      dimScores:  sc.dimension_scores ?? {},
      dimPcts:    p.dimension_percentiles ?? {},
    };
  });

  /* ───────── render ───────── */
  return (
    <div className="min-h-screen w-full flex justify-center items-start px-4 pt-4">
      <ModifiedCard className="w-full max-w-[90vw] mx-auto p-0 bg-transparent overflow-visible">
        <div className="max-w-3xl mx-auto p-6">
          {/* page title */}
          <h2 className="w-fit mx-auto mb-6 px-3 py-1 text-black text-lg font-bold rounded-[10px] flex items-center gap-2 ">
            <span className="inline-block  text-black px-2 py-0.5 rounded-[6px]">
              Results&nbsp;:
            </span>
            <span className="text-black">{tr.test.test_name}</span>
          </h2>

          {/* custom table */}
          <ResultsTable items={items} />
        </div>
      </ModifiedCard>
    </div>
  );
}