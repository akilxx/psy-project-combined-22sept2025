// psych-app/src/pages/AltTestRunner.jsx
import { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { fetchResult, submitAnswer, markComplete } from '../api/testing';

function StatPill({ label, value }) {
  return (
    <div className="flex flex-col items-center rounded-lg bg-slate-100 px-3 py-2">
      <span className="text-xs uppercase tracking-wide text-slate-500">{label}</span>
      <span className="text-lg font-semibold text-slate-900">{value}</span>
    </div>
  );
}

function QuestionChip({ number, isActive, isAnswered, disabled, onSelect }) {
  const base =
    'rounded-md border px-3 py-1 text-sm font-medium transition-colors md:px-2 md:py-1 md:text-xs';
  const activeStyles = 'border-indigo-600 bg-indigo-50 text-indigo-700';
  const answeredStyles = 'border-emerald-500 bg-emerald-50 text-emerald-700 hover:bg-emerald-100';
  const idleStyles = 'border-slate-300 bg-white text-slate-600 hover:bg-slate-100';
  const disabledStyles = 'border-slate-200 bg-slate-50 text-slate-300 cursor-not-allowed';

  let styles = idleStyles;
  if (isActive) styles = activeStyles;
  else if (isAnswered) styles = answeredStyles;
  if (disabled) styles = disabledStyles;

  return (
    <button
      type="button"
      onClick={onSelect}
      disabled={disabled}
      className={`${base} ${styles}`.trim()}
    >
      {number}
    </button>
  );
}

function PrimaryButton({ children, className = '', type = 'button', ...props }) {
  const base =
    'inline-flex items-center justify-center rounded-md px-4 py-2 font-semibold transition-colors';
  const enabled = 'bg-indigo-600 text-white hover:bg-indigo-700 focus:outline-none focus:ring';
  const disabled = 'bg-slate-200 text-slate-400 cursor-not-allowed';
  const computed = `${base} ${props.disabled ? disabled : enabled} ${className}`.trim();

  return (
    <button type={type} {...props} className={computed}>
      {children}
    </button>
  );
}

function SecondaryButton({ children, className = '', type = 'button', ...props }) {
  const base =
    'inline-flex items-center justify-center rounded-md border px-3 py-2 text-sm font-medium transition-colors';
  const enabled = 'border-slate-300 text-slate-700 hover:bg-slate-100';
  const disabled = 'border-slate-200 text-slate-300 cursor-not-allowed';
  const computed = `${base} ${props.disabled ? disabled : enabled} ${className}`.trim();

  return (
    <button type={type} {...props} className={computed}>
      {children}
    </button>
  );
}

export default function AltTestRunner() {
  const { resultId } = useParams();
  const navigate = useNavigate();

  const [test, setTest] = useState(null);
  const [answers, setAnswers] = useState({});
  const [activeIdx, setActiveIdx] = useState(0);
  const [inProgress, setInProgress] = useState(true);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [actionError, setActionError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    try {
      const { data } = await fetchResult(resultId);
      setTest(data.test);
      setAnswers(data.answers);
      setInProgress(Boolean(data.in_progress));

      const firstUnanswered = data.test.questions.findIndex(
        q => !data.answers[q.question_number],
      );
      setActiveIdx(firstUnanswered === -1 ? data.test.questions.length - 1 : firstUnanswered);
    } catch (err) {
      const detail = err.response?.data?.detail;
      setLoadError(detail || 'Unable to load the test.');
    } finally {
      setLoading(false);
    }
  }, [resultId]);

  useEffect(() => {
    load();
  }, [load]);

  const questionMeta = useMemo(() => {
    if (!test) return [];
    return test.questions.map((q, index) => ({
      index,
      number: q.question_number,
      answered: Boolean(answers[q.question_number]),
    }));
  }, [answers, test]);

  const answeredCount = questionMeta.filter(q => q.answered).length;
  const totalQuestions = test?.total_questions_number ?? 0;

  const firstUnansweredIndex = questionMeta.findIndex(q => !q.answered);
  const liveIndex = firstUnansweredIndex === -1 ? questionMeta.length - 1 : firstUnansweredIndex;

  const answeredIndices = questionMeta.filter(q => q.answered).map(q => q.index);
  const allowedIndices = firstUnansweredIndex === -1
    ? answeredIndices
    : [...answeredIndices, liveIndex];

  const canGoPrev = answeredIndices.some(i => i < activeIdx);
  const canGoNext = allowedIndices.some(i => i > activeIdx);

  const goPrev = () => {
    if (!canGoPrev) return;
    const nextIdx = [...answeredIndices].filter(i => i < activeIdx).pop();
    if (typeof nextIdx === 'number') setActiveIdx(nextIdx);
  };

  const goNext = () => {
    if (!canGoNext) return;
    const nextIdx = [...allowedIndices].filter(i => i > activeIdx).sort((a, b) => a - b)[0];
    if (typeof nextIdx === 'number') setActiveIdx(nextIdx);
  };

  const currentQuestion = test?.questions[activeIdx];

  const handleAnswer = async (questionNumber, option) => {
    if (!test) return;
    setActionError(null);

    setAnswers(prev => {
      const next = { ...prev, [questionNumber]: { answer: option } };

      const nextFirstUnanswered = test.questions.findIndex(q => !next[q.question_number]);
      setActiveIdx(
        nextFirstUnanswered === -1 ? test.questions.length - 1 : nextFirstUnanswered,
      );

      return next;
    });

    try {
      const { data } = await submitAnswer(resultId, questionNumber, option);
      setAnswers(prev => ({ ...prev, ...data.answers }));
    } catch (_) {
      setActionError('We could not save that answer. Please tap it again.');
    }
  };

  const allAnswered = totalQuestions > 0 && answeredCount === totalQuestions;

  const handleSubmit = async () => {
    if (!allAnswered || submitting) return;
    setSubmitting(true);
    setActionError(null);
    try {
      await markComplete(resultId);
    } catch (_) {
      // ignore completion errors, keep navigation consistent
    } finally {
      setSubmitting(false);
    }
    navigate(`/results/${resultId}`);
  };

  if (loading) {
    return (
      <div className="mx-auto mt-20 max-w-3xl rounded-2xl bg-white p-10 text-center">
        <p className="text-lg font-medium text-slate-600">Loading test…</p>
      </div>
    );
  }

  if (loadError) {
    return (
      <div className="mx-auto mt-20 max-w-lg rounded-2xl bg-red-50 p-8 text-center">
        <p className="text-red-700">{loadError}</p>
        <PrimaryButton className="mt-6" onClick={load}>
          Retry
        </PrimaryButton>
      </div>
    );
  }

  if (!test) return null;

  if (!inProgress) {
    return (
      <div className="mx-auto mt-20 max-w-2xl space-y-4 rounded-2xl bg-white p-10 text-center">
        <h1 className="text-2xl font-semibold text-slate-900">Test completed</h1>
        <p className="text-slate-600">
          This test has already been submitted. You can review the outcomes in your dashboard.
        </p>
      </div>
    );
  }

  return (
    <div className="mx-auto flex h-screen w-full max-w-5xl flex-col gap-4 overflow-hidden bg-white px-6 py-6">
      <header className="flex flex-col gap-3">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <h1 className="text-2xl font-semibold text-slate-900">{test.test_name}</h1>
          <div className="flex gap-2">
            <StatPill label="Answered" value={`${answeredCount}/${totalQuestions}`} />
            <StatPill label="Current" value={`#${currentQuestion?.question_number ?? '-'}`} />
          </div>
        </div>
        <div>
          <div className="flex items-center justify-between text-xs font-medium uppercase tracking-wide text-slate-500">
            <span>Progress</span>
            <span>{totalQuestions === 0 ? '0%' : `${Math.round((answeredCount / totalQuestions) * 100)}%`}</span>
          </div>
          <progress
            value={answeredCount}
            max={totalQuestions}
            className="mt-1 h-3 w-full overflow-hidden rounded-full bg-slate-100"
          >
            {answeredCount}
          </progress>
        </div>
      </header>

      <section className="flex flex-col gap-2">
        <h2 className="text-sm font-semibold uppercase tracking-wide text-slate-500">
          Navigate items
        </h2>
        <div className="grid grid-cols-5 gap-2 sm:grid-cols-8">
          {questionMeta.map(meta => {
            const disabled =
              meta.index !== activeIdx && !allowedIndices.includes(meta.index);
            return (
              <QuestionChip
                key={meta.number}
                number={meta.number}
                isActive={meta.index === activeIdx}
                isAnswered={meta.answered}
                disabled={disabled}
                onSelect={() => setActiveIdx(meta.index)}
              />
            );
          })}
        </div>
      </section>

      {currentQuestion && (
        <section className="flex flex-1 flex-col gap-4 overflow-y-auto">
          <div className="space-y-1.5">
            <p className="text-sm font-medium uppercase tracking-wide text-slate-500">
              Item {currentQuestion.question_number}
            </p>
            <h2 className="text-2xl font-semibold leading-snug text-slate-900">
              {currentQuestion.text}
            </h2>
          </div>

          {actionError && (
            <p className="rounded-md border border-amber-300 bg-amber-50 px-4 py-2 text-sm text-amber-800">
              {actionError}
            </p>
          )}

          <div className="grid flex-1 grid-cols-1 gap-2 md:grid-cols-2">
            {test.options.map(option => {
              const selected = answers[currentQuestion.question_number]?.answer === option;
              const base = 'rounded-xl border px-4 py-3 text-left font-medium transition';
              const styles = selected
                ? 'border-indigo-600 bg-indigo-600 text-white'
                : 'border-slate-200 bg-slate-50 text-slate-700 hover:bg-white';
              return (
                <button
                  type="button"
                  key={option}
                  onClick={() => handleAnswer(currentQuestion.question_number, option)}
                  className={`${base} ${styles}`.trim()}
                >
                  {option}
                </button>
              );
            })}
          </div>
        </section>
      )}

      <footer className="flex flex-wrap items-center justify-between gap-3 border-t border-slate-200 pt-4">
        <div className="flex gap-2">
          <SecondaryButton onClick={goPrev} disabled={!canGoPrev}>
            Previous answered
          </SecondaryButton>
          <SecondaryButton onClick={goNext} disabled={!canGoNext}>
            Next pending
          </SecondaryButton>
        </div>
        <PrimaryButton onClick={handleSubmit} disabled={!allAnswered || submitting}>
          {submitting ? 'Submitting…' : 'Submit test'}
        </PrimaryButton>
      </footer>
    </div>
  );
}
