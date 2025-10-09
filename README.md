# psy-project-combined-22sept2025
Combined Django and React apps

- **backend/**: Django (run: `py manage.py runserver 0.0.0.0:8000`)
- **frontend/**: React + Vite (run: `npm run dev` on port 5173)

Tunnels:
- api.investmentlab.org → http://localhost:8000
- app.investmentlab.org → http://localhost:5173

## Subscription Billing

The Django backend now exposes subscription APIs under the `/payment/subscriptions/` prefix.

* `GET /payment/subscriptions/plans/` – list active plans.
* `POST /payment/subscriptions/` – create a subscription for the authenticated user. Requires a Stripe payment method and plan ID.
* `GET /payment/subscriptions/me/` – view the subscriber's current status and remaining allowance.

Unused allowances roll forward via a ledger stored in `payment.TestAllowanceLedger`. Run the management command below on a schedule (e.g., monthly) to post new allowances for active subscribers:

```
python manage.py accrue_subscription_allowances
```
