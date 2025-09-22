// psych-app/src/pages/VerifyLogin.jsx
import { useLocation, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { verifyOtp } from '../api/auth';
import useAuth from '../hooks/useAuth';

export default function VerifyLogin() {
  const { state }       = useLocation();          // { email }
  const { loginWithTokens } = useAuth();
  const nav = useNavigate();

  const [otp,     setOtp]   = useState('');
  const [error,   setErr]   = useState(null);
  const [working, setWorking] = useState(false);

  const submit = async e => {
    e.preventDefault();
    if (working) return;                          // guard double-click
    setWorking(true);

    try {
      // 1. Verify OTP and get { access, refresh }
      const { data } = await verifyOtp({
        email: state?.email,
        otp_code: otp,
      });

      // 2. Store tokens & claim any anonymous tests
      await loginWithTokens(data);

      // 3. Go to dashboard
      nav('/dashboard');
    } catch (err) {
      setErr(
        err.response?.data?.otp_code?.[0] ||
        err.response?.data?.detail        ||
        'Invalid code'
      );
    } finally {
      setWorking(false);
    }
  };

  return (
      <form
        onSubmit={submit}
        className="max-w-md mx-auto mt-10 p-8 bg-white rounded-2xl shadow"
      >
        <h1 className="text-2xl font-semibold mb-6">
          Enter the 6-digit code for {state?.email}
        </h1>

        <input
          type="text"
          maxLength={6}
          pattern="\d{6}"
          className="w-full p-3 border rounded-xl mb-4 tracking-widest text-center"
          value={otp}
          onChange={e => setOtp(e.target.value)}
          required
        />

        {error && <p className="text-red-600 text-sm mb-2">{error}</p>}

        <button
          type="submit"
          className="w-full py-3 bg-indigo-600 text-white rounded-xl disabled:opacity-50"
          disabled={working}
        >
          {working ? 'Signing in…' : 'Verify →'}
        </button>
      </form>
  );
}

