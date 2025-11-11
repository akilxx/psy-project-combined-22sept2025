// psych-app/src/pages/TestRunner.jsx
/*
    ————————————————————————————————————————————
    • Layout previously wrapped by ModifiedCard now renders directly on page
    • Unified vertical spacing rhythm
    • Side chevrons aligned to answer grid (absolute; all breakpoints)
    • ProgressBar, question text, options grid, and Submit share identical width
    • Submit centered; aligned to answer grid width
--------------------------------------------------------------------------- */
import { useState, useEffect, useCallback } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import clsx from 'clsx';
import AnimatedSubmitButton from '../components/AnimatedSubmitButton';
import Chevron from '../components/Chevron';
import { fetchResult, submitAnswer, markComplete } from '../api/testing';
import ProgressBar from '../components/ProgressBar';
import ProgressBarMobile from '../components/ProgressBarMobile';
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

  /* 🧠 HOOKS MUST STAY ABOVE ANY EARLY RETURN */
  const handleSeek = useCallback((newIdx) => setIdx(newIdx), []);

  /* Helpers: same wrapper + card classes for all branches */
  const wrapperCls = 'pt-4 px-2 flex justify-center';
  const layoutCls = `
    relative mx-auto flex w-full max-w-[90vw] max-h-[95vh] flex-col
    h-[calc(100vh-3.5rem-2rem)]      /* ~navbar + top/bottom gutters */
  `;

  /* Shared width + side padding for ProgressBar / Question / Grid / Submit */
  const contentMaxWCls = 'w-full max-w-5xl mx-auto';
  const sidePadCls = 'px-5 sm:px-16';
  const mobileSidePadCls = 'px-5';

  /* ---------- completed-test view ---------- */
  if (!inProgress && test) {
    return (
      <div className={wrapperCls}>
        <div className={layoutCls}>
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
        <div className={layoutCls}>
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

  // Safe guard (prevents crash if questions array is empty)
  const firstAnswered =
    Array.isArray(test?.questions) && test.questions.length > 0
      ? Boolean(answers[test.questions[0].question_number])
      : false;

  const handleAnswer = async (qNum, ans) => {
    const shouldAutoAdvance = idx === liveIdx && liveIdx < test.questions.length - 1;

    setAnswers(prev => ({ ...prev, [qNum]: { answer: ans } }));

    // RippleButton gates onClick until ripple ends; advance immediately here.
    if (shouldAutoAdvance) setIdx(idx + 1);

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
    try {
      await markComplete(resultId);
    } catch (err) {
      console.warn('markComplete failed', err);
    }
    nav(`/results/${resultId}`);
  };

  /* current question */
  const q = test.questions[idx];
  const prevAnswer = answers[q.question_number]?.answer;
  /* --- mobile question sizing based on longest question --- */
  const maxQuestionChars = Array.isArray(test.questions)
    ? Math.max(...test.questions.map(item => (item.text || '').length))
    : 0;

  // Tune aggressively so the longest question fits ~2 lines on small screens.
  let mobileQuestionSizeCls;
  if (maxQuestionChars <= 70) {
    // Shortest set → can be comfortably large
    mobileQuestionSizeCls = 'text-xl';
  } else if (maxQuestionChars <= 110) {
    mobileQuestionSizeCls = 'text-lg';
  } else {
    // Very long items → shrink further
    mobileQuestionSizeCls = 'text-base';
  }
    /* mobile option width (used in renderOptions) */
  const longestOptionChars = Array.isArray(test.options)
    ? Math.max(...test.options.map(o => o?.length ?? 0))
    : 0;

  const mobileMinCh = Math.max(8, Math.min(60, longestOptionChars + 2));


  /* Reusable chevron button styles */
  const chevronBtnBase =
  'group p-2 text-black bg-transparent ' +
  'disabled:text-gray-400 disabled:opacity-40 disabled:cursor-not-allowed';

  const renderOptions = () =>
    test.options.map(opt => {
      const selected = prevAnswer === opt;
      return (
        <div
          key={`${q.question_number}-${opt}`}
          className="justify-self-center sm:justify-self-stretch w-auto sm:w-full"
          style={{ minWidth: `${mobileMinCh}ch` }}
        >
          <RippleButton
            onClick={() => handleAnswer(q.question_number, opt)}
            className={clsx(
              'w-full relative overflow-hidden whitespace-nowrap text-center py-1 px-3 sm:px-4 font-bold rounded-[10px] transition',
              
              selected
                ? 'bg-black text-white text-sm border border-black'
                : 'bg-blue-50 text-black text-sm hover:bg-black border border-blue-100 hover:text-white hover:border-black',
            )}
          >
            <span className="inline-block animate-fadeIn">{opt}</span>
          </RippleButton>
        </div>
      );
    });


  /* ---------- live render ---------- */
  return (
    <div className={wrapperCls}>
      <div className={layoutCls}>
        {/* header */}
        <header className="px-5 sm:px-7 pt-6 pb-0">
          {/* Item pill: desktop / tablet only */}
          <div className="hidden sm:flex justify-center mb-10">
            <h2 className="text-xl font-bold text-[#B5B5B5] inline-block bg-[white] px-3 py-1 rounded-[10px]">
              Item {q.question_number} of {test.total_questions_number}
            </h2>
          </div>

          {/* Progress aligned to content width */}
          <div className={clsx(contentMaxWCls, sidePadCls)}>
            {/* Desktop / tablet */}
            <div className="hidden sm:block">
              <ProgressBar
                current={Object.keys(answers).length}
                total={test.total_questions_number}
                idx={idx}
                maxIdx={liveIdx}
                onSeek={firstAnswered ? handleSeek : () => {}}
                disabled={!firstAnswered}
              />
            </div>
            
          </div>
        </header>

        {/* body */}
        <section className="px-5 sm:px-7 pt-10 pb-0">

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
            <div
              className={clsx(
                'rounded-[10px] font-bold text-left text-black leading-snug',
                // Mobile: dynamic size based on longest question
                mobileQuestionSizeCls,
                // Desktop / tablet: fixed larger size
                'sm:text-2xl',
                // Mobile: fixed 2-line block to keep layout stable
                'h-[4.5rem] sm:h-auto flex items-center'
              )}
            >
              <span>{`${q.question_number}. ${q.text}`}</span>
            </div>
          </div>



          {/* answer grid + chevrons */}
          <div className="relative w-full">
            {/* LEFT chevron */}
            <button
              onClick={goPrev}
              disabled={!canGoPrev}
              className={clsx(
                chevronBtnBase,
                'inline-flex absolute top-1/2 -translate-y-1/2 z-10',
                // Mobile: push closer to viewport edge, away from options
                'left-0 -translate-x-4',
                // sm+: align with content container
                'sm:left-0 sm:translate-x-0'
              )}
              aria-label="Previous answered item"
            >
              <Chevron
                direction="left"
                size={40}
                thickness={canGoPrev ? 6 : 4}
                color={canGoPrev ? 'black' : '#9CA3AF'}
                hoverColor={canGoPrev ? 'blue' : '#9CA3AF'}
                scale={0.6}
                hoverScale={0.8}
              />
            </button>

            <div
              className={clsx(
                contentMaxWCls,
                sidePadCls,
                'grid grid-cols-1 gap-3 justify-items-center sm:justify-items-stretch sm:grid-cols-2 lg:grid-cols-3'
              )}
            >
              {renderOptions()}
            </div>

            {/* RIGHT chevron */}
            <button
              onClick={goNext}
              disabled={!canGoNext}
              className={clsx(
                chevronBtnBase,
                'inline-flex absolute top-1/2 -translate-y-1/2 z-10',
                // Mobile: push closer to viewport edge, away from options
                'right-0 translate-x-4',
                // sm+: align with content container
                'sm:right-0 sm:translate-x-0'
              )}
              aria-label="Next answered item"
            >
              <Chevron
                direction="right"
                size={40}
                thickness={canGoNext ? 6 : 4}
                color={canGoNext ? 'black' : '#9CA3AF'}
                hoverColor={canGoNext ? 'blue' : '#9CA3AF'}
                scale={0.6}
                hoverScale={0.8}
              />
            </button>
          </div>

        </section>

        {/* footer — equal gap below answers, aligned to grid */}
        <footer className="px-5 sm:px-7 pb-6 mt-8 sm:mt-20 lg:mt-28 space-y-4 sm:space-y-0">
          {/* Mobile: submit + progress below */}
          <div
            className={clsx(
              contentMaxWCls,
              mobileSidePadCls,
              'flex flex-col items-center gap-8 sm:hidden'
            )}
          >
            <div className="w-full">
              <ProgressBarMobile
                current={Object.keys(answers).length}
                total={test.total_questions_number}
                idx={idx}
                maxIdx={liveIdx}
                onSeek={firstAnswered ? handleSeek : () => {}}
                disabled={!firstAnswered}
              />
            </div>

            <AnimatedSubmitButton
              onClick={(e) => {
                if (!allAnswered) {
                  e.preventDefault();
                  return;
                }
                handleSubmit();
              }}
              className={clsx(
                'tw-pad rounded-[10px] border border-[#43B384] text-sm font-bold',
                !allAnswered && 'is-disabled',
                allAnswered && 'enabled'
              )}
              labels={['Submit', 'Submitting']}
            />
          </div>


          {/* Desktop / tablet */}
          <div
            className={clsx(
              contentMaxWCls,
              sidePadCls,
              'hidden sm:flex justify-center'
            )}
          >
            <AnimatedSubmitButton
              onClick={(e) => {
                if (!allAnswered) {
                  e.preventDefault();
                  return;
                }
                handleSubmit();
              }}
              className={clsx(
                'tw-pad rounded-[10px] border border-[#43B384] text-sm font-bold',
                !allAnswered && 'is-disabled',
                allAnswered && 'enabled'
              )}
              labels={['Submit', 'Submitting']}
            />
          </div>
        </footer>

      </div>
    </div>
  );
}
