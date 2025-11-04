'use client';

import { CheckCircleIcon, ExclamationCircleIcon } from '@heroicons/react/24/solid';
import clsx from 'clsx';
import type { JobStatus } from '@/types/job';

interface JobStatusProps {
  status: JobStatus;
  progress: number;
  error?: string | null;
  description?: string;
}

const statusLabels: Record<JobStatus, string> = {
  queued: 'Queued',
  running: 'Processing',
  done: 'Complete',
  error: 'Error'
};

export function JobStatusBadge({ status }: { status: JobStatus }) {
  return (
    <span
      className={clsx(
        'rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide',
        status === 'done' && 'bg-emerald-500/20 text-emerald-200',
        status === 'error' && 'bg-red-500/20 text-red-200',
        status === 'running' && 'bg-blue-500/20 text-blue-200',
        status === 'queued' && 'bg-slate-500/20 text-slate-200'
      )}
    >
      {statusLabels[status]}
    </span>
  );
}

export function JobStatusPanel({ status, progress, error, description }: JobStatusProps) {
  return (
    <div className="space-y-4 rounded-2xl bg-slate-900/50 p-6">
      <div className="flex items-center justify-between">
        <h2 className="text-lg font-semibold">Status</h2>
        <JobStatusBadge status={status} />
      </div>

      {status !== 'error' ? (
        <div className="space-y-3">
          <div className="h-3 w-full rounded-full bg-slate-800">
            <div
              className={clsx(
                'h-3 rounded-full transition-all',
                status === 'done' ? 'bg-emerald-400' : 'bg-accent'
              )}
              style={{ width: `${status === 'done' ? 100 : progress}%` }}
            />
          </div>
          <p className="text-sm text-slate-300">
            {description ?? (status === 'running' ? 'Transcribing and engraving…' : 'Waiting for job to start…')}
          </p>
        </div>
      ) : (
        <div className="flex items-center space-x-3 rounded-xl bg-red-500/10 px-4 py-3 text-red-200">
          <ExclamationCircleIcon className="h-6 w-6" />
          <div>
            <p className="text-sm font-semibold">Something went wrong</p>
            <p className="text-sm">{error ?? 'Unknown error encountered. Please try again.'}</p>
          </div>
        </div>
      )}

      {status === 'done' && (
        <div className="flex items-center space-x-3 rounded-xl bg-emerald-500/10 px-4 py-3 text-emerald-100">
          <CheckCircleIcon className="h-6 w-6" />
          <p className="text-sm">Your score is ready below.</p>
        </div>
      )}
    </div>
  );
}
