//psych-app/src/api/testing.js

import api from './axios';

// start a test
export const startTest = testId =>
  api.post('/testing/test/start/', { test: testId });

// get full test-result payload
export const fetchResult = resultId =>
  api.get('/testing/test/', { params: { test_result_id: resultId } });

// submit / update answer
export const submitAnswer = (resultId, qNum, answer) =>
  api.post(
    '/testing/test/answer/',
    { answer },
    { params: { test_result_id: resultId, question_number: qNum } }
  );

// mark test complete
export const markComplete = resultId =>
  api.post('/testing/test/complete/', null, {
    params: { test_result_id: resultId },
  });

// list results (optionally ?completed=true/false)
export const listResults = params =>
  api.get('/testing/test/list/', { params });


export const associateTest = resultId =>
  api.post('/testing/test/associate-user/', null, {
    params: { test_result_id: resultId },
  });
