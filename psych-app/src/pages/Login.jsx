// psych-app/src/pages/Login.jsx

import { useEffect, useState } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { startOtpFlow, verifyOtp } from "../api/auth";
import useAuth from "../hooks/useAuth";

const inferFlow = (status) =>
  status && status.startsWith("registration") ? "register" : "login";

export default function AuthPage() {
  const location = useLocation();
  const [email, setEmail] = useState(location.state?.email ?? "");
  const [step, setStep] = useState("email");
  const [flow, setFlow] = useState(null); // "register" | "login"

  const [otp, setOtp] = useState("");
  const [countdown, setCountdown] = useState(0);

  const [sending, setSending] = useState(false);
  const [verifying, setVerifying] = useState(false);

  const [emailError, setEmailError] = useState(null);
  const [otpError, setOtpError] = useState(null);

  const navigate = useNavigate();
  const { loginWithTokens } = useAuth();

  useEffect(() => {
    if (countdown <= 0) return undefined;
    const timer = setInterval(() => {
      setCountdown((prev) => (prev > 0 ? prev - 1 : 0));
    }, 1000);
    return () => clearInterval(timer);
  }, [countdown]);

  const resetFlow = () => {
    setStep("email");
    setFlow(null);
    setOtp("");
    setCountdown(0);
    setOtpError(null);
  };

  const handleStart = async (event) => {
    event.preventDefault();
    if (sending) return;

    setSending(true);
    setEmailError(null);
    setOtpError(null);

    try {
      const { data } = await startOtpFlow(email);
      setFlow(inferFlow(data.status));
      setStep("otp");
      setOtp("");
      setCountdown(data.resend_available_in ?? 30);
    } catch (err) {
      const response = err?.response?.data || {};
      const wait = response.retry_after;
      if (typeof wait === "number") {
        setCountdown(wait);
      }
      setEmailError(
        response.detail || response.email?.[0] || "Something went wrong."
      );
    } finally {
      setSending(false);
    }
  };

  const handleResend = async () => {
    if (sending || countdown > 0) return;
    setSending(true);
    setOtpError(null);

    try {
      const { data } = await startOtpFlow(email);
      setFlow(inferFlow(data.status));
      setCountdown(data.resend_available_in ?? 30);
    } catch (err) {
      const response = err?.response?.data || {};
      const wait = response.retry_after;
      if (typeof wait === "number") {
        setCountdown(wait);
      }
      setOtpError(
        response.detail || response.email?.[0] || "Unable to resend the code."
      );
    } finally {
      setSending(false);
    }
  };

  const handleVerify = async (event) => {
    event.preventDefault();
    if (verifying) return;
    setVerifying(true);
    setOtpError(null);

    try {
      const { data } = await verifyOtp({ email, otp_code: otp });
      await loginWithTokens(data);
      navigate("/dashboard");
    } catch (err) {
      const response = err?.response?.data || {};
      setOtpError(
        response.otp_code?.[0] || response.detail || "Invalid verification code."
      );
    } finally {
      setVerifying(false);
    }
  };

  const heading =
    step === "email"
      ? "Sign in or create an account"
      : flow === "register"
      ? "Finish creating your account"
      : "Enter the code to sign in";

  const helperText =
    step === "email"
      ? "We will email you a 4-digit code."
      : `We've sent a 4-digit code to ${email}.`;

  return (
    <div className="max-w-md mx-auto mt-10 p-8 bg-white rounded-2xl shadow">
      <h1 className="text-2xl font-semibold mb-3 text-slate-900">{heading}</h1>
      <p className="text-sm text-slate-600 mb-6">{helperText}</p>

      {step === "email" ? (
        <form onSubmit={handleStart} className="space-y-4">
          <input
            type="email"
            required
            placeholder="you@example.com"
            className="w-full p-3 border rounded-xl text-black"
            value={email}
            onChange={(event) => {
              setEmail(event.target.value);
              if (emailError) setEmailError(null);
            }}
          />

          {emailError && (
            <p className="text-red-600 text-sm" role="alert">
              {emailError}
            </p>
          )}

          <button
            type="submit"
            className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl disabled:opacity-60"
            disabled={sending}
          >
            {sending ? "Sending…" : "Send code"}
          </button>
        </form>
      ) : (
        <form onSubmit={handleVerify} className="space-y-4">
          <input
            type="text"
            inputMode="numeric"
            maxLength={4}
            pattern="\\d{4}"
            className="w-full p-3 border rounded-xl tracking-widest text-center text-black"
            value={otp}
            onChange={(event) => setOtp(event.target.value.replace(/[^0-9]/g, ""))}
            required
          />

          {otpError && (
            <p className="text-red-600 text-sm" role="alert">
              {otpError}
            </p>
          )}

          <button
            type="submit"
            className="w-full py-3 bg-indigo-600 text-white rounded-xl disabled:opacity-60"
            disabled={verifying || otp.length !== 4}
          >
            {verifying ? "Verifying…" : flow === "register" ? "Create account" : "Sign in"}
          </button>

          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 text-sm">
            <button
              type="button"
              onClick={handleResend}
              disabled={sending || countdown > 0}
              className="text-indigo-600 disabled:text-slate-400"
            >
              {countdown > 0
                ? `Resend code in ${countdown}s`
                : sending
                ? "Sending…"
                : "Resend code"}
            </button>
            <button
              type="button"
              onClick={resetFlow}
              className="text-slate-500 hover:text-slate-700"
            >
              Use a different email
            </button>
          </div>
        </form>
      )}
    </div>
  );
}
