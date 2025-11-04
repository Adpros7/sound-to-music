'use client';

import { ChangeEvent } from 'react';
import type { JobOptions } from '@/types/job';

interface OptionsFormProps {
  options: JobOptions;
  onChange: (options: JobOptions) => void;
  disabled?: boolean;
}

const clefs = [
  { value: 'treble', label: 'Treble' },
  { value: 'alto', label: 'Alto' },
  { value: 'tenor', label: 'Tenor' },
  { value: 'bass', label: 'Bass' }
] as const;

const quantizationOptions = [
  { value: 'quarter', label: 'Quarter notes' },
  { value: 'eighth', label: 'Eighth notes' },
  { value: 'sixteenth', label: 'Sixteenth notes' }
] as const;

export function OptionsForm({ options, onChange, disabled }: OptionsFormProps) {
  const handleChange = <K extends keyof JobOptions>(key: K, value: JobOptions[K]) => {
    onChange({ ...options, [key]: value });
  };

  const onCheckboxChange = (event: ChangeEvent<HTMLInputElement>) => {
    const { name, checked } = event.target;
    handleChange(name as keyof JobOptions, checked as JobOptions[keyof JobOptions]);
  };

  return (
    <div className="space-y-6 rounded-2xl bg-slate-900/50 p-6">
      <div className="space-y-2">
        <h2 className="text-lg font-semibold">Options</h2>
        <p className="text-sm text-slate-400">Tailor the transcription before submitting the job.</p>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="space-y-1">
          <label className="text-xs uppercase tracking-wide text-slate-400">Clef</label>
          <select
            className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-sm focus:border-accent focus:outline-none"
            value={options.clef}
            disabled={disabled}
            onChange={event => handleChange('clef', event.target.value as JobOptions['clef'])}
          >
            {clefs.map(item => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </div>

        <div className="space-y-1">
          <label className="text-xs uppercase tracking-wide text-slate-400">Target tempo (BPM)</label>
          <input
            type="number"
            min={40}
            max={240}
            placeholder="Auto"
            className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-sm focus:border-accent focus:outline-none"
            value={options.tempo ?? ''}
            disabled={disabled}
            onChange={event => handleChange('tempo', event.target.value ? Number(event.target.value) : null)}
          />
        </div>

        <div className="space-y-1">
          <label className="text-xs uppercase tracking-wide text-slate-400">Force key signature</label>
          <input
            type="text"
            placeholder="e.g. C major"
            className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-sm focus:border-accent focus:outline-none"
            value={options.force_key ?? ''}
            disabled={disabled}
            onChange={event => handleChange('force_key', event.target.value || null)}
          />
        </div>

        <div className="space-y-1">
          <label className="text-xs uppercase tracking-wide text-slate-400">Quantization grid</label>
          <select
            className="w-full rounded-lg border border-slate-700 bg-slate-800/80 px-3 py-2 text-sm focus:border-accent focus:outline-none"
            value={options.quantization}
            disabled={disabled}
            onChange={event => handleChange('quantization', event.target.value as JobOptions['quantization'])}
          >
            {quantizationOptions.map(item => (
              <option key={item.value} value={item.value}>
                {item.label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-2">
        <label className="flex items-center space-x-3 rounded-xl bg-slate-800/50 px-4 py-3">
          <input
            type="checkbox"
            name="detect_time_signature"
            checked={options.detect_time_signature}
            disabled={disabled}
            onChange={onCheckboxChange}
            className="h-4 w-4 rounded border-slate-500 text-accent focus:ring-accent"
          />
          <span className="text-sm">Auto-detect time signature</span>
        </label>

        <label className="flex items-center space-x-3 rounded-xl bg-slate-800/50 px-4 py-3">
          <input
            type="checkbox"
            name="loose_quantization"
            checked={options.loose_quantization}
            disabled={disabled}
            onChange={onCheckboxChange}
            className="h-4 w-4 rounded border-slate-500 text-accent focus:ring-accent"
          />
          <span className="text-sm">Loosen quantization (keep more nuance)</span>
        </label>
      </div>
    </div>
  );
}
