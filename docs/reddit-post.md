**Title:** Free desktop app: convert NAM **A2** captures to **A1** (for the Valeton GP-5/GP-50 and other A1-only gear)

---

**TL;DR** — Many NAM capture providers have stopped providing NAM A1 files entirely, leaving owners of devices that convert NAM A1 to some proprietary format unable to use the most recent captures (like the Valeton GP-5/GP-50, Hotone Ampero, etc...). I made a free, no-setup desktop app that distills any A2 `.nam` into an A1 `.nam`. Drop a file, get a file. Windows + macOS + Linux.

**Edit:** Linux build is up as of v0.2.0 — someone asked, so I built it. x86_64, link below.

**Downloads (no Python, no setup):**

- macOS (signed + notarized, opens clean): https://github.com/drewmerc302/nam-a2a1-converter/releases/latest/download/nam-a2a1-converter-macos.dmg
- Windows (unzip + run): https://github.com/drewmerc302/nam-a2a1-converter/releases/latest/download/nam-a2a1-converter-windows.zip
- Linux x86_64 (extract + run): https://github.com/drewmerc302/nam-a2a1-converter/releases/latest/download/nam-a2a1-converter-linux-x86_64.tar.gz
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

1. Download + open. (macOS is notarized. Windows is unsigned — SmartScreen will warn; click *More info → Run anyway*. AV may false-positive on the PyInstaller build. Linux: extract the tarball and run `./nam-a2a1-converter/nam-a2a1-converter` from a terminal.)
2. Drop your A2 `.nam` — batches work, they convert one after another.
3. Pick a quality preset (Draft / Standard / Best), hit **Convert**. Live progress bar + ETA, cancel anytime.
4. Load the A1 `.nam` on your device. For Valeton: import into Valeton Suite → it makes a SnapTone → push to the pedal.

**Notes**

- Free and open source. Runs 100% on your machine — nothing is uploaded.
- First convert is slowest on a machine with no GPU (CPU training — a few minutes at Standard).
- **macOS is tested end-to-end.** The **Windows** and **Linux** builds compile and pass an automated import check in CI, but I don't own either machine — so **nobody has run an actual conversion on them yet.** If you're on Windows or Linux, consider yourself a tester: it *should* work, but please report back or open an issue if it doesn't.
- **Linux** is x86_64, built against glibc 2.35 — Ubuntu 22.04+, Debian 12+, Mint 21+, Pop!_OS 22.04+, Fedora 36+, Arch, openSUSE 15.5+. **Nothing to install:** Tcl/Tk and the X11 libs are bundled, so glibc is the only thing it needs from your system. Older distro or ARM → run it from source (`pip install -r requirements.txt`), same app.

Questions/bugs → drop them here or open an issue on the repo. Enjoy.
