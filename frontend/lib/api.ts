import { CreateJobResponse, JobStatusResponse } from '@/types/job';

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL ?? 'http://localhost:8000/api';

export function uploadJobWithProgress(
  formData: FormData,
  onProgress: (progress: number, estimatedSecondsLeft?: number) => void
): Promise<CreateJobResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${API_BASE}/jobs`);

    const startTime = Date.now();
    xhr.upload.onprogress = event => {
      if (!event.lengthComputable) {
        onProgress(5);
        return;
      }
      const percentage = Math.round((event.loaded / event.total) * 100);
      const elapsedSeconds = (Date.now() - startTime) / 1000;
      const rate = event.loaded / elapsedSeconds;
      const remaining = event.total - event.loaded;
      const eta = rate > 0 ? remaining / rate : undefined;
      onProgress(percentage, eta);
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          const response = JSON.parse(xhr.responseText) as CreateJobResponse;
          resolve(response);
        } catch (error) {
          reject(error);
        }
      } else {
        try {
          const payload = JSON.parse(xhr.responseText) as { detail?: string };
          reject(new Error(payload.detail ?? `Upload failed with status ${xhr.status}`));
        } catch {
          reject(new Error(`Upload failed with status ${xhr.status}`));
        }
      }
    };

    xhr.onerror = () => {
      reject(new Error('Network error during upload'));
    };

    xhr.send(formData);
  });
}

export async function fetchJobStatus(jobId: string): Promise<JobStatusResponse> {
  const response = await fetch(`${API_BASE}/jobs/${jobId}`);
  if (!response.ok) {
    throw new Error(`Failed to fetch job status: ${response.statusText}`);
  }
  return (await response.json()) as JobStatusResponse;
}
