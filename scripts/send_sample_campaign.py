import json
import os

from storefront_sms.infrai_client import InfraiClient
from storefront_sms.order_campaign import CampaignRequest, OrderStage, OrderUpdate, send_order_campaign


phone = os.environ.get("DEMO_SMS_TO")
if not phone:
    raise RuntimeError("DEMO_SMS_TO is required")

campaign = CampaignRequest(
    campaign_id="checkout-demo-2026-08-15",
    orders=[
        OrderUpdate(
            order_id="ORDER-1042",
            phone=phone,
            stage=OrderStage.RECEIPT_READY,
            customer_name="Avery",
            receipt_number="R-1042",
        )
    ],
)

with InfraiClient() as client:
    result = send_order_campaign(campaign, client)

print(json.dumps(result.model_dump(), indent=2))
