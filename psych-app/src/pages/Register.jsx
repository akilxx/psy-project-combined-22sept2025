// psych-app/src/pages/Register.jsx
import { useState } from 'react';
import { register } from '../api/auth';
import { useNavigate } from 'react-router-dom';

export default function Register() {
  const [email, setEmail] = useState('');
  const [error, setErr] = useState(null);
  const nav = useNavigate();

  const submit = async e => {
    e.preventDefault();
    try {
      const { data } = await register(email);           // POST /register/
      nav(`/verify-register/${data.registration_id}`, { state: { email } });
    } catch (err) {
      setErr(
        err.response?.data?.email?.[0] ||
        err.response?.data?.detail     ||
        'Something went wrong'
      );
    }
  };

  return (
      <form
        onSubmit={submit}
        className="max-w-md mx-auto mt-10 p-8 bg-white rounded-2xl shadow"
      >
        <h1 className="text-2xl font-semibold mb-6">Create account</h1>

        <input
          type="email"
          placeholder="you@example.com"
          className="w-full p-3 border rounded-xl mb-4"
          value={email}
          onChange={e => setEmail(e.target.value)}
          required
        />

        {error && <p className="text-red-600 text-sm mb-2">{error}</p>}

        <button
          type="submit"
          className="w-full py-3 bg-indigo-600 text-white rounded-xl"
        >
          Send OTP
        </button>
      </form>
  );
}
