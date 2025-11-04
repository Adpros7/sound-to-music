'use client';

import { ArrowDownTrayIcon } from '@heroicons/react/24/outline';
import type { JobArtifactUrls, JobMeta } from '@/types/job';

interface ResultsProps {
  meta?: JobMeta | null;
  urls: JobArtifactUrls;
  onReset: () => void;
}

const downloadItems: Array<{ key: keyof JobArtifactUrls; label: string }> = [
  { key: 'pdf', label: 'PDF score' },
  { key: 'musicxml', label: 'MusicXML' },
  { key: 'midi', label: 'MIDI' }
];

export function ResultsPanel({ meta, urls, onReset }: ResultsProps) {
  const hasResults = Object.values(urls).some(Boolean);

  if (!hasResults) {
    return null;
  }

  return (
    <div className="space-y-4 rounded-2xl bg-slate-900/60 p-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-lg font-semibold">Results</h2>
          <p className="text-sm text-slate-400">Downloads stay active for 30 minutes.</p>
        </div>
        <button
          type="button"
          onClick={onReset}
          className="rounded-full border border-slate-600/60 px-4 py-2 text-xs font-semibold uppercase tracking-wide text-slate-200 transition hover:border-accent hover:text-accent"
        >
          New transcription
        </button>
      </div>

      {meta && (
        <dl className="grid gap-4 sm:grid-cols-3">
          {meta.title && (
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-400">Title</dt>
              <dd className="text-sm font-medium text-slate-200">{meta.title}</dd>
            </div>
          )}
          {meta.key && (
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-400">Key</dt>
              <dd className="text-sm text-slate-200">{meta.key}</dd>
            </div>
          )}
          {meta.time_signature && (
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-400">Time signature</dt>
              <dd className="text-sm text-slate-200">{meta.time_signature}</dd>
            </div>
          )}
          {meta.tempo && (
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-400">Tempo</dt>
              <dd className="text-sm text-slate-200">{meta.tempo} BPM</dd>
            </div>
          )}
          {meta.note_count != null && (
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-400">Note count</dt>
              <dd className="text-sm text-slate-200">{meta.note_count}</dd>
            </div>
          )}
          {meta.duration_seconds != null && (
            <div>
              <dt className="text-xs uppercase tracking-wide text-slate-400">Duration</dt>
              <dd className="text-sm text-slate-200">{meta.duration_seconds.toFixed(1)} s</dd>
            </div>
          )}
        </dl>
      )}

      <div className="grid gap-3 md:grid-cols-3">
        {downloadItems.map(item => {
          const href = urls[item.key];
          const disabled = !href;
          return (
            <a
              key={item.key}
              href={href ?? undefined}
              target="_blank"
              rel="noopener noreferrer"
              aria-disabled={disabled}
              className={
                'flex items-center justify-between rounded-xl border border-slate-700/60 bg-slate-800/40 px-4 py-3 transition ' +
                (disabled ? 'cursor-not-allowed opacity-60' : 'hover:border-accent')
              }
            >
              <span className="text-sm font-semibold text-slate-200">{item.label}</span>
              <ArrowDownTrayIcon className="h-5 w-5 text-accent" />
            </a>
          );
        })}
      </div>
    </div>
  );
}
