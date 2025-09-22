// psych-app/src/pages/VerifyRegister.jsx
import { useParams, useLocation, useNavigate } from 'react-router-dom';
import { useState } from 'react';
import { verifyRegister } from '../api/auth';
import useAuth from '../hooks/useAuth';
import ModifiedCard from '../components/ModifiedCard';


export default function VerifyRegister() {
  const { registrationId } = useParams();
  const { state }       = useLocation();          // { email }
  const { loginWithTokens } = useAuth();
  const nav = useNavigate();

  const [otp,     setOtp]     = useState('');
  const [error,   setErr]     = useState(null);
  const [working, setWorking] = useState(false);

  const submit = async e => {
    e.preventDefault();
    if (working) return;                          // guard double-click
    setWorking(true);

    try {
      // 1. Verify registration OTP
      const { data } = await verifyRegister({
        registration_id: registrationId,
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
    <div className="">
      <ModifiedCard className="flex w-full justify-center max-w-md px-12 mt-[64px] pt-10 pb-4">
        <form
          onSubmit={submit}

        >
          <h1 className="text-2xl font-bold mb-6 text-white">
            Enter the 6-digit code for:
            <span className="block text-sm font-bold text-gray-300">
              {state?.email}
            </span>
          </h1>

          <input
            type="text"
            maxLength={6}
            pattern="\d{6}"
            className="w-full p-3 border text-[#07071F] rounded-xl mb-4 tracking-widest text-center"
            value={otp}
            onChange={e => setOtp(e.target.value)}
            required
          />

          {error && <p className="text-red-600 text-sm mb-2">{error}</p>}

          <button
            type="submit"
            className="w-full py-3 bg-[#07071F] text-white rounded-xl disabled:opacity-50"
            disabled={working}
          >
            {working ? 'Creating account…' : 'Verify & Sign In'}
          </button>
        </form>
      </ModifiedCard>
    </div>
  );
}
