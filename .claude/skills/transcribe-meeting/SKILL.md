---
name: transcribe-meeting
description: Transcribe a team meeting recorded by Craig (the Discord recording bot) into a speaker-labelled Markdown transcript plus a short summary. Use when the user gives a Craig zip (craig-*.zip with one .aac/.flac track per speaker, info.txt, raw.dat), says "transcribe the meeting", or invokes /transcribe-meeting.
---

# Transcribe a Craig meeting recording

Craig zips hold one audio track per speaker (`1-<handle>.aac`, ...), all time-aligned
from the recording start, plus `info.txt` (guild, channel, start time, tracks) and
`raw.dat` (ignored). The script transcribes each track locally with Whisper
(faster-whisper, free, no API) and merges them by timestamp, so speakers are exact
(from the track) and only the words can be wrong.

## Steps

1. **Environment** (once per machine). Use a venv outside the repo, e.g. in the scratchpad:
   ```bash
   python -m venv <scratch>/whisper-venv
   <scratch>/whisper-venv/Scripts/python -m pip install faster-whisper
   ```
   For the GPU on Windows, also `pip install nvidia-cublas-cu12 nvidia-cudnn-cu12==9.*`;
   the script adds their DLL folders itself and falls back to CPU if CUDA still fails.
   The first run downloads the model (~0.5 GB for `small`).
2. **Read `info.txt`** from the zip for the start time (UTC; convert to the user's local
   date) and the speaker list.
3. **Run** in the background. A 2-hour, 4-speaker meeting took ~17 min with `medium` on a
   GTX 1660 Ti; expect several times that on CPU.
   ```bash
   <venv-python> -I .claude/skills/transcribe-meeting/scripts/transcribe_craig.py <zip> docs/meetings/<YYYY-MM-DD>-transcript.md
   ```
   Options: `--model medium` (better, slower), `--language en` (skip per-track detection
   if a quiet track was detected as the wrong language), `--device cpu`.
4. **Check** the output: every speaker in `info.txt` appears; no long runs of repeated
   lines (Whisper hallucination); the detected language per track (printed) is right.
   Rerun with `--language` or a bigger model if not.
5. **Summarize** in `docs/meetings/<YYYY-MM-DD>-notes.md`: attendees, decisions (who decided),
   action items (owner), open questions. Link to the transcript; quote timestamps for each
   decision so they can be checked. Mark anything you inferred rather than heard.
   Decisions that change a row in CLAUDE.md section 2 must be confirmed with the user
   before editing CLAUDE.md.
6. **Post to Discord.** Preview first (prints the message, sends nothing):
   ```bash
   python -I .claude/skills/transcribe-meeting/scripts/post_discord.py docs/meetings/<date>-notes.md docs/meetings/<date>-transcript.md
   ```
   Show the user that preview and post only after they say yes in chat, by rerunning with
   `--send`. The whole team reads it, and the notes contain guesses (who's who, inferred
   decisions). The message is the "Decided" and "Action items" sections (max 2000 chars),
   with the notes and transcript attached; `@` mentions are disabled.
   The webhook URL is read from the `READCODE_DISCORD_WEBHOOK` environment variable. Never
   write it into the repo, a command line that gets logged, or the notes. If it's unset, ask
   the user to set it (Discord: channel settings > Integrations > Webhooks > New Webhook > Copy URL).
   On Windows, `setx` only reaches shells started afterwards; if the session doesn't see it, read
   it for one command from `[Environment]::GetEnvironmentVariable('READCODE_DISCORD_WEBHOOK','User')`.

## Notes

- Discord handles are not real names; ask the user to map them once (e.g. `chdany12` = Danny)
  and keep the mapping at the top of the notes file.
- Recordings are private meeting content: keep the zip out of the repo and do not upload audio anywhere.
