from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Iterable
import shutil

import numpy as np
import pytest
import soundfile as sf
import subprocess

from ..models import ClefChoice, InstrumentChoice, JobOptions, QuantizationGrid, Job
from ..services.pipeline import (
    PipelineDependencies,
    PlaceholderEngraver,
    PipelineOptions,
    run_pipeline,
    BaseTranscriber,
    LilypondEngraver,
    MetadataBuilder,
)
from ..config import settings


class MidiFixtureTranscriber(BaseTranscriber):
    def __init__(self, notes: Iterable[Iterable[int]]) -> None:
        self.notes = [list(chord) for chord in notes]

    async def transcribe(self, audio_path: Path, midi_output: Path, job, audio_info) -> None:
        import pretty_midi

        midi_output.parent.mkdir(parents=True, exist_ok=True)
        midi = pretty_midi.PrettyMIDI()
        instrument = pretty_midi.Instrument(program=0)
        time = 0.0
        for chord in self.notes:
            duration = 0.5 if len(chord) == 1 else 1.0
            for pitch in chord:
                note = pretty_midi.Note(start=time, end=time + duration, pitch=pitch, velocity=90)
                instrument.notes.append(note)
            time += duration
        midi.instruments.append(instrument)
        midi.write(str(midi_output))


@pytest.fixture
def sine_wave_data() -> tuple[np.ndarray, int]:
    sample_rate = 44100
    duration = 1.0
    t = np.linspace(0, duration, int(sample_rate * duration), endpoint=False)
    waveform = 0.2 * np.sin(2 * np.pi * 440 * t)
    return waveform.astype(np.float32), sample_rate


@pytest.fixture
def sine_wave(tmp_path: Path, sine_wave_data: tuple[np.ndarray, int]) -> Path:
    waveform, sample_rate = sine_wave_data
    path = tmp_path / "upload.wav"
    sf.write(path, waveform, sample_rate)
    return path


@pytest.fixture
def sine_wave_mp3(tmp_path: Path, sine_wave_data: tuple[np.ndarray, int]) -> Path:
    waveform, sample_rate = sine_wave_data
    import lameenc

    encoder = lameenc.Encoder()
    encoder.set_bit_rate(128)
    encoder.set_in_sample_rate(sample_rate)
    encoder.set_channels(1)
    encoder.set_quality(2)
    pcm = np.clip(waveform, -1.0, 1.0)
    pcm16 = (pcm * 32767).astype(np.int16)
    mp3_data = encoder.encode(pcm16.tobytes()) + encoder.flush()
    path = tmp_path / "upload.mp3"
    path.write_bytes(mp3_data)
    return path


def _build_job(tmp_path: Path, options: JobOptions) -> Job:
    job = Job.create(options=options, retention=timedelta(minutes=5), workdir=tmp_path)
    job.workdir.mkdir(parents=True, exist_ok=True)
    return job


@pytest.mark.parametrize("audio_fixture", ["sine_wave", "sine_wave_mp3"])
@pytest.mark.parametrize(
    "instrument_choice, fixture_notes, expected_count",
    [
        (InstrumentChoice.piano, [[60, 64, 67]], 3),
        (InstrumentChoice.piano, [[72], [74], [76], [77]], 4),
        (InstrumentChoice.viola, [[60, 64, 67]], 2),
    ],
)
@pytest.mark.asyncio
async def test_pipeline_generates_artifacts(
    tmp_path: Path,
    request: pytest.FixtureRequest,
    audio_fixture,
    instrument_choice: InstrumentChoice,
    fixture_notes,
    expected_count,
):
    job = _build_job(
        tmp_path,
        JobOptions(
            clef=ClefChoice.treble,
            instrument=instrument_choice,
            tempo=120,
            force_key=None,
            detect_time_signature=True,
            quantization=QuantizationGrid.eighth,
            loose_quantization=False,
        ),
    )
    source_audio: Path = request.getfixturevalue(audio_fixture)
    # Copy audio fixture to expected location
    dest = job.workdir / source_audio.name
    shutil.copy(source_audio, dest)

    deps = PipelineDependencies(
        engraver=PlaceholderEngraver(),
        transcriber=MidiFixtureTranscriber(fixture_notes),
    )
    await run_pipeline(job, deps, PipelineOptions())

    assert job.artifacts["pdf"].exists()
    assert job.artifacts["musicxml"].exists()
    assert job.artifacts["midi"].exists()
    assert job.meta is not None
    assert job.meta.note_count == expected_count
    assert job.meta.tempo == 120
    assert job.meta.key is not None
    assert job.meta.instrument == instrument_choice


def test_metadata_builder_supports_bass_clef():
    builder = MetadataBuilder()
    bass_clef = builder._clef_for(ClefChoice.bass)

    from music21 import clef as music21_clef

    assert isinstance(bass_clef, music21_clef.BassClef)


def test_lilypond_engraver_resolves_musicxml2ly(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    lilypond_dir = tmp_path / "lilypond-bin"
    lilypond_dir.mkdir()
    lilypond_path = lilypond_dir / "lilypond"

    monkeypatch.setenv("PATH", str(tmp_path / "empty-path"))
    monkeypatch.setenv("ENGRAVER_PATH", str(lilypond_path))
    monkeypatch.setattr(settings, "engraver_path", str(lilypond_path))
    monkeypatch.setattr(settings, "musicxml2ly_path", None, raising=False)

    calls: list[list[str]] = []

    def fake_run(cmd, *args, **kwargs):
        calls.append(cmd)
        return subprocess.CompletedProcess(cmd, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)

    engraver = LilypondEngraver()
    musicxml_path = tmp_path / "score.musicxml"
    pdf_path = tmp_path / "output" / "score.pdf"
    musicxml_path.write_text("<score/>")

    engraver.engrave(musicxml_path, pdf_path)

    assert len(calls) == 2
    assert Path(calls[0][0]) == lilypond_path.with_name("musicxml2ly")
    assert calls[0][1:] == [str(musicxml_path), "-o", str(musicxml_path.with_suffix(".ly"))]
    assert calls[1][0] == str(lilypond_path)
