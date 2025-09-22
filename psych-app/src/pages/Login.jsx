// psych-app/src/pages/Login.jsx
import { useState } from "react";
import { requestOtp, register as registerApi } from "../api/auth";
import { useNavigate } from "react-router-dom";

export default function Login() {
  /* ---------------- state ---------------- */
  const [tab, setTab] = useState("login");
  const [loginEmail, setLogin] = useState("");
  const [regEmail, setReg] = useState("");
  const [loginErr, setLErr] = useState(null);
  const [regErr, setRErr] = useState(null);

  const nav = useNavigate();

  /* ---------------- handlers ---------------- */
  const handleLogin = async (e) => {
    e.preventDefault();
    try {
      await requestOtp(loginEmail);
      nav("/verify-login", { state: { email: loginEmail } });
    } catch (err) {
      const apiErr =
        err?.response?.data?.detail ||
        err?.response?.data?.non_field_errors?.[0] ||
        err?.response?.data?.email?.[0] ||
        "Something went wrong";
      setLErr(apiErr);
    }
  };

  const handleRegister = async (e) => {
    e.preventDefault();
    try {
      const { data } = await registerApi(regEmail);
      nav(`/verify-register/${data.registration_id}`, { state: { email: regEmail } });
    } catch (err) {
      const apiErr =
        err?.response?.data?.email?.[0] ||
        err?.response?.data?.detail ||
        "Something went wrong";
      setRErr(apiErr);
    }
  };

  /* ---------------- UI ---------------- */
  return (
    <div className="max-w-md mx-auto mt-10 p-8 bg-white rounded-2xl shadow">
      {/* segment toggle */}
      <div className="grid grid-cols-2 gap-1 bg-gray-100 rounded-lg p-1 mb-6">
        <button
          type="button"
          onClick={() => setTab("login")}
          className={`py-2 rounded-md font-semibold transition ${
            tab === "login"
              ? "bg-indigo-600 text-white"
              : "text-gray-600 hover:bg-white"
          }`}
        >
          Login
        </button>
        <button
          type="button"
          onClick={() => setTab("register")}
          className={`py-2 rounded-md font-semibold transition ${
            tab === "register"
              ? "bg-indigo-600 text-white"
              : "text-gray-600 hover:bg-white"
          }`}
        >
          Register
        </button>
      </div>

      {tab === "login" ? (
        <form onSubmit={handleLogin} className="space-y-4">
          <h1 className="text-2xl font-semibold mb-2">Sign in with OTP</h1>

          <input
            type="email"
            required
            placeholder="you@example.com"
            className="w-full p-3 border rounded-xl text-black"
            value={loginEmail}
            onChange={(e) => {
              setLogin(e.target.value);
              if (loginErr) setLErr(null);
            }}
          />

          {loginErr && <p className="text-red-600 text-sm">{loginErr}</p>}

          <button
            type="submit"
            className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl"
          >
            Send OTP
          </button>
        </form>
      ) : (
        <form onSubmit={handleRegister} className="space-y-4">
          <h1 className="text-2xl font-semibold mb-2">Create account</h1>

          <input
            type="email"
            required
            placeholder="you@example.com"
            className="w-full p-3 border rounded-xl text-black"
            value={regEmail}
            onChange={(e) => {
              setReg(e.target.value);
              if (regErr) setRErr(null);
            }}
          />

          {regErr && <p className="text-red-600 text-sm">{regErr}</p>}

          <button
            type="submit"
            className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-xl"
          >
            Send OTP
          </button>
        </form>
      )}
    </div>
  );
}
