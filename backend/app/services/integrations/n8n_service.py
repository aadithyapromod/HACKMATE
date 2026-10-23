import hmac
import hashlib
import json
import uuid
from typing import Dict, Any, Optional, Tuple
from datetime import datetime, timezone
import httpx

from app.config import settings
from app.core.logging import logger


class N8NService:
    @property
    def is_configured(self) -> bool:
        return bool(settings.N8N_WEBHOOK_URL and settings.N8N_WEBHOOK_URL.strip())

    def _generate_signature(self, payload_bytes: bytes) -> str:
        """Generates an HMAC SHA-256 signature for webhook payload verification."""
        secret = settings.N8N_WEBHOOK_SECRET.encode("utf-8") if settings.N8N_WEBHOOK_SECRET else b"hackmate-default-secret"
        return hmac.new(secret, payload_bytes, hashlib.sha256).hexdigest()

    async def send_event(
        self,
        event_type: str,
        project_id: str,
        data: Optional[Dict[str, Any]] = None
    ) -> Tuple[bool, str]:
        """
        Dispatches an authenticated webhook event to n8n with signature and idempotency token.
        Non-blocking, with a 5.0 second timeout.
        """
        if not self.is_configured:
            return False, "n8n webhook is not configured."

        delivery_id = str(uuid.uuid4())
        payload = {
            "event": event_type,
            "project_id": project_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "payload": data or {}
        }

        payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        signature = self._generate_signature(payload_bytes)

        headers = {
            "Content-Type": "application/json",
            "X-HackMate-Delivery-Id": delivery_id,
            "X-HackMate-Signature": f"sha256={signature}",
            "User-Agent": "HackMate-Webhook-Dispatcher/2.0",
        }

        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.post(
                    settings.N8N_WEBHOOK_URL.strip(),
                    content=payload_bytes,
                    headers=headers
                )
                if resp.status_code in (200, 201, 204):
                    logger.info(f"n8n webhook delivered: event={event_type}, project={project_id}")
                    return True, f"Delivered successfully (HTTP {resp.status_code})"
                else:
                    logger.warning(f"n8n webhook returned HTTP {resp.status_code}: {resp.text[:100]}")
                    return False, f"Webhook server returned HTTP {resp.status_code}"
        except httpx.TimeoutException:
            logger.warning(f"n8n webhook timed out after 5.0s for event {event_type}")
            return False, "Webhook request timed out."
        except Exception as e:
            logger.error(f"Failed to dispatch n8n webhook: {str(e)}")
            return False, f"Dispatch error: {str(e)}"

    async def send_test_ping(self) -> Tuple[bool, str]:
        """Sends a verification ping to confirm the configured n8n workflow endpoint is live."""
        return await self.send_event(
            event_type="test.ping",
            project_id="00000000-0000-0000-0000-000000000000",
            data={"message": "HackMate to n8n connectivity test verification."}
        )


n8n_service = N8NService()
