from __future__ import annotations

import asyncio
import subprocess
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np
import soundfile as sf

from ..config import settings
from ..models import ClefChoice, Job, JobMeta, QuantizationGrid

try:  # pragma: no cover - optional dependency
    import librosa  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    librosa = None


@dataclass
class PipelineOptions:
    sample_rate: int = 44100
    mono: bool = True


@dataclass
class PipelineDependencies:
    engraver: Optional["BaseEngraver"] = None
    transcriber: Optional["BaseTranscriber"] = None
    quantizer: Optional["MidiQuantizer"] = None
    metadata_builder: Optional["MetadataBuilder"] = None


class PipelineError(RuntimeError):
    """Raised when the pipeline fails."""


async def run_pipeline(job: Job, deps: PipelineDependencies | None = None, options: PipelineOptions | None = None) -> None:
    deps = deps or PipelineDependencies()
    options = options or PipelineOptions()

    workdir = job.workdir
    if workdir is None:
        raise PipelineError("Job workdir not initialised")

    raw_audio_path = workdir / "input.wav"
    midi_path = workdir / "transcription.mid"
    musicxml_path = workdir / "score.musicxml"
    pdf_path = workdir / "score.pdf"

    job.progress = 10
    audio_info = await _normalise_audio(job, raw_audio_path, options)

    job.progress = 30
    quantizer = deps.quantizer or MidiQuantizer()
    transcriber = deps.transcriber or load_transcriber()
    try:
        await transcriber.transcribe(raw_audio_path, midi_path, job, audio_info)
    except PipelineError:
        if not isinstance(transcriber, StubTranscriber):
            fallback = StubTranscriber(_default_stub_midi())
            await fallback.transcribe(raw_audio_path, midi_path, job, audio_info)
            transcriber = fallback
        else:
            raise

    job.progress = 60
    quantized_midi_path = workdir / "quantized.mid"
    quantizer.quantize(midi_path, quantized_midi_path, job)

    job.progress = 75
    metadata_builder = deps.metadata_builder or MetadataBuilder()
    musicxml_path = metadata_builder.build_musicxml(quantized_midi_path, musicxml_path, job)
    job.meta = metadata_builder.meta

    job.progress = 90
    engraver = deps.engraver or load_engraver()
    engraver.engrave(musicxml_path, pdf_path)

    job.artifacts = {
        "midi": quantized_midi_path,
        "musicxml": musicxml_path,
        "pdf": pdf_path,
    }


async def _normalise_audio(job: Job, output_path: Path, options: PipelineOptions) -> dict:
    if job.workdir is None:
        raise PipelineError("Job workdir missing")

    candidates = sorted(job.workdir.glob("upload*"))
    if not candidates:
        raise PipelineError("Uploaded audio missing")
    source = candidates[0]
    audio_data, sr = _load_audio_array(source)
    if audio_data.size == 0:
        raise PipelineError("Uploaded file appears to be empty")
    if isinstance(audio_data, np.ndarray) and audio_data.ndim > 1 and options.mono:
        audio_data = np.mean(audio_data, axis=0)
    target_sr = options.sample_rate
    if sr != target_sr:
        if librosa:
            audio_data = librosa.resample(audio_data, orig_sr=sr, target_sr=target_sr)
        else:
            duration = audio_data.shape[-1] / sr
            target_length = int(duration * target_sr)
            if target_length <= 0:
                raise PipelineError("Unable to resample audio: invalid duration")
            indices = np.linspace(0, audio_data.shape[-1] - 1, num=target_length)
            if audio_data.ndim == 1:
                audio_data = np.interp(indices, np.arange(audio_data.shape[-1]), audio_data)
            else:
                audio_data = np.vstack(
                    [np.interp(indices, np.arange(channel.shape[-1]), channel) for channel in audio_data]
                )
        sr = target_sr
    peak = np.max(np.abs(audio_data))
    if peak < 1e-4:
        raise PipelineError("Uploaded audio appears to be silent")
    audio_to_write = audio_data
    if isinstance(audio_data, np.ndarray) and audio_data.ndim > 1:
        audio_to_write = np.moveaxis(audio_data, 0, -1)
    sf.write(output_path, audio_to_write.astype(np.float32), sr)
    duration = audio_data.shape[-1] / sr
    return {"duration": float(duration), "sample_rate": sr, "source_path": source}


def _load_audio_array(source: Path) -> tuple[np.ndarray, int]:
    suffix = source.suffix.lower()
    prefer_librosa = suffix in {".mp3", ".m4a", ".aac"}
    last_error: Exception | None = None

    if not prefer_librosa:
        try:
            audio_data, sr = sf.read(source, always_2d=False)
            if isinstance(audio_data, np.ndarray) and audio_data.ndim == 2:
                audio_data = audio_data.T
            return np.asarray(audio_data), int(sr)
        except Exception as exc:
            last_error = exc
            prefer_librosa = librosa is not None

    if librosa is not None and prefer_librosa:
        try:
            audio_data, sr = librosa.load(source, sr=None, mono=False)
            return np.asarray(audio_data), int(sr)
        except Exception as exc:
            last_error = exc

    message = "Failed to decode audio"
    if librosa is None:
        message += ": install librosa for extended format support"
    if last_error is not None:
        raise PipelineError(message) from last_error
    raise PipelineError(message)


class BaseTranscriber:
    async def transcribe(self, audio_path: Path, midi_output: Path, job: Job, audio_info: dict) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class BasicPitchTranscriber(BaseTranscriber):
    async def transcribe(self, audio_path: Path, midi_output: Path, job: Job, audio_info: dict) -> None:
        try:
            from basic_pitch.inference import predict
        except Exception as exc:  # pragma: no cover - optional import
            raise PipelineError(f"Basic Pitch unavailable: {exc}") from exc

        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: predict(
                audio_path,
                output_directory=midi_output.parent,
                save_midi=True,
                save_model_outputs=False,
            ),
        )
        midi_files = sorted(midi_output.parent.glob("*.mid"))
        if not midi_files:
            raise PipelineError("Basic Pitch failed to generate MIDI")
        midi_files[0].rename(midi_output)


class OnsetsAndFramesTranscriber(BaseTranscriber):
    async def transcribe(self, audio_path: Path, midi_output: Path, job: Job, audio_info: dict) -> None:
        try:
            import onnx
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise PipelineError("Onsets and Frames fallback unavailable") from exc

        raise PipelineError("Onsets and Frames fallback not implemented in this environment")


class StubTranscriber(BaseTranscriber):
    def __init__(self, midi_template: Path) -> None:
        self._template = midi_template

    async def transcribe(self, audio_path: Path, midi_output: Path, job: Job, audio_info: dict) -> None:
        sf.info(str(audio_path))
        midi_output.parent.mkdir(parents=True, exist_ok=True)
        midi_output.write_bytes(self._template.read_bytes())


def load_transcriber() -> BaseTranscriber:
    try:
        __import__("basic_pitch")
        return BasicPitchTranscriber()
    except Exception:
        return StubTranscriber(_default_stub_midi())


def _default_stub_midi() -> Path:
    stub_dir = settings.storage_dir / "stubs"
    stub_dir.mkdir(exist_ok=True)
    stub = stub_dir / "basic.mid"
    if not stub.exists():
        import pretty_midi

        midi = pretty_midi.PrettyMIDI()
        instrument = pretty_midi.Instrument(program=0)
        for i, pitch in enumerate([60, 62, 64, 65, 67, 69, 71, 72]):
            note = pretty_midi.Note(start=i * 0.5, end=i * 0.5 + 0.5, pitch=pitch, velocity=90)
            instrument.notes.append(note)
        midi.instruments.append(instrument)
        midi.write(str(stub))
    return stub


class MidiQuantizer:
    def quantize(self, midi_input: Path, midi_output: Path, job: Job) -> None:
        import pretty_midi

        pm = pretty_midi.PrettyMIDI(str(midi_input))
        grid = job.options.quantization
        step_map = {
            QuantizationGrid.quarter: 1.0,
            QuantizationGrid.eighth: 0.5,
            QuantizationGrid.sixteenth: 0.25,
        }
        step = step_map.get(grid, 0.5)
        beat_length = step
        if job.options.loose_quantization:
            beat_length *= 0.5
        for instrument in pm.instruments:
            for note in instrument.notes:
                note.start = round(note.start / beat_length) * beat_length
                note.end = max(note.start + beat_length, round(note.end / beat_length) * beat_length)
        pm.remove_invalid_notes()
        pm.write(str(midi_output))


class MetadataBuilder:
    def __init__(self) -> None:
        self.meta: JobMeta | None = None

    def build_musicxml(self, midi_path: Path, output_path: Path, job: Job) -> Path:
        from music21 import clef, converter, key, meter, metadata, tempo
        import pretty_midi

        pm = pretty_midi.PrettyMIDI(str(midi_path))
        score = converter.parse(str(midi_path))
        first_staff = score.parts[0] if score.parts else score
        first_staff.insert(0, self._clef_for(job.options.clef))
        score.metadata = metadata.Metadata()
        score.metadata.title = "ScoreForge Transcription"

        metronome_mark = None
        if job.options.tempo:
            metronome_mark = tempo.MetronomeMark(number=job.options.tempo)
            score.insert(0, metronome_mark)
        else:
            marks = list(score.recurse().getElementsByClass(tempo.MetronomeMark))
            if marks:
                metronome_mark = marks[0]

        detected_key = score.analyze("key")
        applied_key = detected_key
        if job.options.force_key:
            try:
                applied_key = key.Key(job.options.force_key)
                score.insert(0, applied_key)
            except Exception:
                applied_key = detected_key

        note_count = sum(len(instrument.notes) for instrument in pm.instruments)
        tempo_value = job.options.tempo or (metronome_mark.number if metronome_mark else 120)
        tempo_value = tempo_value or 120
        duration_seconds = float(score.duration.quarterLength) * (60.0 / tempo_value)

        self.meta = JobMeta(
            title=score.metadata.title,
            key=str(applied_key) if applied_key else None,
            tempo=int(tempo_value) if tempo_value else None,
            note_count=note_count,
            duration_seconds=duration_seconds,
        )

        if job.options.detect_time_signature:
            ts = None
            try:
                ts = score.analyze("meter")
            except Exception:
                pass
            if not ts:
                existing_ts = list(score.recurse().getElementsByClass(meter.TimeSignature))
                if existing_ts:
                    ts = existing_ts[0]
            if self.meta:
                self.meta.time_signature = str(ts) if ts else None

        score.write("musicxml", fp=str(output_path))
        return output_path

    def _clef_for(self, clef_choice: ClefChoice):
        from music21 import clef

        mapping = {
            ClefChoice.treble: clef.TrebleClef(),
            ClefChoice.alto: clef.AltoClef(),
            ClefChoice.tenor: clef.TenorClef(),
            ClefChoice.bass: clef.BassClef(),
        }
        return mapping[clef_choice]


class BaseEngraver:
    def engrave(self, musicxml_path: Path, pdf_path: Path) -> None:  # pragma: no cover - interface
        raise NotImplementedError


class LilypondEngraver(BaseEngraver):
    def __init__(self, executable: str | None = None) -> None:
        self.executable = executable or settings.engraver_path or "lilypond"

    def engrave(self, musicxml_path: Path, pdf_path: Path) -> None:
        ly_path = musicxml_path.with_suffix(".ly")
        musicxml2ly_executable = self._musicxml2ly_executable()
        subprocess.run([
            musicxml2ly_executable,
            str(musicxml_path),
            "-o",
            str(ly_path),
        ], check=True)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([
            self.executable,
            "-o",
            str(pdf_path.with_suffix("")),
            str(ly_path),
        ], check=True)

    def _musicxml2ly_executable(self) -> str:
        if settings.musicxml2ly_path:
            return settings.musicxml2ly_path

        lilypond_path = Path(self.executable)
        if lilypond_path.is_absolute():
            return str(lilypond_path.with_name("musicxml2ly"))

        if lilypond_path.parent != Path("."):
            return str(lilypond_path.parent / "musicxml2ly")

        return "musicxml2ly"


class MuseScoreEngraver(BaseEngraver):
    def __init__(self, executable: str | None = None) -> None:
        self.executable = executable or settings.engraver_path or "mscore"

    def engrave(self, musicxml_path: Path, pdf_path: Path) -> None:
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([
            self.executable,
            "-o",
            str(pdf_path),
            str(musicxml_path),
        ], check=True)


class PlaceholderEngraver(BaseEngraver):
    def engrave(self, musicxml_path: Path, pdf_path: Path) -> None:
        try:
            from reportlab.lib.pagesizes import letter
            from reportlab.pdfgen import canvas
        except Exception as exc:  # pragma: no cover
            pdf_path.write_bytes(b"%PDF-1.4\n% ScoreForge placeholder\n")
            return

        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        c = canvas.Canvas(str(pdf_path), pagesize=letter)
        c.setFont("Helvetica", 16)
        c.drawString(72, 720, "ScoreForge Placeholder Score")
        c.setFont("Helvetica", 10)
        c.drawString(72, 700, f"Generated from {musicxml_path.name}")
        c.save()


def load_engraver() -> BaseEngraver:
    engraver = settings.engraver.lower()
    if engraver == "lilypond":
        return LilypondEngraver()
    if engraver == "musescore":
        return MuseScoreEngraver()
    return PlaceholderEngraver()
