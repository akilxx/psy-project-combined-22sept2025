// psych-app/src/api/subscriptions.js

import api from './axios';

export const fetchPlans = () => api.get('/payment/subscriptions/plans/');

export const createSubscription = payload =>
  api.post('/payment/subscriptions/', payload);

export const fetchCurrentSubscription = () =>
  api.get('/payment/subscriptions/me/');
