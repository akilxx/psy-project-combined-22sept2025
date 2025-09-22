// psych-app/src/components/QuestionCard.jsx

import clsx from 'clsx';

export default function QuestionCard({ q, options, answer, onAnswer }) {
  return (
    <div className="my-6 p-6 bg-white rounded-2xl shadow">
      <h2 className="text-lg font-medium mb-4">
        Q{q['question number']}. {q.text}
      </h2>
      <div className="grid grid-cols-2 gap-3">
        {options.map(opt => (
          <button
            key={opt}
            onClick={() => onAnswer(opt)}
            className={clsx(
              'py-2 px-4 rounded-xl border',
              answer === opt
                ? 'bg-indigo-600 text-white'
                : 'bg-slate-100 hover:bg-indigo-50'
            )}
          >
            {opt}
          </button>
        ))}
      </div>
    </div>
  );
}
