# Contributing to Bubu Desktop Buddy

Thanks for wanting to make Bubu better! This is a small, friendly codebase and
pull requests of all sizes are welcome.

## Getting started

```bash
git clone https://github.com/your-name/bubu-desktop-buddy.git
cd bubu-desktop-buddy
python -m pip install -r requirements.txt
python -m bubu            # run Bubu from source
```

## Where things live

| File | Responsibility |
|------|----------------|
| `bubu/buddy.py` | The window: movement, physics, input, speech bubbles, particles |
| `bubu/character.py` | All the drawing code for Bubu's body and expressions |
| `bubu/brain.py` | The state machine deciding what Bubu does next |
| `bubu/stats.py` | Hunger & mood simulation |
| `bubu/lines.py` | Everything Bubu can say (add new phrases here!) |
| `bubu/dialog.py` | Settings and About dialogs |
| `tools/generate_icon.py` | Regenerates the app icon with zero dependencies |

## Ideas for contributions

- New phrases in `bubu/lines.py` (keep them wholesome)
- New animations or moods in `character.py`
- Extra interactions (follow the cursor, fetch, minigames…)
- macOS support (Windows and Linux already work; autostart is platform-aware)
- Translations

## Guidelines

- Keep dependencies at zero (beyond PySide6).
- Match the existing code style; run `python -m bubu --smoke-test` before
  submitting — it starts the app, exercises pet/feed/jump/dance and exits 0.
- By contributing you agree your work is MIT licensed, same as the project.
