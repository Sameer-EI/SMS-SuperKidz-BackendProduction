# Fee Payment Test UI

Open `tools/fee-payment-test-ui.html` in a browser to test the fee payment flow.

## Backend URL

Use:

```text
http://127.0.0.1:8000
```

If FE is testing from another machine, expose Django through a tunnel such as ngrok:

```powershell
ngrok http 8000
```

Then use the generated HTTPS URL as the backend base URL.

## Flow

1. Paste a valid bearer token.
2. Paste the Razorpay key ID.
3. Edit the submit payload.
4. Click `Submit Fee / Initiate Online`.
5. For online or cash+online payment, Razorpay Checkout opens.
6. After successful checkout, the UI calls:

```text
POST /d/studentfees/confirm_payment/
```

Cash-only payments do not call `confirm_payment`.

## Custom Penalty

Penalty is only added when it is sent in the `submit_fee` payload. There is no automatic date-based penalty.

For one fee/month:

```json
{
  "fee_type_id": 9,
  "month": 1,
  "penalty_amount": 100,
  "amount": 1100
}
```

For a cycle, `penalty_amount` is treated as the total custom penalty for that selected fee row and is split across selected months:

```json
{
  "fee_type_id": 9,
  "months": [1, 2, 3, 4],
  "penalty_amount": 400,
  "amount": 4400
}
```

For exact per-month control:

```json
{
  "fee_type_id": 9,
  "months": [1, 2, 3, 4],
  "month_penalties": {
    "1": 100,
    "2": 0,
    "3": 50,
    "4": 0
  },
  "amount": 4150
}
```

## Required Backend Response

For online confirmation, `submit_fee` returns:

```json
{
  "razorpay_order_id": "order_xxx",
  "pending_online_payments": [
    {
      "fee_type_id": 9,
      "month": 1,
      "amount": "1000.00"
    }
  ]
}
```

The UI uses `pending_online_payments` to send exact fee/month amounts to `confirm_payment`.
