# Reply — Linux Mint tester, RTX 3060 (2026-07-28)

Reply to the user who reported the CUDA link going nowhere on Linux, ran a Draft
convert on an i7-3770, and got it into a Valeton GP-150.

Shipped in v0.4.0. Everything below is confirmed against the built artifacts, not
planned — the Linux CUDA leg builds clean, freezes real cu126 torch, holds the glibc
2.35 floor, and packages to 3,564 MiB across three parts.

---

Thanks for this — and you found a real bug. It's fixed, along with the Linux GPU
support you asked for. Both are in **v0.4.0**, up now.

**The CUDA link.** Not a stale link, though I completely see why it looked like one:
the banner had no idea what OS it was running on. It checks "is there an NVIDIA card
here?" and "can this build use it?" — and if that's yes/no it shows the link, on any
platform. There was no Linux CUDA build for it to point *at*, so it dumped you on the
release page where the only Linux file was the CPU build you already had. Entirely my
fault. It's platform-aware now.

Related: nothing in the app displayed its own version, which is why you couldn't tell
what you were running. (You were on v0.3.0 — v0.2.0 had no GPU detection at all, so the
banner you saw could only have come from the newer build.) v0.4.0 shows the version in
the header, so this is never ambiguous again.

**Linux GPU support: shipped.** `nam-a2a1-converter-linux-x86_64-cuda.tar.gz`, on the
v0.4.0 release. Same app, compiled against CUDA instead of CPU-only PyTorch.

It's ~3.5 GB, and GitHub caps a single release file at 2 GB, so it arrives as three
numbered parts. Rejoining needs nothing you don't already have:

```bash
cat nam-a2a1-converter-linux-x86_64-cuda.tar.gz.0* > nam-a2a1-converter-linux-x86_64-cuda.tar.gz
sha256sum -c --ignore-missing nam-a2a1-converter-linux-x86_64-cuda.tar.gz.sha256
tar -xzf nam-a2a1-converter-linux-x86_64-cuda.tar.gz
./nam-a2a1-converter/nam-a2a1-converter
```

The glob orders the parts correctly — they're numbered `.001`, `.002`, `.003`, so plain
lexical sort is the right order. **It runs on the same distros the CPU build does** —
Mint 22 included — so it needs nothing extra from your system beyond the NVIDIA driver
you already have (`nvidia-smi` printing your card is the whole requirement). The CUDA
toolkit itself is inside the bundle; there's nothing to `apt install`.

**If you'd rather not pull 3.5 GB**, CUDA on Linux also works from source, and it's a
much smaller download:

```bash
git clone https://github.com/drewmerc302/nam-a2a1-converter
cd nam-a2a1-converter
python3 -m venv .venv
./.venv/bin/pip install torch --index-url https://download.pytorch.org/whl/cu126
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python -m nam_a2a1
```

Same app, same UI. Either route, on a 3060 that ~40-minute Draft convert should come
down to a couple of minutes, and Standard and Best become actually practical.

**On the ETA** — it's honest, but optimistic early. It extrapolates from completed
epochs, and the first epochs run faster than the later ones, so the opening number is
always low and drifts up as it goes. What I *have* fixed is the README, which claimed
CPU training takes "a few minutes at Standard" — that was written from a modern desktop
CPU and is nonsense on a 3770. It now says runtime depends heavily on the CPU and uses
your ~40 minutes at Draft as the slow-end data point.

**What I'd love tested**, since you're offering and you're the only person I know
running this on Linux:

1. **The CUDA build — does training actually land on the GPU?** The convert should be
   dramatically faster, and the GPU banner should stop appearing. If it's still slow,
   it silently fell back to CPU and I want to know.
2. **Standard (60 epochs), not just Draft.** Draft is genuinely rough — it's a
   sanity-check preset. I'd like to know a real one imports and sounds right on the 150.
3. **A batch** — drop 3 or 4 files at once and let it work through them.
4. **Both output formats** (A1 0.5.x and A1 0.7.0), if the GP-150 will take either.

And the GP-150 result is genuinely useful on its own — I built this against GP-5 and
GP-50 reports and had no idea whether the 150 ate the same files. It's in the README
now.

Thanks again for the detail. "The link points at the wrong thing" reports are the ones
that actually get fixed.
