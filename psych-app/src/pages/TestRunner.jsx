//psych-app/src/pages/TestRunner.jsx
/*  
    ————————————————————————————————————————————
    • ModifiedCard styling reproduced inline (no Hero-UI Card context)
    • Unified vertical spacing rhythm
    • Side chevrons at inner edge of ModifiedCard (absolute; all breakpoints)
    • ProgressBar, question text, options grid, and Submit share identical width
    • Submit centered; aligned to answer grid width
--------------------------------------------------------------------------- */
import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ChevronLeftIcon, ChevronRightIcon } from '@heroicons/react/24/outline';
import clsx from 'clsx';

import { fetchResult, submitAnswer, markComplete } from '../api/testing';
import ProgressBar from '../components/ProgressBar';
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
  const wrapperCls = 'pt-4 px-2 flex justify-center';
  const cardBaseCls = `
    rounded-[40px] cursor-pointer relative text-white mx-auto
    w-full max-w-[90vw] h-auto max-h-[95vh]
    flex flex-col
    h-[calc(100vh-3.5rem-2rem)]      /* ~navbar + top/bottom gutters */
    bg-white
  `;

  /* Shared width + side padding for ProgressBar / Question / Grid / Submit
     NOTE: sidePadCls indents content so chevrons (abs-positioned at card edge)
     don't overlap the interactive elements. Adjust values if needed. */
  const contentMaxWCls = 'w-full max-w-5xl mx-auto';
  const sidePadCls = 'px-5 sm:px-16';
  const mobileSidePadCls = 'px-5';

  /* ---------- completed-test view ---------- */
  if (!inProgress && test) {
    return (
      <div className={wrapperCls}>
        <div className={cardBaseCls}>
          <div className="flex flex-1 items-center justify-center px-6">
            <div className="max-w-xl w-full rounded-lg bg-[#EBEBEB] p-6 text-center space-y-2">
              <h2 className="text-xl font-semibold text-black">This test has been completed</h2>
              <p className="text-gray-700">
                All items were answered previously. You can review your results from the dashboard.
              </p>
            </div>
          </div>
        </div>
      </div>
    );
  }

  /* ---------- loading skeleton ---------- */
  if (!test || idx === null) {
    return (
      <div className={wrapperCls}>
        <div className={cardBaseCls}>
          {/* invisible scaffold */}
          <div className="px-6 pt-6 pb-0 invisible">
            <div className="h-4 w-4/5 md:w-7/8 mb-6 bg-transparent" />
          </div>
          <div className="px-7 pt-0 pb-6 space-y-6 invisible">
            <div className="h-[120px] bg-transparent" />
            <div className="h-[240px] bg-transparent" />
          </div>
          <div className="px-7 pt-6 pb-6 invisible">
            <div className="h-10 bg-transparent" />
          </div>

          {/* centred spinner */}
          <div className="absolute inset-0 grid place-items-center">
            <div role="status" aria-label="Loading" className="loader" />
          </div>
        </div>
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
  const allAnswered = Object.keys(answers).length === test.total_questions_number;

  const handleSubmit = async () => {
    if (!allAnswered) return;
    try { await markComplete(resultId); } catch (_) {}
    nav(`/results/${resultId}`);
  };

  /* current question */
  const q = test.questions[idx];
  const prevAnswer = answers[q.question_number]?.answer;

  /* Reusable chevron button styles */
  const chevronBtnBase =
    'p-2 rounded-full text-black hover:bg-gray-200 disabled:text-gray-400 ' +
    'disabled:opacity-40 disabled:cursor-not-allowed';

  const renderOptions = () =>
    test.options.map(opt => {
      const selected = prevAnswer === opt;
      return (
        <RippleButton
          key={`${q.question_number}-${opt}`}
          onClick={() => handleAnswer(q.question_number, opt)}
          className={clsx(
            ' relative overflow-hidden py-2 px-4 font-bold rounded-[10px] transition border-0',

            selected
              ? 'bg-black text-white'
              : 'bg-[#EBEBEB] text-black hover:bg-[black] hover:text-[white] focus:outline-none',
          )}
        >
          <span className="inline-block animate-fadeIn">{opt}</span>
        </RippleButton>
      );
    });

  /* ---------- live render ---------- */
  return (
    <div className={wrapperCls}>
      <div className={cardBaseCls}>
        {/* header */}
        <header className="px-5 sm:px-7 pt-6 pb-0">
          {/* ProgressBar aligned to options grid width */}
          <div className={clsx(contentMaxWCls, sidePadCls)}>
            <ProgressBar
              current={Object.keys(answers).length}
              total={test.total_questions_number}
              idx={idx}
              maxIdx={liveIdx}
              onSeek={firstAnswered ? newIdx => setIdx(newIdx) : () => {}}
              disabled={!firstAnswered}
            />
          </div>
        </header>

        {/* body — drives all vertical spacing below ProgressBar */}
        <section className="px-5 sm:px-7 pt-10 pb-0">
          {/* Item pill */}
          <div className="flex justify-center mb-10">
            <h2 className="text-lg font-bold text-black inline-block bg-[#EBEBEB] px-3 py-1 rounded-[10px]">
              Item {q.question_number} of {test.total_questions_number}
            </h2>
          </div>

          {error && (
            <p className="text-red-600 text-center mb-4">
              {error}
            </p>
          )}

          {/* Question text aligned to grid */}
          <div 
            key={`qtxt-${q.question_number}`}
            className={clsx(contentMaxWCls, sidePadCls, 'mb-10 animate-fadeIn')}
          >
            <h3 className="text-2xl rounded-[10px] font-bold text-left text-black">
              {`${q.question_number}. ${q.text}`}
            </h3>
          </div>

          {/* answer grid with responsive chevrons */}
          <div className="relative w-full">
            <button
              onClick={goPrev}
              disabled={!canGoPrev}
              className={clsx(
                chevronBtnBase,
                'hidden sm:inline-flex absolute left-0 top-1/2 -translate-y-1/2'
              )}
              aria-label="Previous answered item"
            >
              <ChevronLeftIcon className="w-10 h-10" strokeWidth={canGoPrev ? 3 : 2} />
            </button>

            <div
              className={clsx(
                contentMaxWCls,
                'grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3',
                sidePadCls
              )}
            >
              {renderOptions()}
            </div>

            <button
              onClick={goNext}
              disabled={!canGoNext}
              className={clsx(
                chevronBtnBase,
                'hidden sm:inline-flex absolute right-0 top-1/2 -translate-y-1/2'
              )}
              aria-label="Next answered item"
            >
              <ChevronRightIcon className="w-10 h-10" strokeWidth={canGoNext ? 3 : 2} />
            </button>
          </div>
        </section>

        {/* footer — equal gap below answers, aligned to grid */}
        <footer className="px-5 sm:px-7 pb-6 mt-16 sm:mt-20 lg:mt-28 space-y-4 sm:space-y-0">
          <div
            className={clsx(
              contentMaxWCls,
              mobileSidePadCls,
              'flex items-center justify-center gap-6 sm:hidden'
            )}
          >
            <button
              onClick={goPrev}
              disabled={!canGoPrev}
              className={clsx(chevronBtnBase)}
              aria-label="Previous answered item"
            >
              <ChevronLeftIcon className="w-10 h-10" strokeWidth={canGoPrev ? 3 : 2} />
            </button>

            <RippleButton
              onClick={handleSubmit}
              disabled={!allAnswered}
              className={clsx(
                'px-8 py-3 leading-[16px] rounded-[10px] font-bold',
                'bg-[#293ABF] text-[white]',
                'disabled:bg-[#EBEBEB] disabled:text-gray-400 disabled:cursor-not-allowed',
                allAnswered && 'hover:bg-[black] hover:text-[white]'
              )}
            >
              Submit
            </RippleButton>

            <button
              onClick={goNext}
              disabled={!canGoNext}
              className={clsx(chevronBtnBase)}
              aria-label="Next answered item"
            >
              <ChevronRightIcon className="w-10 h-10" strokeWidth={canGoNext ? 3 : 2} />
            </button>
          </div>

          <div className={clsx(contentMaxWCls, sidePadCls, 'hidden sm:flex justify-center')}>
            <RippleButton
              onClick={handleSubmit}
              disabled={!allAnswered}
              className={clsx(
                          "px-8 py-3 leading-[16px] rounded-[10px] font-bold",
                          "bg-[#293ABF] text-[white]",
                          "disabled:bg-[#EBEBEB] disabled:text-gray-400 disabled:cursor-not-allowed",
                          allAnswered && "hover:bg-[black] hover:text-[white]"
                        )}
            >
              Submit
            </RippleButton>
          </div>
        </footer>
      </div>
    </div>
  );
}
