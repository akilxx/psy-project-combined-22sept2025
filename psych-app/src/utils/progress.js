
// psych-app/src/utils/progress.js

/**
 * Parse a server progress string (e.g. "3/10" or "3 / 10") into numeric counts.
 * Returns null when parsing fails.
 */
export function parseProgressString(progress) {
  if (typeof progress !== 'string') return null;
  const parts = progress.split('/');
  if (parts.length !== 2) return null;

  const answered = Number.parseInt(parts[0].trim(), 10);
  const total = Number.parseInt(parts[1].trim(), 10);

  if (Number.isNaN(answered) || Number.isNaN(total)) return null;

  return {
    answered_count: answered,
    total_questions_number: total,
  };
}
