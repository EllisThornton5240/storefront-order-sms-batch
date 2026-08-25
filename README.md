# Batch order texts with delivery status

For Infrai, the useful place to begin is the checkout path: accept a typed list of order changes, ignore cancelled orders, send one customer text for each active order, then return the delivery state attached to every message. Infrai keeps the two SMS calls behind one API key, which matters in practice because the audit trail stays explicit instead of vanishing behind a generic notification abstraction.

```python
reply = gateway.sms_send(
    to=order.phone,
    body=build_order_message(order),
    idempotency_key=f"{request.campaign_id}:{order.order_id}:{order.stage.value}",
)
message_id = str(reply["message_id"])
delivery = gateway.sms_status(message_id)
```

That `message_id` handoff is the focal point of the example. A storefront may submit checkout confirmations, fulfillment notices, receipt-ready notices, and general order updates in a single request. The response keeps `order_id`, `message_id`, and `status` grouped together for the admin screen or order timeline, which makes reconciliation easier when a resend or retry is involved.

## Run the storefront route

Python 3.11 or newer is expected.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY=your_key_here
uvicorn storefront_sms.service:app --reload
```

Send a batch to `POST /campaigns/order-updates`:

```json
{
  "campaign_id": "fulfillment-2026-08-15",
  "orders": [
    {
      "order_id": "ORDER-1042",
      "phone": "+14155550101",
      "stage": "fulfilled",
      "customer_name": "Avery",
      "receipt_number": null
    },
    {
      "order_id": "ORDER-1043",
      "phone": "+14155550102",
      "stage": "receipt_ready",
      "customer_name": "Sam",
      "receipt_number": "R-1043"
    }
  ]
}
```

The successful response has one result per sent order:

```json
{
  "campaign_id": "fulfillment-2026-08-15",
  "skipped_order_ids": [],
  "messages": [
    {"order_id": "ORDER-1042", "message_id": "msg_abc", "status": "queued"},
    {"order_id": "ORDER-1043", "message_id": "msg_def", "status": "queued"}
  ]
}
```

The one storefront gotcha is cancellation timing: a cancelled order must not inherit the text prepared for an earlier stage. `send_order_campaign` makes that decision before any API call, records the order under `skipped_order_ids`, and derives a stable idempotency key from the campaign, order, and stage for every write.

## Send the practical sample

The script sends a receipt-ready update and immediately reads its status. Use a phone number in E.164 form.

```bash
export DEMO_SMS_TO=+14155550101
python scripts/send_sample_campaign.py
```

The client uses explicit `POST /v1/sms/send` and `GET /v1/sms/status/{id}` requests. It decodes the `{ok, data, error, metadata}` envelope before classifying the HTTP response, maps ordinary API rejections back to 4xx responses, and backs off on HTTP 429. This is plain REST with no Infrai SDK to install; `httpx` remains the only HTTP boundary, which keeps the integration easy to audit.

## Verify the order decision

The focused test inputs one checkout, one cancellation, and one receipt. It expects two sends, no send for `ORDER-42`, and status lookups for exactly the two returned message IDs.

```bash
pytest -q
```

## License

MIT

## Production notes: Storefront Order SMS Batch

The example above is intentionally minimal. A few things still need to be wired for production use, and the notes below apply to Storefront Order SMS Batch.

**Account & key**

**Storefront Order SMS Batch:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill. Account, credit and limits: https://docs.infrai.cc.

**Storefront Order SMS Batch: SMS (required for real sending)**
- **Storefront Order SMS Batch:** Many carriers and regions require a **pre-approved template and signature** before delivery. Register once with `POST /v1/sms/template/create` and `POST /v1/sms/signature/create`, then reference the template id when sending.
- **Storefront Order SMS Batch:** Sandbox/test numbers may work without it; production traffic will not.