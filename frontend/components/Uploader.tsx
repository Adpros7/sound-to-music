'use client';

import { useCallback, useState, type DragEvent } from 'react';
import { ArrowUpTrayIcon, XMarkIcon } from '@heroicons/react/24/outline';
import clsx from 'clsx';

interface UploaderProps {
  onFileSelected: (file: File) => void;
  onClear: () => void;
  uploading: boolean;
  progress: number;
  eta?: number;
  file?: File | null;
  error?: string | null;
}

const ACCEPTED_TYPES = ['audio/wav', 'audio/x-wav', 'audio/mpeg', 'audio/mp3', 'audio/x-m4a', 'audio/flac', 'audio/x-flac'];
const ACCEPTED_EXTENSIONS = ['.wav', '.mp3', '.m4a', '.flac'];

export function Uploader({ onFileSelected, onClear, uploading, progress, eta, file, error }: UploaderProps) {
  const [isDragging, setDragging] = useState(false);

  const handleFiles = useCallback(
    (files: FileList | null) => {
      if (!files || files.length === 0) {
        return;
      }
      const candidate = files[0];
      const isAllowedType = candidate.type && ACCEPTED_TYPES.includes(candidate.type);
      const hasAllowedExtension = ACCEPTED_EXTENSIONS.some(ext => candidate.name.toLowerCase().endsWith(ext));
      if (!(isAllowedType || hasAllowedExtension)) {
        alert('Unsupported file type. Please upload WAV, MP3, M4A, or FLAC files.');
        return;
      }
      onFileSelected(candidate);
    },
    [onFileSelected]
  );

  const onDrop = useCallback(
    (event: DragEvent<HTMLLabelElement>) => {
      event.preventDefault();
      setDragging(false);
      handleFiles(event.dataTransfer.files);
    },
    [handleFiles]
  );

  return (
    <div className="space-y-3">
      <label
        onDragOver={event => {
          event.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={onDrop}
        className={clsx(
          'flex flex-col items-center justify-center rounded-2xl border-2 border-dashed p-8 transition-colors',
          isDragging ? 'border-accent bg-slate-800/50' : 'border-slate-600/60 bg-slate-800/30',
          uploading && 'opacity-70'
        )}
      >
        <ArrowUpTrayIcon className="h-12 w-12 text-accent" />
        <p className="mt-4 text-lg font-semibold">Drag & drop audio or click to browse</p>
        <p className="mt-2 text-sm text-slate-300">Accepted: WAV, MP3, M4A, FLAC. Max 20MB / 5 minutes.</p>
        <input
          type="file"
          accept={[...ACCEPTED_TYPES, ...ACCEPTED_EXTENSIONS].join(',')}
          className="hidden"
          onChange={event => handleFiles(event.target.files)}
          disabled={uploading}
        />
      </label>

      {file && (
        <div className="flex items-center justify-between rounded-xl bg-slate-900/70 px-4 py-3">
          <div>
            <p className="text-sm font-medium">{file.name}</p>
            <p className="text-xs text-slate-400">{(file.size / (1024 * 1024)).toFixed(2)} MB</p>
          </div>
          <button
            type="button"
            className="rounded-full bg-slate-700/80 p-2 text-slate-100 hover:bg-slate-600"
            onClick={onClear}
            aria-label="Remove file"
            disabled={uploading}
          >
            <XMarkIcon className="h-4 w-4" />
          </button>
        </div>
      )}

      {uploading && (
        <div className="space-y-2">
          <div className="h-3 w-full rounded-full bg-slate-800">
            <div
              className="h-3 rounded-full bg-accent transition-all"
              style={{ width: `${Math.min(100, progress)}%` }}
            />
          </div>
          <p className="text-xs text-slate-400">
            Uploading… {progress}%{eta ? ` · ETA ${Math.max(1, Math.round(eta))}s` : ''}
          </p>
        </div>
      )}

      {error && <p className="text-sm text-red-400">{error}</p>}
    </div>
  );
}
