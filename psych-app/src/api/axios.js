//psych-app/src/api/axios.js

import axios from 'axios';
import { jwtDecode } from 'jwt-decode';
import {
  getAccess,
  getRefresh,
  setAccess,
  clearTokens,
} from '../context/tokenStorage';

const baseURL = import.meta.env.VITE_API_URL;

const api = axios.create({
  baseURL,
  withCredentials: true,
});

// ---------- helpers ----------
const raw = axios.create({ baseURL, withCredentials: true }); // no interceptors

let refreshPromise = null; // tracks an ongoing refresh for de-duplication

async function getValidAccessToken() {
  const current = getAccess();
  if (!current) return null;

  const { exp } = jwtDecode(current);
  if (Date.now() < exp * 1000) return current; // still valid

  // Already refreshing? — await the same promise.
  if (refreshPromise) return refreshPromise;

  // Start a refresh.
  refreshPromise = raw
    .post('/token/refresh/', { refresh: getRefresh() })
    .then(({ data }) => {
      setAccess(data.access);
      refreshPromise = null;
      return data.access;
    })
    .catch(err => {
      refreshPromise = null;
      clearTokens();
      // Hard redirect avoids React-router stash issues
      window.location.href = '/login';
      return Promise.reject(err);
    });

  return refreshPromise;
}

// ---------- request interceptor ----------
api.interceptors.request.use(async config => {
  const token = await getValidAccessToken();     // may trigger refresh
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

// ---------- response interceptor ----------
api.interceptors.response.use(
  res => res,
  async error => {
    const { config, response } = error;
    // If we got a 401 and haven't retried yet, try refreshing once more
    if (response?.status === 401 && !config._retry) {
      config._retry = true;
      try {
        const newToken = await getValidAccessToken(); // refresh if possible
        if (newToken) {
          config.headers.Authorization = `Bearer ${newToken}`;
          return api(config);                          // replay the request
        }
      } catch (_) { /* fall-through to logout */ }
    }

    // Any other case → propagate error
    return Promise.reject(error);
  }
);

export default api;
