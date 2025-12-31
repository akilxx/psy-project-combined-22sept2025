// psych-app/src/pages/Results.jsx
import React, { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

import { fetchResult, markComplete } from '../api/testing';
import ModifiedCard from '../components/ModifiedCard';
import ResultsTable from '../components/ResultsTable';   // ← your new table


export default function Results() {
  /* ───────── state ───────── */
  const { resultId }          = useParams();
  const [tr, setTr]           = useState(null);
  const [working, setWorking] = useState(false);
  const [error, setError]     = useState(null);
  

  /* ───────── helpers ───────── */
  const loadResult = () =>
    fetchResult(resultId).then((r) => setTr(r.data));

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

  // /* ───────── fetch once ───────── */
  // useEffect(() => {
  //   loadResult();
  //   // eslint-disable-next-line react-hooks/exhaustive-deps
  // }, [resultId]);


/* ───────── fetch once ───────── */
useEffect(() => {
  // wait 5 s before we call the API
  const timer = setTimeout(() => {
    loadResult();
  }, 0);

  // clear timeout if component unmounts or resultId changes
  return () => clearTimeout(timer);
  // eslint-disable-next-line react-hooks/exhaustive-deps
}, [resultId]);

  /* ───────── loading / not-ready states ───────── */

/* ───────── loading / not-ready states ───────── */
if (!tr) {
  return (
    <div className="">
      {/*  card: identical class list + `relative` for overlay  */}
      <ModifiedCard
        className="relative w-full max-w-2xl max-w-[80vw] max-h-[80vh]
                   overflow-hidden flex flex-col bg-[#fafafb] cursor-default"
      >
        {/* 1️⃣  Invisible skeleton that mimics TestRunner’s layout
               (progress-bar header + some body rows).           */}
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

        {/* 2️⃣  Spinner overlay, perfectly centred */}
        <div className="absolute inset-0 grid place-items-center">
          <div role="status" aria-label="Loading" className="loader" />
        </div>
      </ModifiedCard>
    </div>
  );
}





  const scores      = tr.scores      ?? [];
  const percentiles = tr.percentiles ?? [];

  // if (!scores.length) {
  //   return (
  //     <ModifiedCard className="page-card w-full max-w-[80vw] max-h-[80vh] overflow-auto bg-[#fafafb]">
  //       <div className="max-w-lg mx-auto mt-20 text-center">
  //         <h1 className="text-2xl font-semibold mb-4">
  //           Results not calculated yet
  //         </h1>
  //         <p className="mb-6">
  //           Scores and percentiles are generated once the test is marked&nbsp;complete.
  //         </p>

  //         {error && <p className="text-red-600 mb-2">{error}</p>}

  //         <button
  //           onClick={handleComplete}
  //           className="px-8 py-4 bg-emerald-600 text-white rounded-xl disabled:opacity-50"
  //           disabled={working}
  //         >
  //           {working ? 'Computing…' : 'Mark test as complete'}
  //         </button>
  //       </div>
  //     </ModifiedCard>
  //   );
  // }

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
