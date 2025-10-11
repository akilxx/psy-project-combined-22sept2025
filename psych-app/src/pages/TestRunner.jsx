//psych-app/src/pages/TestRunner.jsx
/*
    ————————————————————————————————————————————
    Redesigned assessment workspace:
    • Immersive gradient shell with elevated white workspace card
    • Header combines assessment identity with real-time progress snapshot
    • Two-column canvas: question area + navigation/controls sidebar
    • Option tiles animate with depth + ripple feedback
    • Sidebar offers quick jumps, previous/next controls, and submit state messaging
--------------------------------------------------------------------------- */
import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/react/24/outline';
import clsx from 'clsx';

import { fetchResult, submitAnswer, markComplete } from '../api/testing';
import ProgressBar from '../components/ProgressBar';
import ModifiedCard from '../components/ModifiedCard';
import RippleButton from '../components/RippleButton';

export default function TestRunner() {
  const { resultId } = useParams();
  const nav = useNavigate();

  /* ---------------- state ---------------- */
  const [test, setTest] = useState(null);
  const [answers, setAnswers] = useState({});
  const [idx, setIdx] = useState(null);
  const [error, setErr] = useState(null);
  const [inProgress, setInProgress] = useState(true);

  /* ---------------- initial fetch ---------------- */
  const load = useCallback(async () => {
    const { data } = await fetchResult(resultId);

    setTest(data.test);
    setAnswers(data.answers);
    setInProgress(Boolean(data.in_progress));

    const firstUnanswered = data.test.questions.findIndex(
      q => !data.answers[q.question_number],
    );
    setIdx(
      firstUnanswered === -1
        ? data.test.questions.length - 1
        : firstUnanswered,
    );
  }, [resultId]);

  useEffect(() => { load(); }, [load]);

  /* Helpers: same wrapper + card classes for all branches */
  const shellCls = `
    min-h-[calc(100vh-3.5rem)]
    bg-gradient-to-b from-slate-100 via-white to-slate-100
    px-3 sm:px-6 py-6 md:py-8
    flex justify-center
  `;

  const cardBaseCls = `
    w-full max-w-6xl h-full flex flex-col
    bg-white text-slate-900 cursor-default
    border border-slate-200 shadow-[0_35px_120px_-50px_rgba(15,23,42,0.6)]
    overflow-hidden
  `;

  /* ---------- completed-test view ---------- */
  if (!inProgress && test) {
    return (
      <div className={shellCls}>
        <ModifiedCard className={`${cardBaseCls} items-center justify-center text-center`}>
          <div className="max-w-xl space-y-6 px-8 py-12">
            <div className="inline-flex h-16 w-16 items-center justify-center rounded-2xl bg-slate-900 text-white shadow-lg shadow-slate-900/20">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                fill="none"
                viewBox="0 0 24 24"
                strokeWidth="1.5"
                stroke="currentColor"
                className="h-9 w-9"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  d="M9 12.75 11.25 15 15 9.75m6.75 2.25a9.75 9.75 0 1 1-19.5 0 9.75 9.75 0 0 1 19.5 0Z"
                />
              </svg>
            </div>
            <div className="space-y-3">
              <p className="text-sm uppercase tracking-[0.3em] text-slate-500">Assessment locked</p>
              <h2 className="text-3xl font-semibold text-slate-900">This test is already complete</h2>
              <p className="text-base text-slate-600">
                All questions were answered in a previous session. You can revisit your insights at any time from the results dashboard.
              </p>
            </div>
          </div>
        </ModifiedCard>
      </div>
    );
  }

  /* ---------- loading skeleton ---------- */
  if (!test || idx === null) {
    return (
      <div className={shellCls}>
        <ModifiedCard className={`${cardBaseCls} relative`}>
          <div className="flex flex-1 flex-col gap-12 px-10 py-12">
            <div className="space-y-3">
              <div className="h-4 w-32 animate-pulse rounded-full bg-slate-200" />
              <div className="h-10 w-2/3 animate-pulse rounded-full bg-slate-200" />
            </div>
            <div className="space-y-4">
              <div className="h-5 w-full animate-pulse rounded-full bg-slate-100" />
              <div className="h-5 w-11/12 animate-pulse rounded-full bg-slate-100" />
              <div className="h-5 w-10/12 animate-pulse rounded-full bg-slate-100" />
            </div>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {Array.from({ length: 6 }).map((_, i) => (
                <div key={i} className="h-16 animate-pulse rounded-2xl bg-slate-100" />
              ))}
            </div>
          </div>
          <div className="absolute inset-0 grid place-items-center">
            <div role="status" aria-label="Loading" className="loader" />
          </div>
        </ModifiedCard>
      </div>
    );
  }

  /* ---------- live test logic ---------- */
  const firstUnansweredIdx = test.questions.findIndex(
    q => !answers[q.question_number],
  );
  const liveIdx =
    firstUnansweredIdx === -1 ? test.questions.length : firstUnansweredIdx;
  const firstAnswered = Boolean(answers[test.questions[0].question_number]);
  const answeredCount = Object.keys(answers).length;

  const handleAnswer = async (qNum, ans) => {
    setAnswers(prev => {
      const next = { ...prev, [qNum]: { answer: ans } };
      if (idx === liveIdx && liveIdx < test.questions.length - 1) {
        setIdx(liveIdx + 1);
      }
      return next;
    });

    try {
      const { data } = await submitAnswer(resultId, qNum, ans);
      setAnswers(prev => ({ ...prev, ...data.answers }));
    } catch {
      setErr('Network error — retry by clicking again.');
    }
  };

  /* navigation helpers */
  const answeredIdxs = test.questions
    .map((q, i) => ({ i, answered: !!answers[q.question_number] }))
    .filter(({ answered }) => answered)
    .map(({ i }) => i);

  const allowedIdxs =
    liveIdx < test.questions.length
      ? [...answeredIdxs, liveIdx]
      : answeredIdxs;
  const answeredIdxSet = new Set(answeredIdxs);
  const allowedIdxsSet = new Set(allowedIdxs);

  const canGoPrev = answeredIdxs.some(i => i < idx);
  const canGoNext = allowedIdxs.some(i => i > idx);

  const goPrev = () => {
    if (!canGoPrev) return;
    const prev = [...answeredIdxs].filter(i => i < idx).pop();
    setIdx(prev);
  };

  const goNext = () => {
    if (!canGoNext) return;
    const next = [...allowedIdxs].filter(i => i > idx).shift();
    setIdx(next);
  };

  /* submit */
  const allAnswered = answeredCount === test.total_questions_number;

  const handleSubmit = async () => {
    if (!allAnswered) return;
    try {
      await markComplete(resultId);
    } catch (err) {
      console.error(err);
      setErr('We could not finalize your session. Please try again.');
      return;
    }
    nav(`/results/${resultId}`);
  };

  /* current question */
  const q = test.questions[idx];
  const prevAnswer = answers[q.question_number]?.answer;

  /* ---------- live render ---------- */
  return (
    <div className={shellCls}>
      <ModifiedCard className={cardBaseCls}>
        <header className="border-b border-slate-200 bg-slate-50 px-6 py-8 sm:px-10">
          <div className="flex flex-col gap-6">
            <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between">
              <div className="space-y-1">
                <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-500">Active assessment</p>
                <h1 className="text-2xl font-semibold text-slate-900">
                  {test.test_name ?? 'Psychometric session'}
                </h1>
              </div>
              <div className="flex items-end gap-3 rounded-2xl bg-white px-5 py-3 shadow-sm ring-1 ring-slate-200">
                <span className="text-3xl font-semibold text-slate-900">{answeredCount}</span>
                <div className="text-sm leading-tight text-slate-500">
                  <span className="block text-[11px] font-semibold uppercase tracking-[0.25em] text-slate-500">Answered</span>
                  <span className="block text-slate-900">{test.total_questions_number} total</span>
                </div>
              </div>
            </div>
            <div className="w-full max-w-3xl">
              <ProgressBar
                current={answeredCount}
                total={test.total_questions_number}
                idx={idx}
                maxIdx={liveIdx}
                onSeek={firstAnswered ? newIdx => setIdx(newIdx) : () => {}}
                disabled={!firstAnswered}
              />
            </div>
          </div>
        </header>

        <main className="flex-1 overflow-hidden px-6 py-8 sm:px-10 sm:py-10">
          <div className="grid h-full gap-10 lg:grid-cols-[minmax(0,1fr)_320px] xl:grid-cols-[minmax(0,1fr)_360px]">
            <div className="flex h-full flex-col gap-8 overflow-hidden">
              <div className="inline-flex w-fit items-center gap-3 rounded-2xl bg-slate-900 px-5 py-3 text-white shadow-lg shadow-slate-900/20">
                <span className="text-xs uppercase tracking-[0.35em] text-slate-300">Question</span>
                <span className="text-lg font-semibold">{q.question_number}</span>
              </div>

              {error && (
                <p className="rounded-2xl border border-red-200 bg-red-50 px-5 py-3 text-sm font-medium text-red-700 shadow-sm">
                  {error}
                </p>
              )}

              <div className="flex-1 space-y-8 overflow-y-auto pr-1">
                <div className="space-y-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-500">Prompt</p>
                  <h3
                    key={`qtxt-${q.question_number}`}
                    className="text-3xl font-semibold leading-snug text-slate-900"
                  >
                    {`${q.question_number}. ${q.text}`}
                  </h3>
                </div>

                <div className="space-y-3">
                  <p className="text-xs font-semibold uppercase tracking-[0.3em] text-slate-500">Choose one option</p>
                  <div className="grid gap-3 sm:grid-cols-2">
                    {test.options.map(opt => {
                      const selected = prevAnswer === opt;
                      return (
                        <RippleButton
                          key={`${q.question_number}-${opt}`}
                          onClick={() => handleAnswer(q.question_number, opt)}
                          className={clsx(
                            'group relative w-full min-w-0 overflow-hidden rounded-2xl border px-6 py-5 text-left text-base font-semibold transition-all duration-200',
                            'shadow-sm focus:outline-none',
                            selected
                              ? 'border-slate-900 bg-slate-900 text-white shadow-lg shadow-slate-900/20'
                              : 'border-slate-200 bg-white text-slate-800 hover:-translate-y-0.5 hover:border-slate-400 hover:shadow-lg hover:shadow-slate-200'
                          )}
                        >
                          <span className="block leading-snug">{opt}</span>
                        </RippleButton>
                      );
                    })}
                  </div>
                </div>
              </div>
            </div>

            <aside className="flex h-full flex-col gap-6 rounded-3xl border border-slate-200 bg-slate-50/80 p-6">
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase tracking-[0.35em] text-slate-500">Navigation</p>
                <h4 className="text-lg font-semibold text-slate-900">Jump to an item</h4>
                <p className="text-sm text-slate-600">
                  You can revisit any answered question or the live question in progress.
                </p>
              </div>

              <div className="flex-1 overflow-y-auto pr-1">
                <div className="grid grid-cols-4 gap-2 sm:grid-cols-5">
                  {test.questions.map((item, i) => {
                    const isActive = i === idx;
                    const isAnswered = answeredIdxSet.has(i);
                    const canOpen = allowedIdxsSet.has(i);
                    return (
                      <button
                        key={item.question_number}
                        type="button"
                        onClick={() => (canOpen ? setIdx(i) : null)}
                        disabled={!canOpen}
                        className={clsx(
                          'flex h-11 items-center justify-center rounded-xl border text-sm font-semibold transition-all duration-150',
                          'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-slate-900',
                          isActive
                            ? 'border-slate-900 bg-slate-900 text-white shadow-lg shadow-slate-900/20'
                            : isAnswered
                              ? 'border-slate-300 bg-white text-slate-900 hover:border-slate-400'
                              : 'border-dashed border-slate-300 bg-white text-slate-400',
                          !canOpen && 'cursor-not-allowed opacity-50'
                        )}
                      >
                        {item.question_number}
                      </button>
                    );
                  })}
                </div>
              </div>

              <div className="space-y-3">
                <div className="flex gap-3">
                  <button
                    type="button"
                    onClick={goPrev}
                    disabled={!canGoPrev}
                    className={clsx(
                      'flex flex-1 items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 shadow-sm transition-all duration-150',
                      'hover:-translate-y-0.5 hover:border-slate-400 hover:shadow-lg',
                      'disabled:translate-y-0 disabled:border-slate-200 disabled:text-slate-400 disabled:shadow-none disabled:cursor-not-allowed'
                    )}
                    aria-label="Previous answered item"
                  >
                    <ChevronLeftIcon className="h-5 w-5" />
                    <span>Previous</span>
                  </button>
                  <button
                    type="button"
                    onClick={goNext}
                    disabled={!canGoNext}
                    className={clsx(
                      'flex flex-1 items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm font-semibold text-slate-700 shadow-sm transition-all duration-150',
                      'hover:-translate-y-0.5 hover:border-slate-400 hover:shadow-lg',
                      'disabled:translate-y-0 disabled:border-slate-200 disabled:text-slate-400 disabled:shadow-none disabled:cursor-not-allowed'
                    )}
                    aria-label="Next available item"
                  >
                    <span>Next</span>
                    <ChevronRightIcon className="h-5 w-5" />
                  </button>
                </div>

                <RippleButton
                  onClick={handleSubmit}
                  disabled={!allAnswered}
                  className={clsx(
                    'w-full min-w-0 justify-center rounded-2xl border-0 px-6 py-4 text-sm font-semibold uppercase tracking-[0.3em]',
                    allAnswered
                      ? 'bg-slate-900 text-white shadow-xl shadow-slate-900/25 hover:bg-slate-800'
                      : 'bg-slate-200 text-slate-500 shadow-none'
                  )}
                >
                  Submit assessment
                </RippleButton>
                {allAnswered ? (
                  <p className="text-center text-xs font-medium uppercase tracking-[0.35em] text-emerald-600">Ready to submit</p>
                ) : (
                  <p className="text-center text-xs text-slate-500">
                    Answer every question to unlock submission.
                  </p>
                )}
              </div>
            </aside>
          </div>
        </main>
      </ModifiedCard>
    </div>
  );
}
