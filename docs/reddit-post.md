**Title:** Free desktop app: convert NAM **A2** captures to **A1** (for the Valeton GP-5/GP-50 and other A1-only gear)

---

**TL;DR** — A2-only NAM captures won't load on devices that only accept A1 (like the Valeton GP-5/GP-50). I made a free, no-setup desktop app that distills any A2 `.nam` into an A1 `.nam`. Drop a file, get a file. Windows + macOS.

**Downloads (no Python, no setup):**

- macOS (signed + notarized, opens clean): https://github.com/drewmerc302/nam-a2a1-converter/releases/latest/download/nam-a2a1-converter-macos.dmg
- Windows (unzip + run): https://github.com/drewmerc302/nam-a2a1-converter/releases/latest/download/nam-a2a1-converter-windows.zip
- Source + all releases: https://github.com/drewmerc302/nam-a2a1-converter

---

**The problem**

A2 and A1 are different neural-net architectures — you can't just "downgrade" an A2 to A1, the weights don't transfer. So a lot of great A2 captures are dead weight on A1-only hardware.

**What it actually does**

Instead of converting weights, it **distills**. It plays the standardized NAM DI through the A2 model to capture its exact output, then trains a fresh A1 to reproduce that output. The A2 teacher is deterministic and noise-free, so the resulting A1 usually matches the A2 *tighter* than a real-amp capture matches its amp — validation ESR typically lands ~0.005–0.02.

```
A2.nam ──render DI──▶ teacher.wav ──train an A1 to match──▶ A1.nam
```

**How to use it**

1. Download + open. (macOS is notarized. Windows is unsigned — SmartScreen will warn; click *More info → Run anyway*. AV may false-positive on the PyInstaller build.)
2. Drop your A2 `.nam` — batches work, they convert one after another.
3. Pick a quality preset (Draft / Standard / Best), hit **Convert**. Live progress bar + ETA, cancel anytime.
4. Load the A1 `.nam` on your device. For Valeton: import into Valeton Suite → it makes a SnapTone → push to the pedal.

**Notes**

- Free and open source. Runs 100% on your machine — nothing is uploaded.
- First convert is slowest on a machine with no GPU (CPU training — a few minutes at Standard).
- I tested macOS thoroughly. Windows builds and passes an import smoke-test in CI, but I don't own a Windows box — **testers and feedback very welcome.**

Questions/bugs → drop them here or open an issue on the repo. Enjoy.
