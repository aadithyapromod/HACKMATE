from typing import Dict, Any, Optional, Tuple, List
from app.config import settings
from app.core.logging import logger
from app.core.errors import HackMateException


class AdaptionConsentError(HackMateException):
    def __init__(self, message: str = "User consent required before exporting dataset to Adaption API."):
        super().__init__(message, status_code=403)


class AdaptionService:
    """
    Integration interface for Adaption Labs API (https://adaptionlabs.ai).
    
    CAPABILITY ANALYSIS:
    - Adaption is an automated model training, data generation (Invent API), and recipe optimization
      platform (AutoScientist API). It is NOT a real-time code-generation inference endpoint.
    - Relevant HackMate Use Case: Curating, profiling, and evaluating golden prompt-completion datasets
      for training specialized offline models or evaluating generation diversity/win rates.
    
    SAFETY & DATA GOVERNANCE RULES:
    1. NEVER send private user prompts, codebase files, or credentials without explicit user opt-in consent.
    2. Zero runtime dependency for core generation pipeline.
    3. Disabled by default.
    """

    @property
    def is_configured(self) -> bool:
        return bool(settings.ADAPTION_API_KEY and settings.ADAPTION_API_KEY.strip())

    def get_status_info(self) -> Dict[str, Any]:
        return {
            "configured": self.is_configured,
            "status": "active" if self.is_configured else "disabled",
            "supported_use_case": "Curated React+Vite golden dataset profiling and evaluation for AutoScientist tuning",
            "data_governance": {
                "requires_explicit_user_consent": True,
                "private_projects_shared": False,
                "data_retention_policy": "External service retention subject to Adaption Labs terms. Datasets stored in user's Adaption account.",
            },
            "cost_and_quota_implications": (
                "Dataset uploads incur storage and profiling compute units on Adaption Labs. "
                "AutoScientist training runs require compute allocation depending on target model size."
            )
        }

    async def prepare_curated_dataset_entry(
        self,
        prompt: str,
        validated_manifest: List[str],
        user_opt_in: bool = False
    ) -> Optional[Dict[str, Any]]:
        """
        Formats a validated, high-quality prompt-and-manifest pair into an evaluation dataset row.
        STRICT REQUIREMENT: Requires explicit user authorization (user_opt_in=True).
        """
        if not user_opt_in:
            raise AdaptionConsentError(
                "Cannot prepare or export dataset to Adaption API without explicit user authorization."
            )

        if not self.is_configured:
            logger.info("Adaption API is not configured. Dataset export skipped.")
            return None

        # Clean, privacy-safe instruction pair (no secrets or environment variables)
        return {
            "instruction": prompt.strip(),
            "target_stack": "react-vite-typescript",
            "expected_manifest": validated_manifest,
        }


adaption_service = AdaptionService()
