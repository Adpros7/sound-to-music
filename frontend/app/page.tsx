'use client';

import { FormEvent, useCallback, useEffect, useState } from 'react';

import { JobStatusPanel } from '@/components/JobStatus';
import { OptionsForm } from '@/components/OptionsForm';
import { ResultsPanel } from '@/components/Results';
import { Uploader } from '@/components/Uploader';
import { fetchJobStatus, uploadJobWithProgress } from '@/lib/api';
import type { JobArtifactUrls, JobOptions, JobStatusResponse } from '@/types/job';

const defaultOptions: JobOptions = {
  clef: 'treble',
  instrument: 'piano',
  tempo: null,
  force_key: null,
  detect_time_signature: true,
  quantization: 'eighth',
  loose_quantization: false
};

export default function HomePage() {
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [options, setOptions] = useState<JobOptions>(defaultOptions);
  const [jobId, setJobId] = useState<string | null>(null);
  const [status, setStatus] = useState<JobStatusResponse['status']>('queued');
  const [progress, setProgress] = useState(0);
  const [eta, setEta] = useState<number | undefined>(undefined);
  const [isUploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [statusDescription, setStatusDescription] = useState<string | undefined>(undefined);
  const [jobResult, setJobResult] = useState<JobStatusResponse | null>(null);

  useEffect(() => {
    if (!jobId) {
      return;
    }

    let cancelled = false;
    let interval: NodeJS.Timeout;

    async function poll() {
      try {
        const response = await fetchJobStatus(jobId);
        if (cancelled) {
          return;
        }
        setJobResult(response);
        setStatus(response.status);
        setProgress(response.progress);
        switch (response.status) {
          case 'queued':
            setStatusDescription('Waiting in queue…');
            break;
          case 'running':
            if (response.progress < 50) {
              setStatusDescription('Transcribing audio to MIDI…');
            } else if (response.progress < 90) {
              setStatusDescription('Quantizing and preparing MusicXML…');
            } else {
              setStatusDescription('Engraving score to PDF…');
            }
            break;
          case 'done':
            setStatusDescription('Complete');
            break;
          case 'error':
            setStatusDescription(response.error ?? 'An error occurred');
            break;
          default:
            setStatusDescription(undefined);
        }
        if (response.status === 'done' || response.status === 'error') {
          clearInterval(interval);
        }
      } catch (err) {
        if (!cancelled) {
          setError((err as Error).message);
        }
      }
    }

    poll();
    interval = setInterval(poll, 1000);

    return () => {
      cancelled = true;
      clearInterval(interval);
    };
  }, [jobId]);

  const onFileSelected = useCallback((file: File) => {
    setSelectedFile(file);
    setError(null);
  }, []);

  const onClearFile = useCallback(() => {
    setSelectedFile(null);
    setError(null);
  }, []);

  const resetAll = useCallback(() => {
    setSelectedFile(null);
    setJobId(null);
    setJobResult(null);
    setProgress(0);
    setStatus('queued');
    setEta(undefined);
    setError(null);
    setStatusDescription(undefined);
    setOptions(defaultOptions);
  }, []);

  const handleSubmit = useCallback(
    async (event?: FormEvent<HTMLFormElement>) => {
      event?.preventDefault();
      if (!selectedFile) {
        setError('Please select an audio file first.');
        return;
      }

      const formData = new FormData();
      formData.append('file', selectedFile);
      formData.append('clef', options.clef);
      formData.append('instrument', options.instrument);
      if (options.tempo) {
        formData.append('tempo', String(options.tempo));
      }
      if (options.force_key) {
        formData.append('force_key', options.force_key);
      }
      formData.append('detect_time_signature', String(options.detect_time_signature));
      formData.append('quantization', options.quantization);
      formData.append('loose_quantization', String(options.loose_quantization));

      setUploading(true);
      setProgress(0);
      setStatus('queued');
      setStatusDescription('Uploading audio…');
      setError(null);
      setEta(undefined);
      setJobResult(null);
      setJobId(null);

      try {
        const response = await uploadJobWithProgress(formData, (value, estimatedSeconds) => {
          setProgress(value);
          setEta(estimatedSeconds);
        });
        setUploading(false);
        setJobId(response.job_id);
        setStatusDescription('Queued for processing…');
      } catch (err) {
        setUploading(false);
        setError((err as Error).message);
      }
    },
    [options, selectedFile]
  );

  const disableControls = isUploading || (jobId !== null && status !== 'error' && status !== 'done');
  const resultsUrls: JobArtifactUrls = jobResult?.urls ?? { pdf: null, musicxml: null, midi: null };

  return (
    <main className="mx-auto max-w-5xl space-y-8 px-4 py-12">
      <header className="space-y-4 text-center">
        <p className="text-sm uppercase tracking-[0.3em] text-accent">ScoreForge</p>
        <h1 className="text-4xl font-bold">Audio to engraved music in minutes</h1>
        <p className="mx-auto max-w-2xl text-base text-slate-300">
          Upload your recording, choose a clef, and ScoreForge will transcribe, quantize, and engrave a clean score. Receive a
          downloadable PDF, MusicXML, and MIDI within minutes.
        </p>
      </header>

      <form onSubmit={handleSubmit} className="grid gap-6 lg:grid-cols-[2fr,1fr]">
        <div className="space-y-6">
          <Uploader
            onFileSelected={onFileSelected}
            onClear={onClearFile}
            uploading={isUploading}
            progress={progress}
            eta={eta}
            file={selectedFile}
            error={error}
          />

          <OptionsForm options={options} onChange={setOptions} disabled={disableControls} />

          <button
            type="submit"
            className="w-full rounded-xl bg-accent px-6 py-3 text-base font-semibold text-slate-900 transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-60"
            disabled={disableControls || !selectedFile}
          >
            {jobId && status !== 'error' && status !== 'done' ? 'Processing…' : 'Convert to score'}
          </button>
        </div>

        <div className="space-y-6">
          <JobStatusPanel status={status} progress={progress} error={jobResult?.error} description={statusDescription} />
          <ResultsPanel meta={jobResult?.meta} urls={resultsUrls} onReset={resetAll} />
        </div>
      </form>
    </main>
  );
}
