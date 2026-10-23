import pytest
from unittest.mock import AsyncMock, patch
from httpx import AsyncClient, Response

from app.config import settings
from app.core.ssrf_protection import validate_url_ssrf, SSRFViolationError
from app.services.integrations.firecrawl_service import firecrawl_service
from app.services.integrations.n8n_service import n8n_service
from app.services.integrations.adaption_service import adaption_service, AdaptionConsentError


def test_ssrf_protection_blocks_private_networks():
    with pytest.raises(SSRFViolationError, match="restricted local or internal"):
        validate_url_ssrf("http://localhost:8000/api")

    with pytest.raises(SSRFViolationError):
        validate_url_ssrf("http://127.0.0.1:3000")

    with pytest.raises(SSRFViolationError, match="blocked private or metadata IP"):
        validate_url_ssrf("http://169.254.169.254/latest/meta-data/")

    with pytest.raises(SSRFViolationError):
        validate_url_ssrf("http://10.0.0.5/admin")

    with pytest.raises(SSRFViolationError):
        validate_url_ssrf("http://192.168.1.1/router")

    with pytest.raises(SSRFViolationError, match="Protocol 'ftp' is forbidden"):
        validate_url_ssrf("ftp://files.example.com")

    with pytest.raises(SSRFViolationError, match="Protocol 'file' is forbidden"):
        validate_url_ssrf("file:///etc/passwd")


def test_ssrf_protection_allows_valid_public_domain():
    is_safe, url = validate_url_ssrf("https://example.com/about")
    assert is_safe is True
    assert url == "https://example.com/about"


@pytest.mark.asyncio
async def test_firecrawl_graceful_fallback_when_unconfigured():
    with patch.object(settings, "FIRECRAWL_API_KEY", ""):
        res = await firecrawl_service.scrape_reference_design("https://example.com")
        assert res is None


@pytest.mark.asyncio
async def test_firecrawl_mocked_success():
    with patch.object(settings, "FIRECRAWL_API_KEY", "fc-mock-test-key"):
        mock_response = Response(
            status_code=200,
            json={"data": {"markdown": "# Example Domain\n\nThis is a sample layout."}}
        )
        with patch("httpx.AsyncClient.post", new_callable=AsyncMock, return_value=mock_response):
            res = await firecrawl_service.scrape_reference_design("https://example.com")
            assert res is not None
            assert "REFERENCE SITE LAYOUT" in res
            assert "Example Domain" in res


@pytest.mark.asyncio
async def test_n8n_webhook_signature_and_headers():
    with patch.object(settings, "N8N_WEBHOOK_URL", "https://n8n.internal.mock/webhook/123"):
        with patch.object(n8n_service, "send_event", new_callable=AsyncMock) as mock_send:
            mock_send.return_value = (True, "Delivered successfully")
            ok, msg = await n8n_service.send_event(
                event_type="project.ready",
                project_id="test-proj-id",
                data={"status": "READY"}
            )
            assert ok is True


@pytest.mark.asyncio
async def test_adaption_consent_guard():
    with pytest.raises(AdaptionConsentError):
        await adaption_service.prepare_curated_dataset_entry(
            prompt="Test prompt",
            validated_manifest=["package.json"],
            user_opt_in=False
        )

    with patch.object(settings, "ADAPTION_API_KEY", "adp-mock-test-key"):
        entry = await adaption_service.prepare_curated_dataset_entry(
            prompt="Test prompt",
            validated_manifest=["package.json"],
            user_opt_in=True
        )
        assert entry is not None
        assert entry["instruction"] == "Test prompt"


@pytest.mark.asyncio
async def test_integrations_api_endpoints(client: AsyncClient):
    status_resp = await client.get("/api/v2/integrations/status")
    assert status_resp.status_code == 200
    data = status_resp.json()
    assert "firecrawl" in data
    assert "n8n" in data
    assert "adaption" in data

    ssrf_resp = await client.post("/api/v2/integrations/firecrawl/test", json={"test_url": "http://127.0.0.1:8000"})
    assert ssrf_resp.status_code in (400, 503)

    info_resp = await client.get("/api/v2/integrations/adaption/info")
    assert info_resp.status_code == 200
    info_data = info_resp.json()
    assert "data_governance" in info_data
    assert info_data["data_governance"]["requires_explicit_user_consent"] is True
