//psych-app/src/pages/PaymentElementPage.jsx

/* 
    – Creates exactly ONE PaymentIntent, waits for client_secret,
      THEN mounts <Elements> so Stripe has what it needs.
-----------------------------------------------------------------*/
import { useEffect, useState, useRef } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import {
  Elements,
  PaymentElement,
  useStripe,
  useElements,
} from '@stripe/react-stripe-js';
import api from '../api/axios';            // shared axios w/ JWT
import { useParams, useNavigate } from 'react-router-dom';

const stripePromise = loadStripe(
  import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY
);

/* ---------------- inner checkout form ---------------- */
function CheckoutForm({ clientSecret }) {
  const stripe   = useStripe();
  const elements = useElements();
  const nav      = useNavigate();
  const [busy, setBusy]     = useState(false);
  const [msg,  setMsg]      = useState(null);

  const handlePay = async () => {
    if (!stripe || !elements || busy) return;
    setBusy(true);
    setMsg(null);

    /* 1️⃣  gather the Payment Element input */
    const { error: submitErr } = await elements.submit();
    if (submitErr) {
      setMsg(submitErr.message);
      setBusy(false);
      return;
    }
    /* 2️⃣  now confirm */
    const { error } = await stripe.confirmPayment({
      elements,
      clientSecret,
      confirmParams: {
        return_url: window.location.origin + '/dashboard',
      },
    });

    if (error) setMsg(error.message);
    setBusy(false);
  };

  return (
    <div className="max-w-md mx-auto p-8 bg-white rounded-xl shadow mt-10">
      <h1 className="text-2xl font-semibold mb-6">Checkout</h1>

      <PaymentElement className="mb-6" />

      {msg && <p className="text-red-600 mb-4">{msg}</p>}

      <button
        onClick={handlePay}
        disabled={busy || !stripe}
        className="w-full py-3 bg-indigo-600 hover:bg-indigo-500 text-white rounded-lg disabled:opacity-50"
      >
        {busy ? 'Processing…' : 'Pay $20'}
      </button>
    </div>
  );
}

/* ---------------- outer page that fetches client secret ---------------- */
export default function PaymentElementPage() {
  const { resultId } = useParams();
  const [clientSecret, setSecret] = useState(null);
  const [error,       setError]  = useState(null);
  const fetchedRef = useRef(false);          // ← guard duplicate calls

  useEffect(() => {
    if (fetchedRef.current) return;          // already ran once
    fetchedRef.current = true;

    (async () => {
      try {
        /* 1️⃣ lookup numeric test id */
        const { data: tr } = await api.get('/testing/test/', {
          params: { test_result_id: resultId },
        });

        /* 2️⃣ create PaymentIntent (no confirm) */
        const { data } = await api.post('/payment/payments/create/', {
          test:        tr.test.id,
          test_result: resultId,
          amount:      20.0,
          currency:    'usd',
        });

        setSecret(data.client_secret);
      } catch (e) {
        setError(e.response?.data?.error || 'Unable to start payment');
      }
    })();
  }, [resultId]);

  if (error) return <p className="mt-20 text-center text-red-600">{error}</p>;
  if (!clientSecret) return <p className="mt-20 text-center">Loading…</p>;

  /*  Only now do we mount <Elements>, passing the secret  */
  return (
    <Elements stripe={stripePromise} options={{ clientSecret }}>
      <CheckoutForm clientSecret={clientSecret} />
    </Elements>
  );
}
