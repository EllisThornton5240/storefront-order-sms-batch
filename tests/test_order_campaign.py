from storefront_sms.order_campaign import CampaignRequest, OrderUpdate, send_order_campaign


class RecordingGateway:
    def __init__(self) -> None:
        self.sent: list[dict[str, str]] = []
        self.status_ids: list[str] = []

    def sms_send(self, *, to: str, body: str, idempotency_key: str) -> dict[str, object]:
        self.sent.append({"to": to, "body": body, "idempotency_key": idempotency_key})
        return {"message_id": f"msg-{len(self.sent)}"}

    def sms_status(self, message_id: str) -> dict[str, object]:
        self.status_ids.append(message_id)
        return {"status": "queued"}


def test_campaign_skips_cancelled_order_and_checks_each_sent_message() -> None:
    gateway = RecordingGateway()
    request = CampaignRequest(
        campaign_id="checkout-wave-7",
        orders=[
            OrderUpdate(
                order_id="ORDER-41",
                phone="+14155550101",
                stage="checkout_confirmed",
                customer_name="Mina",
            ),
            OrderUpdate(
                order_id="ORDER-42",
                phone="+14155550102",
                stage="cancelled",
                customer_name="Jules",
            ),
            OrderUpdate(
                order_id="ORDER-43",
                phone="+14155550103",
                stage="receipt_ready",
                customer_name="Ren",
                receipt_number="R-43",
            ),
        ],
    )

    result = send_order_campaign(request, gateway)

    assert result.skipped_order_ids == ["ORDER-42"]
    assert [message.order_id for message in result.messages] == ["ORDER-41", "ORDER-43"]
    assert gateway.status_ids == ["msg-1", "msg-2"]
    assert gateway.sent[1] == {
        "to": "+14155550103",
        "body": "Hi Ren, order ORDER-43: receipt R-43 is ready.",
        "idempotency_key": "checkout-wave-7:ORDER-43:receipt_ready",
    }
