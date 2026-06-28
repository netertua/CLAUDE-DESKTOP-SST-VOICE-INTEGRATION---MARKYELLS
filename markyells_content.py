"""MARKYELLS — shared content (English only). Private gift for Mark."""

JOKE_HEADLINE = (
    "MARK CAN YELL AT CLAUDE DESKTOP\n"
    "ALL DAY LONG.\n"
    "ANTHROPIC BUILT A $20B BRAIN\n"
    "WITH NO EARS."
)

JOKE_SUBTITLE = "(Anthropic: world-class reasoning. World-class silence.)"

JOKE_BODY = """You can have the best LLMs on the planet.

But if you cannot build a cybersecure, fully local speech-recognition pipeline around them,
even a rough chat app with faster-whisper can hear you better than a $20B brain with no ears.

So I built MARKYELLS — local, offline, cybersecure by design —
so Mark gets the superpower to talk back to Anthropic out loud
whenever Claude Desktop frustrates him again.

No cloud APIs. No voice leaving the machine. Just ears that actually work."""

JOKE_TAB_TEXT = f"{JOKE_HEADLINE}\n\n{JOKE_SUBTITLE}\n\n{JOKE_BODY}"

BACKSTORY_TEXT = """Developed by Capt Can Yapıcı.

So I built this speech recognizer as a gift for him — so my brilliant, lonely-but-quality friend would always have an infinite listener. Someone who never gets tired. Someone who actually hears him.

And yes: Claude Desktop still had no speech recognition. Everyone was complaining. Poor Anthropic. A whole company, all that money, all those engineers — and still no speech rec on desktop.

So I thought: fine. If they won't build it, I will. Even from Thailand. Even on my own. Even I can build a speech recognizer — and I did.

This is MARKYELLS. A personal gift for Mark. Not for the public. Not open source.

Speak freely. Someone's finally listening."""

CORELOGIC_FOR_CURIOUS = """Corelogic for Curious

Why local? Because on Apple, everything is expensive. Cloud APIs, subscriptions, per-minute billing — it adds up fast. Mark deserved better than a meter running while he talks.

So we built MARKYELLS around fully local, offline speech recognition. No surprise bills. No paid API calls. Your voice stays on your machine.

Cybersecure speech pipeline (local only):
  · Audio captured and transcribed on your machine — not sent to cloud LLM APIs
  · No subscription meter running while you talk
  · Best LLMs are useless for voice if they never built the hearing layer — faster-whisper class local engines do

Three local paths on Mac — not just one:
  · mlx-whisper        → Apple Silicon native (MLX + Metal GPU) — primary on M-series Macs
  · faster-whisper     → Intel Mac + fallback (100% local CPU/CUDA)
  · Apple Speech Framework → macOS built-in SFSpeechRecognizer (desktop & laptop, no API cost)

MLX is NOT only faster-whisper. On Mark's Mac, mlx-whisper runs first. Apple Speech Framework is the OS-native option (like Windows uses faster-whisper locally). faster-whisper is the universal backup.

Mark is Thai — so we built dual language support:
  · Thai speech recognition  (ภาษาไทย)
  · English speech recognition
  · Auto-detect mode for both

The hard part: every Apple Mac is different.
  · Intel Macs from 2011–2020
  · M1, M2, M3, M4 — each a different chip, different memory, different era
  · Past, present, and future MLX platforms

So we wrote a custom Python auto-detect module. It reads your exact hardware and picks the right local engine automatically.

With this tech, MARK CAN SPEAK TO ALL MLX PLATFORMS — past, present, and future — in Thai or English.

I gave my friend this special superpower and I am genuinely happy about it.

Local. Free. Forever. Private gift only."""

LICENSE_TEXT = """LICENSE INFORMATION

MARKYELLS is a private, personal gift.
This is NOT an open source project.

This tool is proprietary software created exclusively as a gift for Mark.
It is not intended for public distribution, resale, or commercial use.

Unauthorized copying, redistribution, reverse engineering, or modification
of this software is strictly prohibited.

Protected under English law.
Provided by ASPERA.BOND

© Capt Can Yapıcı · ASPERA.BOND
All rights reserved."""