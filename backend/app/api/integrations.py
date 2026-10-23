from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, HttpUrl
from typing import Dict, Any, Optional

from app.services.integrations.firecrawl_service import firecrawl_service
from app.services.integrations.n8n_service import n8n_service
from app.services.integrations.adaption_service import adaption_service
from app.core.ssrf_protection import validate_url_ssrf, SSRFViolationError

router = APIRouter(prefix="/integrations", tags=["Integrations"])


class FirecrawlTestRequest(BaseModel):
    test_url: str = "https://example.com"


class IntegrationStatusResponse(BaseModel):
    firecrawl: Dict[str, Any]
    n8n: Dict[str, Any]
    adaption: Dict[str, Any]


@router.get("/status", response_model=IntegrationStatusResponse)
async def get_integrations_status():
    """Retrieves operational readiness status for optional pluggable integrations."""
    fc_ok, fc_msg = await firecrawl_service.check_readiness()
    
    return IntegrationStatusResponse(
        firecrawl={
            "configured": firecrawl_service.is_configured,
            "status": "ready" if fc_ok else "unconfigured",
            "message": fc_msg,
        },
        n8n={
            "configured": n8n_service.is_configured,
            "status": "ready" if n8n_service.is_configured else "unconfigured",
            "webhook_configured": bool(n8n_service.is_configured),
        },
        adaption=adaption_service.get_status_info()
    )


@router.post("/firecrawl/test")
async def test_firecrawl_connection(payload: FirecrawlTestRequest):
    """Executes a real test scrape against a validated public URL to confirm Firecrawl connectivity."""
    if not firecrawl_service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="FIRECRAWL_API_KEY is not configured in backend environment."
        )

    # Validate SSRF
    try:
        validate_url_ssrf(payload.test_url)
    except SSRFViolationError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"SSRF violation: {e.message}"
        )

    summary = await firecrawl_service.scrape_reference_design(payload.test_url)
    if not summary:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Firecrawl test request failed. Check API key validity, credits, or target website reachability."
        )

    return {
        "status": "success",
        "scraped_preview": summary[:300],
        "message": "Firecrawl connection successfully verified."
    }


@router.post("/n8n/test")
async def test_n8n_webhook():
    """Dispatches a signed test ping to the configured n8n webhook URL to verify receipt."""
    if not n8n_service.is_configured:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="N8N_WEBHOOK_URL is not configured in backend environment."
        )

    success, message = await n8n_service.send_test_ping()
    if not success:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"n8n test ping delivery failed: {message}"
        )

    return {"status": "success", "message": message}


@router.get("/adaption/info")
async def get_adaption_info():
    """Returns dataset preparation capabilities, data retention, and consent policy for Adaption."""
    return adaption_service.get_status_info()
