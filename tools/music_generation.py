from __future__ import annotations

import base64
from collections.abc import Generator
from typing import Any

import requests as http_requests
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from minimax_api import (
    build_audio_setting,
    call_music_api,
    yield_audio,
)

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


class MusicGenerationTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        api_key = self.runtime.credentials.get("minimax_api_key")
        api_base = self.runtime.credentials.get("api_base", "https://api.minimaxi.com")

        if not api_key:
            yield self.create_text_message("Error: MiniMax API key is not configured")
            return

        model = str(tool_parameters.get("model") or "music-2.6").strip()
        prompt = str(tool_parameters.get("prompt") or "").strip()
        lyrics = str(tool_parameters.get("lyrics") or "").strip()
        output_format = str(tool_parameters.get("output_format") or "hex").strip()
        cover_feature_id = str(tool_parameters.get("cover_feature_id") or "").strip()
        audio_url = str(tool_parameters.get("audio_url") or "").strip()
        audio_file = tool_parameters.get("audio_file")

        try:
            audio_setting = build_audio_setting(tool_parameters)
        except ValueError as e:
            yield self.create_text_message(f"Error: {e}")
            return

        audio_b64 = ""
        if audio_file:
            try:
                audio_b64 = _encode_file_to_base64(audio_file)
            except Exception as e:
                yield self.create_text_message(f"Error reading audio file: {e}")
                return

        try:
            body = call_music_api(
                api_key=api_key,
                api_base=api_base,
                model=model,
                prompt=prompt,
                lyrics=lyrics,
                output_format=output_format,
                audio_setting=audio_setting,
                is_instrumental=bool(tool_parameters.get("is_instrumental")),
                lyrics_optimizer=bool(tool_parameters.get("lyrics_optimizer")),
                cover_feature_id=cover_feature_id,
                audio_url=audio_url if not audio_b64 else "",
                audio_base64=audio_b64,
            )
        except (ValueError, RuntimeError) as e:
            yield self.create_text_message(f"Error: {e}")
            return
        except Exception as e:
            yield self.create_text_message(f"Request failed: {e}")
            return

        yield from yield_audio(body, self, output_format)
