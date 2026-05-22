import logging

import requests
from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

logger = logging.getLogger(__name__)

VALIDATION_MODEL = "minimax-m2.5"


class MiniMaxMusicProvider(ToolProvider):
    def _validate_credentials(self, credentials: dict) -> None:
        api_key = credentials.get("minimax_api_key")
        if not api_key:
            raise ToolProviderCredentialValidationError("API key is required")

        api_base = credentials.get("api_base", "https://api.minimaxi.com").rstrip("/")
        url = f"{api_base}/v1/text/chatcompletion_v2"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        }
        payload = {
            "model": VALIDATION_MODEL,
            "messages": [{"role": "user", "content": "hi"}],
        }

        try:
            response = requests.post(url, headers=headers, json=payload, timeout=30)
            if response.status_code == 401:
                raise ToolProviderCredentialValidationError("Invalid API key")
            if response.status_code == 1004:
                raise ToolProviderCredentialValidationError("Authentication failed: invalid API key")
            if response.status_code != 200:
                body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {}
                status_code = body.get("base_resp", {}).get("status_code", response.status_code)
                status_msg = body.get("base_resp", {}).get("status_msg", response.text)
                if status_code in (1004, 2049):
                    raise ToolProviderCredentialValidationError(f"Authentication failed: {status_msg}")

        except requests.exceptions.ConnectionError:
            raise ToolProviderCredentialValidationError(f"Cannot connect to {api_base}")
        except requests.exceptions.Timeout:
            raise ToolProviderCredentialValidationError("Connection timed out while validating credentials")
        except ToolProviderCredentialValidationError:
            raise
        except Exception as e:
            logger.exception("Unexpected error validating credentials")
            raise ToolProviderCredentialValidationError(f"Validation failed: {e}")