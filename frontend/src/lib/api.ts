// Cliente API mínimo — usa fetch nativo. El backend está expuesto vía
// proxy de Vite (ver vite.config.ts).

export interface CohortConfig {
  n_patients: number;
  edad_min: number;
  edad_max: number;
  sex_distribution: "balanced" | "real_world" | "more_men" | "more_women";
  region_focus: "any" | "alta" | "media" | "baja";
  forzar_comorbilidades: string[];
  excluir_comorbilidades: string[];
  generar_notas_clinicas: boolean;
  output_formats: ("csv" | "fhir" | "omop" | "all")[];
  seed: number | null;
}

export interface JobStatus {
  job_id: string;
  status: "queued" | "running" | "done" | "failed";
  progress: number;
  message: string;
  dataset_id: string | null;
  error: string | null;
  created_at: string;
  updated_at: string;
}

export async function generateCohort(cfg: CohortConfig): Promise<{ job_id: string }> {
  const r = await fetch("/api/cohorts/generate", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(cfg),
  });
  if (!r.ok) throw new Error(`POST /generate failed: ${r.status}`);
  return r.json();
}

export async function getJobStatus(jobId: string): Promise<JobStatus> {
  const r = await fetch(`/api/cohorts/${jobId}/status`);
  if (!r.ok) throw new Error(`GET /status failed: ${r.status}`);
  return r.json();
}

export async function getPreview(jobId: string, limit = 20): Promise<any> {
  const r = await fetch(`/api/cohorts/${jobId}/preview?limit=${limit}`);
  if (!r.ok) throw new Error(`GET /preview failed: ${r.status}`);
  return r.json();
}

export async function getMetrics(jobId: string): Promise<any> {
  const r = await fetch(`/api/cohorts/${jobId}/metrics`);
  if (!r.ok) throw new Error(`GET /metrics failed: ${r.status}`);
  return r.json();
}

export async function getHistory(): Promise<any[]> {
  const r = await fetch(`/api/cohorts`);
  if (!r.ok) throw new Error(`GET /cohorts failed: ${r.status}`);
  return r.json();
}

export function downloadUrl(jobId: string, format: "csv" | "fhir" | "omop"): string {
  return `/api/cohorts/${jobId}/data?format=${format}`;
}

export function datasheetUrl(jobId: string): string {
  return `/api/cohorts/${jobId}/datasheet`;
}
