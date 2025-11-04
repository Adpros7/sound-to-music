from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from typing import Iterable
import shutil

import numpy as np
import pytest
import soundfile as sf

from ..models import ClefChoice, JobOptions, QuantizationGrid, Job
from ..services.pipeline import (
    PipelineDependencies,
    PlaceholderEngraver,
    PipelineOptions,
    run_pipeline,
    BaseTranscriber,
)


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
    "fixture_notes, expected_count",
    [
        ([[60, 64, 67]], 3),
        ([[72], [74], [76], [77]], 4),
        ([[60, 63], [62], [65, 69]], 5),
    ],
)
@pytest.mark.asyncio
async def test_pipeline_generates_artifacts(tmp_path: Path, request: pytest.FixtureRequest, audio_fixture, fixture_notes, expected_count):
    job = _build_job(
        tmp_path,
        JobOptions(
            clef=ClefChoice.treble,
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
