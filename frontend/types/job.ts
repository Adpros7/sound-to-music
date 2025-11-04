export type JobStatus = 'queued' | 'running' | 'done' | 'error';

export type ClefChoice = 'treble' | 'alto' | 'tenor';
export type QuantizationGrid = 'quarter' | 'eighth' | 'sixteenth';

export interface JobMeta {
  title?: string;
  key?: string;
  time_signature?: string | null;
  tempo?: number | null;
  note_count?: number | null;
  duration_seconds?: number | null;
}

export interface JobArtifactUrls {
  pdf?: string | null;
  musicxml?: string | null;
  midi?: string | null;
}

export interface JobStatusResponse {
  status: JobStatus;
  progress: number;
  error?: string | null;
  urls: JobArtifactUrls;
  meta?: JobMeta | null;
}

export interface CreateJobResponse {
  job_id: string;
}

export interface JobOptions {
  clef: ClefChoice;
  tempo?: number | null;
  force_key?: string | null;
  detect_time_signature: boolean;
  quantization: QuantizationGrid;
  loose_quantization: boolean;
}
