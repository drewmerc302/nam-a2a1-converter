**TL;DR** — Lots of NAM capture providers have stopped releasing A1 files, which strands anyone whose gear only converts A1 into its own proprietary format (Valeton GP-5 / GP-50 / GP-150, Hotone Ampero, etc.). I made a free, no-setup desktop app that distills any A2 `.nam` into an A1 `.nam`. Drop a file, get a file. Windows + macOS + Linux.

**Downloads** — no Python, no setup:

- **macOS** (signed + notarized — drag to Applications, opens clean): https://github.com/drewmerc302/nam-a2a1-converter/releases/latest/download/nam-a2a1-converter-macos.dmg
- **Windows** (unzip + run): https://github.com/drewmerc302/nam-a2a1-converter/releases/latest/download/nam-a2a1-converter-windows.zip
- **Linux x86_64** (extract + run): https://github.com/drewmerc302/nam-a2a1-converter/releases/latest/download/nam-a2a1-converter-linux-x86_64.tar.gz
- **Windows or Linux + NVIDIA** (much faster, multi-part download): https://github.com/drewmerc302/nam-a2a1-converter#gpu-acceleration
- Source + all releases: https://github.com/drewmerc302/nam-a2a1-converter

---

**Why this isn't just a file conversion**

A2 and A1 are different neural architectures — the weights don't transfer, so you can't "downgrade" an A2. Instead this **distills**: it plays the standardized NAM DI through the A2 model to capture its exact output, then trains a fresh A1 to reproduce that output.

```
A2.nam ──render DI──▶ teacher.wav ──train an A1 to match──▶ A1.nam
```

The A2 teacher is deterministic and noise-free, so the resulting A1 usually matches the A2 *tighter* than a real-amp capture matches its amp — validation ESR typically lands ~0.005–0.02.

**Using it**

1. Download and open — it opens a converter page in your browser.
2. Drop your A2 `.nam` files. Batches work; they convert one after another.
3. Pick a quality preset — **Draft** (20 epochs, rough preview), **Standard** (60, the default and the sweet spot), **Best** (120, diminishing returns).
4. Hit Convert. Live progress bar + ETA, cancel anytime.
5. Load the A1 `.nam` on your device. For Valeton: import into Valeton Suite → it makes a SnapTone → push to the pedal.

**Leave the output format on 0.5.x.** That's the default and it's what A1-only gear wants. The 0.7.0 option exists for newer NAM plugins, and **Valeton Suite cannot import it** — it sits on "importing…" for about two minutes and then times out, which is a miserable way to find out after a full training run.

**Speed**

- **M-series Macs already use the GPU** via Metal. Nothing to install, nothing to opt into, no separate download.
- **NVIDIA on Windows or Linux:** there's a separate CUDA build — same app, compiled against CUDA instead of CPU-only PyTorch. It's a separate download because it's several GB rather than a few hundred MB, and it ships in numbered parts because GitHub caps a release file at 2 GB (rejoin with `copy /b` on Windows or `cat *.0* > file` on Linux — no extra software, and there's a PowerShell script that does it for you). The Linux CUDA build runs on exactly the same distros as the standard one; all it needs from you is the driver.
- **The standard build tells you if this applies to you** — it checks your GPU at launch and shows a banner if it finds an NVIDIA card it can't use. No banner means you're already as fast as this tool gets.
- **On CPU it's slow, and how slow depends a lot on the CPU.** A recent desktop chip does Standard in a few minutes; a 2012-era i7-3770 took ~40 minutes at *Draft*. The ETA is also optimistic at first — it extrapolates from finished epochs and the early ones run faster than the later ones.
- AMD and Intel GPUs aren't supported for training. CPU only there.

**Notes**

- Free and open source. Runs 100% on your machine — nothing is uploaded.
- macOS, Windows and Linux have all had real conversions run on them by people who reported back, with output confirmed running on a Valeton GP-150. The CUDA builds are newer and less travelled — if you're on one and something looks wrong, please open an issue.
- **Windows is unsigned**, so SmartScreen warns: **More info → Run anyway**. Some antivirus flags PyInstaller apps — false positive.
- **Linux** is x86_64 built against glibc 2.35: Ubuntu 22.04+, Debian 12+, Mint 21+, Pop!\_OS 22.04+, Fedora 36+, Arch, openSUSE 15.5+. Tcl/Tk and the X11 libs are bundled, so glibc is the only thing it needs from your system. Older distro or ARM → run it from source, same app.
- If you tried an earlier build and got **`ValueError: Output clipped.`** on some captures but not others, that's fixed as of v0.4.2. Nothing was wrong with your file — it was just a loud capture, and the trainer refuses any target that hits full scale. Grab the current build.

Questions/bugs → drop them here or open an issue on the repo. Enjoy.
