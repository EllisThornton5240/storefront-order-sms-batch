from __future__ import annotations

from enum import StrEnum
from typing import Protocol

from pydantic import BaseModel, Field


class OrderStage(StrEnum):
    CHECKOUT_CONFIRMED = "checkout_confirmed"
    FULFILLED = "fulfilled"
    RECEIPT_READY = "receipt_ready"
    ORDER_UPDATED = "order_updated"
    CANCELLED = "cancelled"


class OrderUpdate(BaseModel):
    order_id: str = Field(min_length=1, max_length=80)
    phone: str = Field(pattern=r"^\+[1-9]\d{7,14}$")
    stage: OrderStage
    customer_name: str = Field(min_length=1, max_length=60)
    receipt_number: str | None = Field(default=None, max_length=80)


class CampaignRequest(BaseModel):
    campaign_id: str = Field(min_length=1, max_length=80)
    orders: list[OrderUpdate] = Field(min_length=1, max_length=100)


class MessageResult(BaseModel):
    order_id: str
    message_id: str
    status: str


class CampaignResult(BaseModel):
    campaign_id: str
    skipped_order_ids: list[str]
    messages: list[MessageResult]


class SmsGateway(Protocol):
    def sms_send(self, *, to: str, body: str, idempotency_key: str) -> dict[str, object]:
        """Send one order update and return its message identifier."""

    def sms_status(self, message_id: str) -> dict[str, object]:
        """Read delivery status for a previously returned identifier."""


def build_order_message(order: OrderUpdate) -> str:
    if order.stage == OrderStage.CHECKOUT_CONFIRMED:
        detail = "we received your checkout"
    elif order.stage == OrderStage.FULFILLED:
        detail = "your order has been fulfilled"
    elif order.stage == OrderStage.RECEIPT_READY:
        if not order.receipt_number:
            raise ValueError("receipt_number is required for receipt_ready")
        detail = f"receipt {order.receipt_number} is ready"
    elif order.stage == OrderStage.ORDER_UPDATED:
        detail = "your order details were updated"
    else:
        raise ValueError("cancelled orders are not messageable")
    return f"Hi {order.customer_name}, order {order.order_id}: {detail}."


def send_order_campaign(request: CampaignRequest, gateway: SmsGateway) -> CampaignResult:
    sent: list[MessageResult] = []
    skipped: list[str] = []

    for order in request.orders:
        if order.stage == OrderStage.CANCELLED:
            skipped.append(order.order_id)
            continue

        reply = gateway.sms_send(
            to=order.phone,
            body=build_order_message(order),
            idempotency_key=f"{request.campaign_id}:{order.order_id}:{order.stage.value}",
        )
        message_id = str(reply["message_id"])
        delivery = gateway.sms_status(message_id)
        sent.append(
            MessageResult(
                order_id=order.order_id,
                message_id=message_id,
                status=str(delivery["status"]),
            )
        )

    return CampaignResult(
        campaign_id=request.campaign_id,
        skipped_order_ids=skipped,
        messages=sent,
    )
