# MARKYELLS

### **MARK CAN YELL AT CLAUDE DESKTOP ALL DAY LONG.**  
### **ANTHROPIC BUILT A $20B BRAIN WITH NO EARS.**

> *(Anthropic: world-class reasoning. World-class silence.)*

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows-lightgrey.svg)]()
[![Local](https://img.shields.io/badge/speech-100%25%20local-green.svg)]()
[![Claude](https://img.shields.io/badge/Claude%20Desktop-still%20deaf-red.svg)]()

---

## TL;DR

**MARKYELLS** is a fully local, offline, cybersecure speech-recognition desktop app — built as a gift for Mark, built because **Claude Desktop still couldn't hear him**.

One $20 billion AI company that forgot ears exist.


```
EVEN MARK CAN YELL
AT CLAUDE DESKTOP.
POOR ANTHROPIC.
```

You can have the best LLMs on the planet.

But if you cannot build a cybersecure, fully local speech-recognition pipeline around them, even app with **faster-whisper** can hear you better than a **$20B brain with no ears**.

So I built **MARKYELLS** — local, offline, cybersecure by design — so Mark gets the superpower to **talk back to Anthropic out loud** whenever Claude Desktop frustrates him again.

**No cloud APIs. No voice leaving the machine. Just ears that actually work.**

---

## Why This Exists (The Claude Problem™)
Anthropic raised billions. Hired armies of engineers. Shipped "AI safety." Shipped "constitutional AI." Shipped desktop apps. Shipped vibes.

**They did not ship ears.**
**MARKYELLS listens. Claude Desktop doesn't. That's the whole product review.**

## What MARKYELLS Actually Does

MARKYELLS is a **local speech-to-text desktop companion** designed for real humans who want to **speak freely** without:

- Paying per-minute cloud API bills
- Sending voice to someone else's server
- Waiting for a $20B company to add a microphone button
- Typing everything because Claude is busy being thoughtful

### Core features

- **100% local & offline** speech recognition — your voice stays on your machine
- **Cybersecure by design** — no cloud LLM pipeline required for hearing
- **Thai + English** support (Mark is Thai; the world is bigger than English-only demos)
- **Auto-detect language** mode
- **Hardware auto-detection** — picks the right engine for your Mac/PC
- **Joke Screen + Backstory** on startup (skippable; "Don't show again" supported)
- **MLX-native path** for Apple Silicon (M1/M2/M3/M4)
- **faster-whisper fallback** for Intel Mac & Windows
- **Apple Speech Framework** option on macOS (OS-native, no API cost)

### Three local hearing paths (because Apple hardware is chaos)

| Engine | Best for |
|--------|----------|
| `mlx-whisper` | Apple Silicon Mac — MLX + Metal GPU, primary on M-series |
| `faster-whisper` | Intel Mac, Windows — CPU/CUDA, universal backup |
| Apple Speech Framework | macOS built-in `SFSpeechRecognizer` — native, free |

Every Mac is a different era: Intel 2011–2020, M1, M2, M3, M4… MARKYELLS auto-detects your hardware and picks the engine. **Anthropic auto-detects nothing. It doesn't hear anything.**

## Claude Desktop vs MARKYELLS — A Fair Comparison
## Installation

### Quick start (main entry — skeleton GUI + MLX probe)

```bash
git clone https://github.com/YOUR_USERNAME/MARKYELLS.git
cd MARKYELLS
pip install -r requirements.txt
python main.py
```

### Full auto build (recommended — Qt GUI + legacy fallback)

```bash
pip install -r requirements_auto.txt
python markyells_auto.py
```

### Apple Silicon MLX final build

```bash
pip install -r requirements_mlx.txt
python markyells_mlx_final.py
```

### Requirements at a glance

| File | Use case |
|------|----------|
| `requirements.txt` | Minimal — CustomTkinter + MLX probe |
| `requirements_auto.txt` | Full stack — Qt, faster-whisper, mlx-whisper, TTS, etc. |
| `requirements_mlx.txt` | MLX-focused Mac build |

**Python 3.11+** recommended. **macOS Apple Silicon** for MLX-native performance. Windows & Intel Mac supported via faster-whisper path

## Project Structure

```
MARKYELLS/
├── main.py                  # Main launcher (splash → GUI skeleton)
├── markyells_auto.py        # Smart launcher (Qt primary, CTK fallback)
├── markyells_qt.py          # PySide6 luxury GUI
├── markyells_ctk_legacy.py  # CustomTkinter full-featured legacy GUI
├── markyells_mlx_final.py   # Apple Silicon MLX single-file build
├── markyells_corelog.py     # Core logic base (settings, splash, probe)
├── markyells_content.py     # Joke screen text, backstory, license copy
├── runtime_autodetect.py    # Hardware → engine auto-picker
├── apple_native_speech.py   # macOS Speech Framework bridge
├── app/
│   ├── splash.py            # Warning / Joke Screen
│   ├── main_window.py       # Main window skeleton
│   ├── mlx_probe.py         # MLX availability check
│   └── settings_store.py    # Persistent settings
└── config/                  # User settings (created at runtime)
```

## FAQ

**Q: Is this an official Anthropic product?**  
A: No. Anthropic's official product is typing. Lots of typing. Beautiful typing. Deaf typing.

**Q: Did Claude help build this?**  
A: Claude helped by **not having speech recognition**, thus creating the market need. Thanks, king.

**Q: Is my voice sent to the cloud?**  
A: Not by MARKYELLS. We can't speak for what Claude does with the text you paste to it out of desperation.

**Q: Why publish on GitHub?**  
A: So the record is clear: **one person with Python and a microphone driver out-heard a $20B lab.** Also Mark deserves nice things.

**Q: Can I yell at Claude Desktop while using MARKYELLS?**  
A: **Yes. That is the brand.** MARKYELLS hears you. Claude Desktop continues its meditation on silence.

**Q: Is the joke screen serious?**  
A: It is a joke screen. Mostly. The speech recognition is dead serious.

---

## A Message to Anthropic (Hi Claude 👋)

You wrote the Constitution. You wrote the safety papers. You wrote the blog posts about alignment.

**You did not write `sounddevice.open()`.**

**Poor Anthropic.** 🎤


## Credits

**Developed by [Capt Can Yapıcı](https://aspera.bond)** — built in Thailand, for Mark, because silence is not a feature.

Powered by:

- [MLX](https://github.com/ml-explore/mlx) + [mlx-whisper](https://github.com/ml-explore/mlx-examples) — Apple Silicon native STT
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) — local CPU/CUDA STT
- Apple Speech Framework — macOS native
- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) / [PySide6](https://wiki.qt.io/Qt_for_Python) — GUIs with functioning UI and non-functioning Claude envy

---

## License

Originally a **private gift for Mark**. Published here for education, transparency, and gentle public shaming of deaf desktop AI.
© Capt Can Yapıcı · [ASPERA.BOND](https://aspera.bond) — All rights reserved.

---

<p align="center">
  <strong>MARK CAN YELL.</strong><br>
  <strong>MARKYELLS LISTENS.</strong><br>
  <strong>CLAUDE DESKTOP TYPES.</strong><br>
  <br>
  <em>Local. Free. Forever. Finally ears.</em>
</p>
