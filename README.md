# ScoreForge (COMPLETLEY VIBE CODED)

ScoreForge is a full-stack web application that converts short audio clips into engraved sheet music. Upload MP3, WAV, M4A, or FLAC files, pick a clef, and receive a downloadable PDF score alongside MusicXML and MIDI exports. I'm testing vibe coding with this.

## Features

- 🎧 Audio ingestion with size and duration limits (20 MB / 5 minutes)
- 🤖 Automatic transcription using Spotify's Basic Pitch (with graceful fallbacks)
- 🎼 Music engraving with configurable clefs, quantization, and tempo overrides
- 📄 Downloadable PDF, MusicXML, and MIDI artifacts served directly from the API
- 🖥️ Single-page Next.js interface with drag-and-drop uploading, progress tracking, and results summary
- 🧹 Background worker queue with automatic cleanup after 30 minutes

## Repository structure

```
backend/   FastAPI application, transcription pipeline, tests
frontend/  Next.js + Tailwind single-page interface
examples/  Example output artifacts
models/    Cached transcription models (gitignored)
scripts/   Developer tooling
```

## Prerequisites

- Node.js 18+ and npm
- Python 3.10+
- libsndfile and ffmpeg (required when using optional `librosa` for MP3/M4A support)
- Optional: [`librosa`](https://librosa.org/) for extended audio format support
- Optional engravers: [LilyPond](https://lilypond.org/) or [MuseScore CLI](https://musescore.org/en/handbook/3/command-line-options)
- Optional transcription enhancements: `tensorflow` for accelerated Basic Pitch inference

### Ubuntu 22.04 quick start

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-dev build-essential libsndfile1 ffmpeg nodejs npm lilypond
# Optional: MuseScore 4 CLI via AppImage or PPA
```

### Windows 11 quick start

1. Install [Python 3.11](https://www.python.org/downloads/windows/) and ensure it is added to PATH.
2. Install [Node.js 18 LTS](https://nodejs.org/en/download/).
3. Install [LilyPond](https://lilypond.org/download.html) or MuseScore 4 (ensure `MuseScore4.exe` is available via the CLI).
4. Install [libsndfile binaries](https://github.com/erikd/libsndfile/releases) (required by `soundfile`).
5. If using PowerShell, run `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned` to allow the setup scripts.

## Setup

The Makefile automates common tasks. Run the following from the repository root:

```bash
make setup
```

This installs backend dependencies into `backend/.venv` (via `uv` when available) and runs `npm install` inside `frontend/`.

If you prefer manual steps:

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate  # or .venv\\Scripts\\activate on Windows
pip install -r requirements.txt
# Optional transcription extras
# pip install basic-pitch tensorflow-cpu

cd ../frontend
npm install
```

Copy the example environment files if you want to customise configuration:

```bash
cp backend/.env.example backend/.env
cp frontend/.env.local.example frontend/.env.local
```

Adjust the following environment variables as needed:

- `BACKEND_STORAGE_DIR` – directory for uploads and generated artifacts
- `ENGRAVER` – `lilypond`, `musescore`, or `placeholder`
- `ENGRAVER_PATH` – explicit path to the CLI (e.g. `/usr/bin/lilypond` or `"C:\Program Files\MuseScore 4\bin\MuseScore4.exe"`)
- `NEXT_PUBLIC_API_BASE_URL` – frontend base URL for API calls (defaults to `http://localhost:8000/api`)

## Running the app

Terminal 1 (backend):

```bash
make run-backend
```

Terminal 2 (frontend):

```bash
make run-frontend
```

The UI is served at `http://localhost:3000` and communicates with the backend at `http://localhost:8000`.

## Testing & linting

Back-end unit tests focus on the transcription pipeline. Run them with:

```bash
make test-backend
```

Frontend linting uses Next.js defaults:

```bash
make lint-frontend
```

These commands are also executed in CI to ensure regressions are caught early.

## Transcription pipeline overview

1. **Normalisation** – audio is converted to mono 44.1kHz WAV via `librosa`.
2. **Transcription** – Basic Pitch is attempted; on failure the pipeline falls back to bundled MIDI templates (sufficient for tests).
3. **Quantisation** – `pretty_midi` tightens note starts/ends according to the selected grid.
4. **Score assembly** – `music21` sets clef, key/time signatures, tempo, and writes MusicXML.
5. **Engraving** – LilyPond or MuseScore CLI converts MusicXML to PDF. A placeholder engraver (ReportLab) is used when neither is available.
6. **Artifacts** – MIDI, MusicXML, and PDF files are stored in `<storage_dir>/<job_id>/` and served via `/results/{job_id}/`.

Jobs remain downloadable for 30 minutes. Cleanup runs on each status request.

## Example artifacts

See [`examples/`](examples/) for a sample transcription bundle. The MIDI example is provided as
[`simple_melody_midi.json`](examples/simple_melody_midi.json), a text description you can rebuild
with `pretty_midi` to avoid committing binary assets while keeping the melody reproducible.

## Troubleshooting

- **Basic Pitch model downloads** – the first run may download model weights to `~/.cache/basic_pitch`. Adjust `BASIC_PITCH_MODEL` if you want to pin a location.
- **Engraver errors** – set `ENGRAVER=placeholder` during development if LilyPond/MuseScore are not installed.
- **FFmpeg/libsndfile missing** – installation errors from `librosa` or `soundfile` usually indicate missing system libraries (see prerequisites above).

## Contributing

1. Create a branch from `main` (e.g. `codex/audio-to-score-site`).
2. Commit logically grouped changes with descriptive messages.
3. Run `make test-backend` and `make lint-frontend` before opening a PR.
4. Attach screenshots of UI changes (see `/examples/ui` for references).

Happy transcribing!
