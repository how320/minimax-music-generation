from __future__ import annotations

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from minimax_api import (
    build_audio_setting,
    call_lyrics_api,
    call_music_api,
    yield_audio,
)


class OneClickSongTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        api_key = self.runtime.credentials.get("minimax_api_key")
        api_base = self.runtime.credentials.get("api_base", "https://api.minimaxi.com")

        if not api_key:
            yield self.create_text_message("Error: MiniMax API key is not configured")
            return

        prompt = str(tool_parameters.get("prompt") or "").strip()
        if not prompt:
            yield self.create_text_message("Error: prompt is required for one-click song generation")
            return

        title = str(tool_parameters.get("title") or "").strip()
        model = str(tool_parameters.get("model") or "music-2.6").strip()
        output_format = str(tool_parameters.get("output_format") or "hex").strip()
        is_instrumental = bool(tool_parameters.get("is_instrumental"))

        try:
            audio_setting = build_audio_setting(tool_parameters)
        except ValueError as e:
            yield self.create_text_message(f"Error: {e}")
            return

        lyrics = ""
        if not is_instrumental:
            yield self.create_text_message("Step 1/2: Generating lyrics...")
            try:
                lyrics_body = call_lyrics_api(
                    api_key=api_key,
                    api_base=api_base,
                    mode="write_full_song",
                    prompt=prompt,
                    title=title,
                )
                lyrics = lyrics_body.get("lyrics", "")
                song_title = lyrics_body.get("song_title", title or "Untitled")
                style_tags = lyrics_body.get("style_tags", "")
                yield self.create_text_message(
                    f"Lyrics generated:\nTitle: {song_title}\nStyle: {style_tags}\n\n{lyrics[:500]}..."
                )
            except Exception as e:
                yield self.create_text_message(f"Warning: Lyrics generation failed ({e}). Proceeding with prompt only.")

        yield self.create_text_message("Step 2/2: Generating music...")
        try:
            body = call_music_api(
                api_key=api_key,
                api_base=api_base,
                model=model,
                prompt=prompt,
                lyrics=lyrics,
                output_format=output_format,
                audio_setting=audio_setting,
                is_instrumental=is_instrumental,
            )
        except (ValueError, RuntimeError) as e:
            yield self.create_text_message(f"Error: {e}")
            return
        except Exception as e:
            yield self.create_text_message(f"Request failed: {e}")
            return

        yield from yield_audio(body, self, output_format)