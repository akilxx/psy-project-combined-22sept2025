//  psych-app/src/context/AuthContext.jsx 

import { createContext, useState } from 'react';
import { jwtDecode } from 'jwt-decode';

import { getAccess, saveTokens, clearTokens } from './tokenStorage';
import { getAnonTests, clearAnonTests } from '../utils/anonTests';
import { associateTest } from '../api/testing';

export const AuthContext = createContext(null);

export default function AuthProvider({ children }) {
  /* ---------- initial user (if JWT already present) ---------- */
  const [user, setUser] = useState(() => {
    const token = getAccess();
    return token ? jwtDecode(token) : null;
  });

  /* ---------- login / register flow ---------- */
  const loginWithTokens = async tokens => {
    // 1. persist access & refresh in localStorage
    saveTokens(tokens);

    // 2. decode user info & update state
    const decoded = jwtDecode(tokens.access);
    setUser(decoded);

    // 3. claim any tests started while the visitor was anonymous
    const pending = getAnonTests();           // [uuid, uuid, …]
    if (pending.length) {
      await Promise.allSettled(pending.map(associateTest));
      clearAnonTests();
    }
  };

  /* ---------- logout ---------- */
  const logout = () => {
    clearTokens();
    setUser(null);
  };

  /* ---------- context value ---------- */
  return (
    <AuthContext.Provider value={{ user, loginWithTokens, logout }}>
      {children}
    </AuthContext.Provider>
  );
}
