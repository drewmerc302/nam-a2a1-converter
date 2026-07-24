# NAM A2 → A1 Converter

Distill **NAM A2** captures into **A1** `.nam` files, for devices and plugins that
only accept A1 — like the **Valeton GP-5 / GP-50**.

A2 and A1 are different neural architectures; their weights don't transfer. So this
doesn't "downgrade" — it **distills**: render a standardized DI through the A2 model,
then train an A1 to reproduce that output.

```
A2.nam ──render DI──▶ teacher.wav ──train an A1 to match──▶ A1.nam ──▶ your A1-only device
```

Because the A2 teacher is deterministic and noise-free, the A1 copy is typically a
*tighter* match to the A2 than a real-amp capture is to its amp.

## Download

Grab the latest desktop build from **[Releases](https://github.com/drewmerc302/nam-a2a1-converter/releases)**:

- **macOS** — `nam-a2a1-converter-macos.dmg` (signed + notarized; opens clean).
- **Windows** — `nam-a2a1-converter-windows.zip` (unzip, run `nam-a2a1-converter.exe`).
  It's **unsigned**, so Windows SmartScreen will warn: click **More info → Run anyway**.
  Some antivirus may flag PyInstaller apps; it's a false positive.

Launch it, drop an A2 `.nam`, pick a quality preset, hit Convert. Output lands in
`~/NAM-A2A1-out/`. Load the resulting A1 `.nam` on your device (e.g. import into
Valeton Suite → it converts to a SnapTone and pushes to the pedal).

**First convert is slow on a stock machine** (no GPU → CPU training). A live progress
bar with an ETA shows how long it's got left; you can cancel anytime.

## Quality presets

| Preset | Epochs | Use |
|--------|--------|-----|
| Draft  | 20     | Quick preview — rough, sanity-check only. |
| Standard | 60   | The sweet spot. Faithful tone, sane runtime. **Default.** |
| Best   | 120    | Chasing the last few %. Diminishing returns, longer. |

## Run from source

```bash
python3 -m venv .venv
./.venv/bin/pip install -r requirements.txt
./.venv/bin/python -m nam_a2a1            # opens the web UI in your browser
```

Or headless / batch on the CLI:

```bash
# one file, end to end (render + train + transcode)
./.venv/bin/python -m nam_a2a1 render capture.nam refs/v3_0_0.wav /tmp/y.wav
./.venv/bin/python -m nam_a2a1 train  refs/v3_0_0.wav /tmp/y.wav /tmp/out --epochs 60 --format 0.5x
```

## How it works (one venv, no format juggling)

The whole pipeline runs on **NAM 0.13.0**. 0.13.0 loads A2 and trains A1, but exports
the 0.7.0 `.nam` format; A1-only devices want **0.5.x**. For a standard WaveNet the two
formats differ *only* in their config schema — the weight array is byte-identical — so
`nam_a2a1/pipeline/nam_transcode.py` reshapes the config in pure Python, no torch, no
retraining. That removed the second (0.12.2) environment the pipeline used to need.

## Build the installers yourself

```bash
pip install -r requirements.txt pyinstaller
pyinstaller --noconfirm build/nam-a2a1-converter.spec
# dist/nam-a2a1-converter/  → the frozen onedir app
```

CI (`.github/workflows/build-desktop.yml`) builds both platforms on a `v*` tag and
attaches them to the Release. macOS signing/notarization needs these repo secrets:
`MACOS_CERT_P12_BASE64`, `MACOS_CERT_PASSWORD`, `MACOS_KEYCHAIN_PASSWORD`,
`APPLE_TEAM_ID`, `APPLE_API_KEY_ID`, `APPLE_API_ISSUER_ID`, `APPLE_API_KEY_P8_BASE64`.
Without them the macOS build is produced unsigned. Windows is always unsigned.

## Credits

Built on [Neural Amp Modeler](https://github.com/sdatkinson/neural-amp-modeler) (MIT).
0.5.x-format insight from [`arturksd/NAM-A1-local-trainer`](https://github.com/arturksd/NAM-A1-local-trainer).
