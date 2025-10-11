// psych-app/src/pages/Subscription.jsx
import { useCallback, useEffect, useMemo, useState } from 'react';
import { loadStripe } from '@stripe/stripe-js';
import {
  Elements,
  CardElement,
  useElements,
  useStripe,
} from '@stripe/react-stripe-js';
import clsx from 'clsx';
import {
  fetchPlans,
  createSubscription,
  fetchCurrentSubscription,
  cancelSubscription,
} from '../api/subscriptions';

const stripePromise = loadStripe(
  import.meta.env.VITE_STRIPE_PUBLISHABLE_KEY
);

const cardElementOptions = {
  style: {
    base: {
      fontSize: '16px',
      color: '#111827',
      '::placeholder': {
        color: '#9CA3AF',
      },
    },
    invalid: {
      color: '#DC2626',
    },
  },
  hidePostalCode: true,
};

function formatCurrency(amount, currency) {
  if (amount == null) return '';
  const value = Number(amount);
  if (Number.isNaN(value)) return `${amount}`;

  const isoCurrency = (currency || 'USD').toUpperCase();
  try {
    return new Intl.NumberFormat(undefined, {
      style: 'currency',
      currency: isoCurrency,
    }).format(value);
  } catch {
    return `${isoCurrency} ${value.toFixed(2)}`;
  }
}

function formatAllowance(plan) {
  if (plan.unlimited_tests) return 'Unlimited tests';
  if (plan.monthly_allowance)
    return `${plan.monthly_allowance} tests / month`;
  return 'Includes test access';
}

function formatInterval(interval) {
  if (!interval) return 'monthly';
  return interval.charAt(0).toUpperCase() + interval.slice(1);
}

function formatDate(value) {
  if (!value) return '—';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '—';
  return date.toLocaleDateString(undefined, {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
  });
}

function CurrentSubscription({ subscription, onCancel, cancelling }) {
  if (!subscription) {
    return (
      <div className="rounded-2xl border border-dashed border-slate-300 p-6 bg-slate-50">
        <h2 className="text-lg font-semibold mb-2">No active subscription</h2>
        <p className="text-slate-600">
          Choose a plan below to unlock premium assessments and monthly
          allowances.
        </p>
      </div>
    );
  }

  const { plan } = subscription;
  const canScheduleCancellation =
    subscription.status !== 'canceled' && !subscription.cancel_at_period_end;
  const canCancelImmediately = subscription.status !== 'canceled';

  return (
    <div className="rounded-2xl border border-indigo-200 bg-white p-6 shadow-sm">
      <div className="flex flex-col md:flex-row md:items-start md:justify-between gap-4">
        <div>
          <p className="uppercase text-xs tracking-wide text-indigo-500 font-semibold">
            Current plan
          </p>
          <h2 className="text-2xl font-semibold text-slate-900">
            {plan?.name || 'Subscription'}
          </h2>
          {plan?.description && (
            <p className="mt-2 text-slate-600 max-w-xl">{plan.description}</p>
          )}
        </div>
        <div className="text-right">
          <p className="text-lg font-semibold text-slate-900">
            {formatCurrency(plan?.price, plan?.currency)}
            <span className="text-sm font-normal text-slate-500 ml-1">
              / {formatInterval(plan?.billing_interval)}
            </span>
          </p>
          <p className="text-sm text-slate-600">{formatAllowance(plan || {})}</p>
        </div>
      </div>

      <dl className="mt-6 grid gap-4 sm:grid-cols-3">
        <div>
          <dt className="text-xs uppercase tracking-wide text-slate-500">
            Status
          </dt>
          <dd className="text-sm font-medium text-slate-900">
            {subscription.status || '—'}
            {subscription.cancel_at_period_end && (
              <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-700">
                Cancels at period end
              </span>
            )}
          </dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-slate-500">
            Current period
          </dt>
          <dd className="text-sm text-slate-900">
            {formatDate(subscription.current_period_start)}
            <span className="mx-1 text-slate-400">→</span>
            {formatDate(subscription.current_period_end)}
          </dd>
        </div>
        <div>
          <dt className="text-xs uppercase tracking-wide text-slate-500">
            Remaining allowance
          </dt>
          <dd className="text-sm text-slate-900">
            {subscription.is_unlimited
              ? 'Unlimited'
              : subscription.remaining_tests ?? '—'}
          </dd>
        </div>
      </dl>

      <div className="mt-6 flex flex-col gap-3 sm:flex-row sm:items-center">
        {canScheduleCancellation && (
          <button
            type="button"
            onClick={() => onCancel?.({ cancelAtPeriodEnd: true })}
            disabled={cancelling}
            className="inline-flex items-center justify-center rounded-xl border border-indigo-200 px-4 py-2 text-sm font-semibold text-indigo-700 transition hover:border-indigo-300 hover:text-indigo-800 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-400"
          >
            {cancelling ? 'Scheduling cancellation…' : 'Cancel at period end'}
          </button>
        )}

        {canCancelImmediately && (
          <button
            type="button"
            onClick={() => {
              if (
                window.confirm(
                  'Are you sure you want to cancel immediately? You will lose access right away.'
                )
              ) {
                onCancel?.({ cancelAtPeriodEnd: false });
              }
            }}
            disabled={cancelling}
            className="inline-flex items-center justify-center rounded-xl border border-red-200 px-4 py-2 text-sm font-semibold text-red-700 transition hover:border-red-300 hover:text-red-800 disabled:cursor-not-allowed disabled:border-slate-200 disabled:text-slate-400"
          >
            {cancelling ? 'Cancelling…' : 'Cancel immediately'}
          </button>
        )}

        {!canScheduleCancellation && !canCancelImmediately && (
          <span className="text-sm text-slate-500">
            This subscription is no longer active.
          </span>
        )}
      </div>
    </div>
  );
}

function SubscriptionForm({
  plans,
  disabled,
  onSubscribed,
}) {
  const stripe = useStripe();
  const elements = useElements();
  const [selectedPlan, setSelectedPlan] = useState(plans[0]?.id ?? '');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  useEffect(() => {
    if (!plans.length) {
      setSelectedPlan('');
      return;
    }
    if (!plans.some(plan => plan.id === selectedPlan)) {
      setSelectedPlan(plans[0].id);
    }
  }, [plans, selectedPlan]);

  const handleSubmit = async event => {
    event.preventDefault();
    setError(null);
    setSuccess(null);

    if (disabled) return;

    if (!selectedPlan) {
      setError('Please select a plan.');
      return;
    }

    if (!stripe || !elements) {
      setError('Payment service is not ready yet.');
      return;
    }

    const cardElement = elements.getElement(CardElement);
    if (!cardElement) {
      setError('Card input is not available.');
      return;
    }

    setSubmitting(true);
    try {
      const { error: pmError, paymentMethod } = await stripe.createPaymentMethod({
        type: 'card',
        card: cardElement,
      });

      if (pmError) {
        throw new Error(pmError.message || 'Unable to create payment method.');
      }

      const { data } = await createSubscription({
        plan_id: selectedPlan,
        payment_method_id: paymentMethod.id,
      });

      cardElement.clear();
      setSuccess('Subscription activated successfully.');
      onSubscribed?.(data);
    } catch (err) {
      const apiMessage =
        err.response?.data?.error ||
        err.response?.data?.detail ||
        err.message ||
        'Unable to start the subscription.';
      setError(apiMessage);
    } finally {
      setSubmitting(false);
    }
  };

  if (!plans.length) {
    return (
      <p className="text-sm text-slate-600">
        There are no subscription plans available yet.
      </p>
    );
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6">
      <div className="grid gap-4 lg:grid-cols-3">
        {plans.map(plan => {
          const isSelected = plan.id === selectedPlan;
          return (
            <button
              key={plan.id}
              type="button"
              onClick={() => setSelectedPlan(plan.id)}
              className={clsx(
                'w-full rounded-2xl border p-6 text-left transition focus:outline-none focus:ring-2 focus:ring-indigo-500',
                isSelected
                  ? 'border-indigo-500 shadow-lg ring-2 ring-indigo-200'
                  : 'border-slate-200 hover:border-indigo-200 hover:shadow'
              )}
              disabled={disabled}
            >
              <div className="flex items-start justify-between gap-3">
                <div>
                  <span className="inline-flex items-center rounded-full bg-indigo-100 px-3 py-1 text-xs font-semibold text-indigo-700">
                    {formatInterval(plan.billing_interval)}
                  </span>
                  <h3 className="mt-3 text-xl font-semibold text-slate-900">
                    {plan.name}
                  </h3>
                  {plan.description && (
                    <p className="mt-2 text-sm text-slate-600">
                      {plan.description}
                    </p>
                  )}
                </div>
                <input
                  type="radio"
                  name="subscriptionPlan"
                  value={plan.id}
                  checked={isSelected}
                  onChange={() => setSelectedPlan(plan.id)}
                  className="mt-1 h-4 w-4 text-indigo-600 focus:ring-indigo-500"
                />
              </div>

              <p className="mt-4 text-2xl font-semibold text-slate-900">
                {formatCurrency(plan.price, plan.currency)}
              </p>
              <p className="text-sm text-slate-600">{formatAllowance(plan)}</p>
            </button>
          );
        })}
      </div>

      <div className="space-y-2">
        <label className="block text-sm font-medium text-slate-700">
          Payment details
        </label>
        <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <CardElement options={cardElementOptions} />
        </div>
        <p className="text-xs text-slate-500">
          Your card will be charged immediately and then on a
          {` ${formatInterval(plans.find(p => p.id === selectedPlan)?.billing_interval)} `}
          basis.
        </p>
      </div>

      {error && <p className="text-sm text-red-600">{error}</p>}
      {success && <p className="text-sm text-green-600">{success}</p>}

      <button
        type="submit"
        className="w-full rounded-xl bg-indigo-600 py-3 text-white font-semibold shadow hover:bg-indigo-500 disabled:cursor-not-allowed disabled:bg-slate-400"
        disabled={disabled || submitting || !stripe}
      >
        {submitting ? 'Processing…' : 'Start subscription'}
      </button>
    </form>
  );
}

function SubscriptionContent() {
  const [plans, setPlans] = useState([]);
  const [plansLoading, setPlansLoading] = useState(true);
  const [plansError, setPlansError] = useState(null);
  const [subscription, setSubscription] = useState(null);
  const [subscriptionLoading, setSubscriptionLoading] = useState(true);
  const [subscriptionError, setSubscriptionError] = useState(null);
  const [cancelling, setCancelling] = useState(false);
  const [cancelError, setCancelError] = useState(null);
  const [cancelSuccess, setCancelSuccess] = useState(null);

  useEffect(() => {
    let cancelled = false;

    (async () => {
      try {
        const [{ data: planData }] = await Promise.all([
          fetchPlans(),
        ]);
        if (!cancelled) {
          setPlans(planData);
          setPlansError(null);
        }
      } catch (err) {
        if (!cancelled) {
          const message =
            err.response?.data?.detail ||
            err.message ||
            'Unable to load plans right now.';
          setPlansError(message);
        }
      } finally {
        if (!cancelled) setPlansLoading(false);
      }
    })();

    (async () => {
      try {
        const { data } = await fetchCurrentSubscription();
        if (!cancelled) {
          setSubscription(data);
          setSubscriptionError(null);
          setCancelError(null);
          setCancelSuccess(null);
        }
      } catch (err) {
        if (!cancelled) {
          if (err.response?.status === 404) {
            setSubscription(null);
            setSubscriptionError(null);
            setCancelError(null);
            setCancelSuccess(null);
          } else {
            const message =
              err.response?.data?.detail ||
              err.message ||
              'Unable to fetch your subscription.';
            setSubscriptionError(message);
          }
        }
      } finally {
        if (!cancelled) setSubscriptionLoading(false);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, []);

  const handleCancelSubscription = useCallback(
    async ({ cancelAtPeriodEnd }) => {
      if (!subscription) return;

      setCancelError(null);
      setCancelSuccess(null);
      setCancelling(true);

      try {
        const { data } = await cancelSubscription({
          cancel_at_period_end: cancelAtPeriodEnd,
        });

        if (!cancelAtPeriodEnd && data.status === 'canceled') {
          setSubscription(null);
        } else {
          setSubscription(data);
        }

        setCancelSuccess(
          cancelAtPeriodEnd
            ? 'Your subscription will be cancelled at the end of the current billing period.'
            : 'Your subscription has been cancelled immediately.'
        );
      } catch (err) {
        const message =
          err.response?.data?.error ||
          err.response?.data?.detail ||
          err.response?.data?.stripe ||
          err.message ||
          'Unable to cancel your subscription.';
        setCancelError(message);
      } finally {
        setCancelling(false);
      }
    },
    [subscription]
  );

  const hasActiveSubscription = useMemo(
    () => Boolean(subscription && subscription.status !== 'canceled'),
    [subscription]
  );

  return (
    <div className="mx-auto max-w-5xl px-4 py-10">
      <div className="mb-8">
        <h1 className="text-3xl font-semibold text-slate-900">Subscription</h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          Access premium test content and track your progress with recurring
          allowances. Pick a plan that fits your team and update payment details
          securely via Stripe.
        </p>
      </div>

      {subscriptionError && (
        <div className="mb-6 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {subscriptionError}
        </div>
      )}

      {cancelSuccess && (
        <div className="mb-4 rounded-xl border border-green-200 bg-green-50 p-4 text-sm text-green-700">
          {cancelSuccess}
        </div>
      )}

      {cancelError && (
        <div className="mb-4 rounded-xl border border-red-200 bg-red-50 p-4 text-sm text-red-700">
          {cancelError}
        </div>
      )}

      {subscriptionLoading ? (
        <div className="mb-8 rounded-2xl border border-slate-200 bg-white p-6 text-center text-slate-500">
          Loading your subscription…
        </div>
      ) : (
        <CurrentSubscription
          subscription={subscription}
          onCancel={handleCancelSubscription}
          cancelling={cancelling}
        />
      )}

      <div className="mt-10 rounded-2xl bg-white p-6 shadow-sm">
        <h2 className="text-xl font-semibold text-slate-900">Choose your plan</h2>
        <p className="mt-1 text-sm text-slate-600">
          Subscriptions renew automatically. You can cancel anytime from this
          page if your needs change.
        </p>

        {plansLoading ? (
          <p className="mt-6 text-sm text-slate-500">Loading plans…</p>
        ) : plansError ? (
          <p className="mt-6 text-sm text-red-600">{plansError}</p>
        ) : (
        <SubscriptionForm
          plans={plans}
          disabled={hasActiveSubscription}
          onSubscribed={data => {
            setSubscription(data);
            setCancelError(null);
            setCancelSuccess(null);
          }}
        />
      )}

      {hasActiveSubscription && (
        <p className="mt-4 rounded-lg bg-indigo-50 p-3 text-sm text-indigo-700">
          You already have an active subscription. Use the options above to
          manage or cancel your plan at any time.
        </p>
      )}
      </div>
    </div>
  );
}

export default function SubscriptionPage() {
  return (
    <Elements stripe={stripePromise}>
      <SubscriptionContent />
    </Elements>
  );
}
