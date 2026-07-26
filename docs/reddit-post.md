**Title:** Free desktop app: convert NAM **A2** captures to **A1** (for the Valeton GP-5/GP-50 and other A1-only gear)

---

**TL;DR** — Many NAM capture providers have stopped providing NAM A1 files entirely, leaving owners of devices that convert NAM A1 to some proprietary format unable to use the most recent captures (like the Valeton GP-5/GP-50, Hotone Ampero, etc...). I made a free, no-setup desktop app that distills any A2 `.nam` into an A1 `.nam`. Drop a file, get a file. Windows + macOS + Linux.

**Edit:** Linux build is up as of v0.2.0 — someone asked, so I built it. x86_64, link below.

**EDIT 2 (v0.3.0) — GPU acceleration, and a Windows launch crash is fixed:**

- **Apple silicon (M1/M2/M3/M4) already got this for free.** The macOS build trains on the GPU via Metal (MPS) and always has — you don't need to download anything, change a setting, or opt in. If you're on an M-series Mac you are already on the fast path.
- **NVIDIA on Windows:** there's now a **separate CUDA build**. Same app, compiled against CUDA instead of CPU-only PyTorch. Converts that took ~40 minutes on CPU drop to a small fraction of that. It's a separate download because it's ~2.6 GB versus ~350 MB, and Mac/AMD/Intel machines can't use any of it.
- **You don't have to guess whether it applies to you.** The standard build now detects your GPU on launch. If it finds an NVIDIA card it can't use, it shows a banner linking to the CUDA build. No banner = you're already as fast as this tool gets.
- GitHub caps a single release file at 2 GB, so the CUDA build ships as two parts. Run the included `get-cuda-build.ps1` and it fetches, checksums, and reassembles them for you — or rejoin them by hand with `copy /b`, no extra software needed. Instructions on the repo.
- **Windows launch crash fixed.** If you double-clicked the .exe and it flashed and vanished, that was a real bug, not your machine: the windowed build starts with no stdout, and PyTorch's web server died configuring its logger before it could even open a port. Launching via PowerShell with `| Out-Host` worked around it by handing the process a real output pipe. **v0.3.0 fixes the cause — no wrapper script needed.** Thanks to the person who reported it.
- AMD/Intel GPUs aren't supported for training — CPU only there for now.

**Downloads (no Python, no setup):**

- macOS (signed + notarized, opens clean): https://github.com/drewmerc302/nam-a2a1-converter/releases/latest/download/nam-a2a1-converter-macos.dmg
- Windows (unzip + run): https://github.com/drewmerc302/nam-a2a1-converter/releases/latest/download/nam-a2a1-converter-windows.zip
- Windows + NVIDIA GPU (much faster, ~2.6 GB, ships as 2 parts — see the repo's *Faster training on an NVIDIA GPU* section): https://github.com/drewmerc302/nam-a2a1-converter#faster-training-on-an-nvidia-gpu-windows
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
- Runtimes depend heavily on whether training lands on a GPU. **M-series Macs use theirs automatically (Metal/MPS) — nothing to install.** On Windows, the CUDA build is what gets you off the CPU; the standard build will tell you if that applies to your machine.
- **macOS is tested end-to-end, and Windows has now had a real conversion run on it** by someone who reported back (~40 min at Standard on CPU). **Linux** compiles and passes an automated check in CI, but I don't own a Linux box — so if you're on Linux, consider yourself a tester and please open an issue if something breaks.
- **Linux** is x86_64, built against glibc 2.35 — Ubuntu 22.04+, Debian 12+, Mint 21+, Pop!_OS 22.04+, Fedora 36+, Arch, openSUSE 15.5+. **Nothing to install:** Tcl/Tk and the X11 libs are bundled, so glibc is the only thing it needs from your system. Older distro or ARM → run it from source (`pip install -r requirements.txt`), same app.

Questions/bugs → drop them here or open an issue on the repo. Enjoy.
