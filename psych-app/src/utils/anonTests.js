//psych-app/src/utils/anonTests.js

/*  Keep a small list of anonymous TestResult UUIDs in localStorage.
    We never store more than 20 for safety.
-----------------------------------------------------------------*/
const KEY = 'anon_test_ids';

export function getAnonTests() {
  try {
    return JSON.parse(localStorage.getItem(KEY)) ?? [];
  } catch {
    return [];
  }
}

export function addAnonTest(id) {
  const list = getAnonTests();
  if (list.includes(id)) return;
  list.unshift(id);
  localStorage.setItem(KEY, JSON.stringify(list.slice(0, 20)));
}

export function clearAnonTests() {
  localStorage.removeItem(KEY);
}
