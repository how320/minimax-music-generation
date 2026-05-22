from __future__ import annotations

import base64
from collections.abc import Generator
from typing import Any

import requests as http_requests
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from minimax_api import call_cover_preprocess_api

_DIFY_INTERNAL_API_URL = "http://api:5001"


def _resolve_file_url(url: str) -> str:
    if url.startswith(("http://", "https://")):
        return url
    return f"{_DIFY_INTERNAL_API_URL.rstrip('/')}/{url.lstrip('/')}"


def _encode_file_to_base64(file_obj: Any) -> str:
    url = getattr(file_obj, "url", None)
    if not url:
        raise ValueError(
            f"Cannot read audio file: no URL found. "
            f"type={type(file_obj).__name__}, value={repr(file_obj)[:200]}"
        )
    url = _resolve_file_url(url)
    resp = http_requests.get(url, timeout=120)
    resp.raise_for_status()
    return base64.b64encode(resp.content).decode("utf-8")


class MusicCoverPreprocessTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        api_key = self.runtime.credentials.get("minimax_api_key")
        api_base = self.runtime.credentials.get("api_base", "https://api.minimaxi.com")

        if not api_key:
            yield self.create_text_message("Error: MiniMax API key is not configured")
            return

        audio_url = str(tool_parameters.get("audio_url") or "").strip()
        audio_file = tool_parameters.get("audio_file")

        audio_b64 = ""
        if audio_file:
            try:
                audio_b64 = _encode_file_to_base64(audio_file)
            except Exception as e:
                yield self.create_text_message(f"Error reading audio file: {e}")
                return
        elif not audio_url:
            yield self.create_text_message("Error: Either audio_url or audio_file is required")
            return

        try:
            body = call_cover_preprocess_api(
                api_key=api_key,
                api_base=api_base,
                audio_url=audio_url if not audio_b64 else "",
                audio_base64=audio_b64,
            )
        except (ValueError, RuntimeError) as e:
            yield self.create_text_message(f"Error: {e}")
            return
        except Exception as e:
            yield self.create_text_message(f"Request failed: {e}")
            return

        cover_feature_id = body.get("cover_feature_id", "")
        formatted_lyrics = body.get("formatted_lyrics", "")
        structure_result = body.get("structure_result", "")
        audio_duration = body.get("audio_duration", 0)

        result = (
            f"Cover Feature ID: {cover_feature_id}\n"
            f"Audio Duration: {audio_duration}s\n"
            f"\nFormatted Lyrics:\n{formatted_lyrics}\n"
            f"\nStructure Result:\n{structure_result}"
        )
        yield self.create_text_message(result)
        yield self.create_json_message({
            "cover_feature_id": cover_feature_id,
            "formatted_lyrics": formatted_lyrics,
            "structure_result": structure_result,
            "audio_duration": audio_duration,
        })