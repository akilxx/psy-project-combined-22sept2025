//  psych-app/src/context/tokenStorage.js

export const getAccess  = () => localStorage.getItem('access');
export const getRefresh = () => localStorage.getItem('refresh');
export const setAccess  = t => localStorage.setItem('access', t);
export const saveTokens = ({ access, refresh }) => {
  localStorage.setItem('access', access);
  localStorage.setItem('refresh', refresh);
};
export const clearTokens = () => { localStorage.clear(); };
