from fastapi import Depends, FastAPI, HTTPException

from .infrai_client import InfraiClient, InfraiError
from .order_campaign import CampaignRequest, CampaignResult, send_order_campaign


app = FastAPI(title="Storefront order SMS batch")


def get_infrai() -> InfraiClient:
    with InfraiClient() as client:
        yield client


@app.post("/campaigns/order-updates", response_model=CampaignResult)
def create_order_campaign(
    request: CampaignRequest,
    infrai: InfraiClient = Depends(get_infrai),
) -> CampaignResult:
    try:
        return send_order_campaign(request, infrai)
    except InfraiError as exc:
        caller_status = exc.status_code if 400 <= exc.status_code < 500 else 502
        raise HTTPException(
            status_code=caller_status,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
