from __future__ import annotations

from collections.abc import Generator
from typing import Any

from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from minimax_api import call_lyrics_api


class LyricsGenerationTool(Tool):
    def _invoke(self, tool_parameters: dict[str, Any]) -> Generator[ToolInvokeMessage, None, None]:
        api_key = self.runtime.credentials.get("minimax_api_key")
        api_base = self.runtime.credentials.get("api_base", "https://api.minimaxi.com")

        if not api_key:
            yield self.create_text_message("Error: MiniMax API key is not configured")
            return

        mode = str(tool_parameters.get("mode") or "write_full_song").strip()
        if mode not in ("write_full_song", "edit"):
            yield self.create_text_message(f"Error: Invalid mode {mode!r}. Must be 'write_full_song' or 'edit'.")
            return

        prompt = str(tool_parameters.get("prompt") or "").strip()
        lyrics = str(tool_parameters.get("lyrics") or "").strip()
        title = str(tool_parameters.get("title") or "").strip()

        try:
            body = call_lyrics_api(
                api_key=api_key,
                api_base=api_base,
                mode=mode,
                prompt=prompt,
                lyrics=lyrics,
                title=title,
            )
        except (ValueError, RuntimeError) as e:
            yield self.create_text_message(f"Error: {e}")
            return
        except Exception as e:
            yield self.create_text_message(f"Request failed: {e}")
            return

        song_title = body.get("song_title", "")
        style_tags = body.get("style_tags", "")
        generated_lyrics = body.get("lyrics", "")

        result = f"Song Title: {song_title}\nStyle Tags: {style_tags}\n\n{generated_lyrics}"
        yield self.create_text_message(result)
