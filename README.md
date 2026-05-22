# MiniMax Music Generation Plugin

Dify plugin for music generation powered by the [MiniMax](https://platform.minimaxi.com) API. Provides lyrics generation, text-to-music, cover song generation, and a one-click song workflow.

## Prerequisites

- A MiniMax API Key — obtain one from [platform.minimaxi.com](https://platform.minimaxi.com/user-center/basic-information/interface-key)
- Dify instance with plugin runtime support (Python 3.12)

## Installation

1. Clone or download this directory into your Dify plugin workspace.
2. Install the plugin through the Dify dashboard (Settings → Plugins → Install from local folder), or package it as a `.difypkg` file.
3. Configure the following credentials when prompted:

| Credential | Required | Description |
|---|---|---|
| `minimax_api_key` | Yes | Your MiniMax API key |
| `api_base` | No | API base URL. Defaults to `https://api.minimaxi.com` |

## Tools

### 1. Lyrics Generation (`lyrics_generation`)

Generate or edit song lyrics.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `mode` | select | Yes | `write_full_song` | `write_full_song` creates a complete song; `edit` modifies or continues existing lyrics |
| `prompt` | string | No | — | Song theme / style description (max 2000 chars). Leave empty for random generation |
| `lyrics` | string | No | — | Existing lyrics to edit or continue. Only used in `edit` mode (max 3500 chars) |
| `title` | string | No | — | Song title. If provided, the output keeps this title unchanged |

**Output** — text message containing:
- `song_title` — generated song title
- `style_tags` — style labels
- `lyrics` — full lyrics text

---

### 2. Music Generation (`music_generation`)

Generate music from lyrics, descriptions, or reference audio. Supports `music-2.6` (text-to-music) and `music-cover` (cover song) models.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `model` | select | Yes | `music-2.6` | `music-2.6`, `music-2.6-free`, `music-cover`, `music-cover-free` |
| `prompt` | string | No | — | Music style description, e.g. "pop, sad, rainy night" (max 2000 chars) |
| `lyrics` | string | No | — | Lyrics with structure tags like `[Verse]`, `[Chorus]` (max 3500 chars) |
| `output_format` | select | No | `hex` | `hex` returns audio blob; `url` returns a download link (valid 24 hours) |
| `is_instrumental` | boolean | No | `false` | Generate instrumental-only music (no vocals). **music-2.6 only** |
| `lyrics_optimizer` | boolean | No | `false` | Auto-generate lyrics from prompt when `lyrics` is empty. **music-2.6 only** |
| `cover_feature_id` | string | No | — | Feature ID from the Music Cover Preprocess tool. For two-step cover workflow |
| `audio_url` | string | No | — | Reference audio URL for cover models (6 s – 6 min, max 50 MB). Mutually exclusive with `cover_feature_id` |
| `audio_file` | file | No | — | Upload reference audio for cover models. Mutually exclusive with `cover_feature_id` and `audio_url` |
| `sample_rate` | select | No | — | `16000`, `24000`, `32000`, `44100` Hz |
| `bitrate` | select | No | — | `32000`, `64000`, `128000`, `256000` |
| `audio_format` | select | No | — | `mp3`, `wav`, `pcm` |

**Output** depends on `output_format`:

- **`hex` (default)** — text summary (duration, sample rate, size) + audio blob message.
- **`url`** — text summary with download URL + JSON message:
  ```json
  {
    "audio_url": "https://...",
    "duration_ms": 180000,
    "sample_rate": 44100,
    "size": 5242880
  }
  ```

---

### 3. Music Cover Preprocess (`music_cover_preprocess`)

Preprocess a reference audio for two-step cover generation. Extracts audio features and formatted lyrics that are fed into the Music Generation tool.

| Parameter | Type | Required | Description |
|---|---|---|---|
| `audio_url` | string | No* | URL of the reference audio (6 s – 6 min, max 50 MB, mp3/wav/flac) |
| `audio_file` | file | No* | Upload a reference audio file |

\* One of `audio_url` or `audio_file` is required.

**Output** — text + JSON message containing:
- `cover_feature_id` — pass this to the Music Generation tool's `cover_feature_id` parameter
- `formatted_lyrics` — extracted and formatted lyrics
- `structure_result` — song structure analysis
- `audio_duration` — duration in seconds

**Two-step cover workflow:**
1. Run this tool to get a `cover_feature_id`.
2. Pass the `cover_feature_id` to the Music Generation tool with `model=music-cover`.

---

### 4. One-Click Song (`one_click_song`)

Combine lyrics generation and music generation into a single call. Provide a theme description and get a complete song back.

| Parameter | Type | Required | Default | Description |
|---|---|---|---|---|
| `prompt` | string | Yes | — | Song theme and style, e.g. "a cheerful pop song about summer beach" (max 2000 chars) |
| `title` | string | No | — | Optional song title |
| `model` | select | No | `music-2.6` | `music-2.6` or `music-2.6-free` |
| `output_format` | select | No | `hex` | `hex` returns audio blob; `url` returns a download link |
| `is_instrumental` | boolean | No | `false` | Skip lyrics generation; produce instrumental only |
| `sample_rate` | select | No | — | `16000`, `24000`, `32000`, `44100` Hz |
| `bitrate` | select | No | — | `32000`, `64000`, `128000`, `256000` |
| `audio_format` | select | No | — | `mp3`, `wav`, `pcm` |

**Output** — same as Music Generation (text summary + audio blob or URL).

The tool runs in two steps internally:
1. Calls the lyrics API to generate lyrics from the prompt.
2. Calls the music API to produce audio from the generated lyrics.

## Project Structure

```
minimax-music-generation/
├── _assets/
│   └── icon.svg                # Plugin icon
├── provider/
│   ├── minimax.py              # Provider credential validation
│   └── minimax.yaml            # Provider & credential definition
├── tools/
│   ├── lyrics_generation.py    # Lyrics generation tool
│   ├── lyrics_generation.yaml
│   ├── music_generation.py     # Music generation tool
│   ├── music_generation.yaml
│   ├── music_cover_preprocess.py  # Cover preprocessing tool
│   ├── music_cover_preprocess.yaml
│   ├── one_click_song.py       # One-click song tool
│   └── one_click_song.yaml
├── main.py                     # Plugin entry point
├── manifest.yaml               # Plugin manifest
├── minimax_api.py              # Shared MiniMax API client
└── requirements.txt            # Python dependencies
```

## Error Codes

The plugin maps MiniMax API error codes to user-friendly messages:

| Code | Message |
|---|---|
| 1002 | Rate limited — retry later |
| 1004 | Authentication failed — check API key |
| 1008 | Insufficient account balance |
| 1026 | Sensitive content detected in input |
| 2013 | Invalid request parameters |
| 2049 | Invalid API key |

## License

This project is licensed under the [MIT License](LICENSE).
