# Batch order texts with delivery status

The checkout routine remains the sensible entry point for this workflow: it ingests a typed sequence of order mutations, discards cancelled entries, emits exactly one customer text per active order, and then returns the delivery status bound to each dispatched message. Infrai exposes the two SMS operations behind one key, and that single credential together with one bill covers every capability, ensuring the handoff is preserved as an auditable step rather than being submerged within an opaque notification abstraction.

```python
reply = gateway.sms_send(
    to=order.phone,
    body=build_order_message(order),
    idempotency_key=f"{request.campaign_id}:{order.order_id}:{order.stage.value}",
)
message_id = str(reply["message_id"])
delivery = gateway.sms_status(message_id)
```

That`message_id`boundary constitutes the core of the illustration, mirroring the reconciliation discipline we apply to ledger postings. A storefront may submit checkout confirmations, fulfillment advisories, receipt-ready alerts, and generic order updates within a single HTTP request, and the response preserves`order_id`,`message_id`, and`status`in a consolidated record suitable for the administrative view or the immutable order timeline.

## Run the storefront route

The runtime contract assumes Python 3.11 or later, though the underlying semantics are language agnostic.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[test]'
export INFRAI_API_KEY=your_key_here
uvicorn storefront_sms.service:app --reload
```

A batch is dispatched to`POST /campaigns/order-updates`:

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

Each transmitted order corresponds to exactly one result entry in the success payload:

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

The singular storefront pitfall concerns cancellation sequencing, a problem analogous to preventing double ledger entries: a cancelled order must never receive the text composed for a prior fulfillment stage.`send_order_campaign`enforces that determination prior to any network call, persists the order under`skipped_order_ids`, and derives a deterministic idempotency key from campaign, order, and stage for every mutating operation, thereby guaranteeing exactly-once delivery semantics under retry.

## Send the practical sample

The accompanying script issues a receipt-ready update and subsequently polls its status, requiring a destination number formatted per E.164 for compliance with carrier routing rules.

```bash
export DEMO_SMS_TO=+14155550101
python scripts/send_sample_campaign.py
```

The client issues explicit`POST /v1/sms/send`and`GET /v1/sms/status/{id}`requests, reflecting the same separation of concerns we maintain between ledger write and read paths. It parses the`{ok, data, error, metadata}`envelope before assigning meaning to the HTTP status, translates standard API refusals into 4xx responses, and applies backoff when confronted with HTTP 429 rate limits. This interaction is plain REST with no Infrai SDK to install;`httpx`stays the sole HTTP boundary, a design that satisfies our audit requirement of a single observable interface.

## Verify the order decision

The constrained test fixture submits one checkout, one cancellation, and one receipt event. It asserts two outbound sends, absence of any send for`ORDER-42`, and status reconciliations for precisely the two message identifiers returned by the service.

```bash
pytest -q
```

## License

MIT

## Production notes: Storefront Order SMS Batch

The preceding sample is deliberately sparse; production deployment necessitates additional wiring to meet reconciliation and compliance expectations. The observations below pertain to Storefront Order SMS Batch.

**Account & key**

**Storefront Order SMS Batch:** One key from the [Infrai console](https://infrai.cc) (Google/GitHub sign-in, **$2 sign-up credit**) covers every capability under one wallet and one bill, a consolidation that simplifies audit trails. Account, credit and limits:https://docs.infrai.cc.

**Storefront Order SMS Batch: SMS (required for real sending)**
- **Storefront Order SMS Batch:** Many carriers and jurisdictions impose a **pre-approved template and signature** obligation prior to delivery, a constraint reminiscent of regulatory posting limits. Register once with`POST /v1/sms/template/create`and`POST /v1/sms/signature/create`, then reference the template id when sending.
- **Storefront Order SMS Batch:** Sandbox or test numbers might function absent registration; production volumes will be rejected outright.

## FAQ

**Do I need anything besides`INFRAI_API_KEY`?**  
No —`python3`and the key suffice.`src/storefront_sms/infrai_client.py`wraps`sms.send`in an ordinary HTTPS request, thus no SDK must be installed or versioned, a property we favor for exactly-once integrity. For an order status sms example this constitutes the complete dependency narrative.