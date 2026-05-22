from __future__ import annotations

import base64
import json
import logging
from collections.abc import Generator
from typing import Any

import requests
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

logger = logging.getLogger(__name__)

API_BASE = "https://api.minimaxi.com"
REQUEST_TIMEOUT = 300

LYRICS_ENDPOINT = "/v1/lyrics_generation"
COVER_PREPROCESS_ENDPOINT = "/v1/music_cover_preprocess"
MUSIC_ENDPOINT = "/v1/music_generation"

VALID_SAMPLE_RATES = (16000, 24000, 32000, 44100)
VALID_BITRATES = (32000, 64000, 128000, 256000)
VALID_AUDIO_FORMATS = ("mp3", "wav", "pcm")
VALID_MUSIC_MODELS = ("music-2.6", "music-cover", "music-2.6-free", "music-cover-free")

ERROR_MESSAGES: dict[int, str] = {
    1002: "请求过于频繁，请稍后再试 (Rate limited)",
    1004: "API Key 认证失败，请检查配置 (Authentication failed)",
    1008: "账户余额不足 (Insufficient balance)",
    1026: "输入内容包含敏感信息 (Sensitive content detected)",
    2013: "请求参数异常，请检查输入 (Invalid parameters)",
    2049: "无效的 API Key (Invalid API key)",
}


def _has_value(v: Any) -> bool:
    if v is None:
        return False
    if isinstance(v, str) and v.strip() in ("", "None"):
        return False
    return True


def _is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.lower() in ("true", "yes", "y", "1")
    return bool(value)


def _safe_int(value: Any, name: str) -> int:
    if value is None or value == "" or value == "None":
        raise ValueError(f"{name} must be a valid integer, got {value!r}")
    try:
        return int(float(value))
    except (ValueError, TypeError):
        raise ValueError(f"{name} must be a valid integer, got {value!r}")


def _check_base_resp(body: dict[str, Any]) -> None:
    base_resp = body.get("base_resp", {})
    status_code = base_resp.get("status_code", 0)
    if status_code != 0:
        status_msg = base_resp.get("status_msg", "Unknown error")
        friendly = ERROR_MESSAGES.get(status_code, f"API error code {status_code}")
        raise RuntimeError(f"MiniMax API error: {friendly} — {status_msg}")


def _call_api(
    endpoint: str,
    api_key: str,
    api_base: str,
    payload: dict[str, Any],
    timeout: int = REQUEST_TIMEOUT,
) -> dict[str, Any]:
    url = f"{api_base.rstrip('/')}{endpoint}"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
    }
    logger.info("MiniMax API request: POST %s", url)
    response = requests.post(url, headers=headers, json=payload, timeout=timeout)
    body = response.json()
    logger.info("MiniMax API response: status=%s", response.status_code)
    _check_base_resp(body)
    return body


def build_audio_setting(tool_parameters: dict[str, Any]) -> dict[str, Any] | None:
    sample_rate = tool_parameters.get("sample_rate")
    bitrate = tool_parameters.get("bitrate")
    audio_format = tool_parameters.get("audio_format")

    if not _has_value(sample_rate) and not _has_value(bitrate) and not _has_value(audio_format):
        return None

    setting: dict[str, Any] = {}
    if _has_value(sample_rate):
        sr = _safe_int(sample_rate, "sample_rate")
        if sr not in VALID_SAMPLE_RATES:
            raise ValueError(f"Invalid sample_rate {sr}. Must be one of {VALID_SAMPLE_RATES}")
        setting["sample_rate"] = sr
    if _has_value(bitrate):
        br = _safe_int(bitrate, "bitrate")
        if br not in VALID_BITRATES:
            raise ValueError(f"Invalid bitrate {br}. Must be one of {VALID_BITRATES}")
        setting["bitrate"] = br
    if _has_value(audio_format):
        fmt = str(audio_format).strip()
        if fmt not in VALID_AUDIO_FORMATS:
            raise ValueError(f"Invalid audio_format {fmt!r}. Must be one of {VALID_AUDIO_FORMATS}")
        setting["format"] = fmt
    return setting if setting else None


def call_lyrics_api(
    api_key: str,
    api_base: str,
    mode: str,
    prompt: str = "",
    lyrics: str = "",
    title: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {"mode": mode}
    if prompt:
        payload["prompt"] = prompt[:2000]
    if mode == "edit" and lyrics:
        payload["lyrics"] = lyrics[:3500]
    if title:
        payload["title"] = title
    return _call_api(LYRICS_ENDPOINT, api_key, api_base, payload)


def call_cover_preprocess_api(
    api_key: str,
    api_base: str,
    audio_url: str = "",
    audio_base64: str = "",
) -> dict[str, Any]:
    payload: dict[str, Any] = {"model": "music-cover"}
    if audio_base64:
        payload["audio_base64"] = audio_base64
    elif audio_url:
        payload["audio_url"] = audio_url
    else:
        raise ValueError("Either audio_url or audio_base64 is required")
    return _call_api(COVER_PREPROCESS_ENDPOINT, api_key, api_base, payload)


def call_music_api(
    api_key: str,
    api_base: str,
    model: str,
    prompt: str = "",
    lyrics: str = "",
    output_format: str = "hex",
    audio_setting: dict[str, Any] | None = None,
    is_instrumental: bool = False,
    lyrics_optimizer: bool = False,
    cover_feature_id: str = "",
    audio_url: str = "",
    audio_base64: str = "",
) -> dict[str, Any]:
    if model not in VALID_MUSIC_MODELS:
        raise ValueError(f"Invalid model {model!r}. Must be one of {VALID_MUSIC_MODELS}")

    payload: dict[str, Any] = {
        "model": model,
        "stream": False,
        "output_format": output_format,
    }

    if prompt:
        payload["prompt"] = prompt[:2000]
    if lyrics:
        payload["lyrics"] = lyrics[:3500]
    if audio_setting:
        payload["audio_setting"] = audio_setting

    if model in ("music-2.6", "music-2.6-free"):
        if is_instrumental:
            payload["is_instrumental"] = True
        if lyrics_optimizer:
            payload["lyrics_optimizer"] = True

    if model in ("music-cover", "music-cover-free"):
        if cover_feature_id:
            payload["cover_feature_id"] = cover_feature_id
        elif audio_base64:
            payload["audio_base64"] = audio_base64
        elif audio_url:
            payload["audio_url"] = audio_url

    return _call_api(MUSIC_ENDPOINT, api_key, api_base, payload)


def yield_audio(
    body: dict[str, Any],
    tool: Tool,
    output_format: str = "hex",
) -> Generator[ToolInvokeMessage, None, None]:
    data = body.get("data", {})
    status = data.get("status")
    if status == 1:
        yield tool.create_text_message("Music is still being generated (status: processing). Please try again later.")
        return

    extra_info = body.get("extra_info", {})
    duration = extra_info.get("music_duration", 0)
    sample_rate = extra_info.get("music_sample_rate", 0)
    size = extra_info.get("music_size", 0)

    audio_field = data.get("audio", "")
    if not audio_field:
        yield tool.create_text_message("No audio data returned from MiniMax API")
        return

    if output_format == "url":
        # When output_format is "url", MiniMax returns the download URL in data.audio
        yield tool.create_text_message(
            f"Music generated successfully.\n"
            f"Duration: {duration / 1000:.1f}s | Sample rate: {sample_rate}Hz | Size: {size} bytes\n"
            f"Audio URL (valid for 24 hours): {audio_field}"
        )
        yield tool.create_json_message({
            "audio_url": audio_field,
            "duration_ms": duration,
            "sample_rate": sample_rate,
            "size": size,
        })
    else:
        audio_bytes = bytes.fromhex(audio_field)
        audio_fmt = extra_info.get("format", "mp3")
        mime_map = {"mp3": "audio/mpeg", "wav": "audio/wav", "pcm": "audio/pcm"}
        mime_type = mime_map.get(audio_fmt, "audio/mpeg")
        yield tool.create_text_message(
            f"Music generated successfully.\n"
            f"Duration: {duration / 1000:.1f}s | Sample rate: {sample_rate}Hz | Size: {len(audio_bytes)} bytes"
        )
        yield tool.create_blob_message(
            audio_bytes,
            meta={"mime_type": mime_type},
        )