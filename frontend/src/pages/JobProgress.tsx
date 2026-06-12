import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { Layout } from "../components/Layout";
import { getJobStatus, JobStatus } from "../lib/api";

export function JobProgress() {
  const { jobId } = useParams<{ jobId: string }>();
  const nav = useNavigate();
  const [job, setJob] = useState<JobStatus | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;
    let stopped = false;
    const poll = async () => {
      try {
        const s = await getJobStatus(jobId);
        if (stopped) return;
        setJob(s);
        if (s.status === "done") {
          nav(`/results/${jobId}`);
          return;
        }
        if (s.status !== "failed") {
          setTimeout(poll, 1000);
        }
      } catch (e: any) {
        setErr(e.message);
      }
    };
    poll();
    return () => { stopped = true; };
  }, [jobId, nav]);

  return (
    <Layout>
      <h1 className="text-2xl font-bold">Generando cohorte…</h1>
      <p className="text-xs text-slate-500 mt-1 font-mono">{jobId}</p>

      <div className="mt-8 rounded-lg bg-white p-6 shadow-sm">
        {err && <div className="text-red-600 text-sm">{err}</div>}
        {job && (
          <>
            <div className="flex items-center justify-between text-sm">
              <span className="font-medium">Estado:</span>
              <span className="px-2 py-1 rounded bg-slate-100 text-xs">
                {job.status}
              </span>
            </div>
            <div className="mt-4 h-2 rounded-full bg-slate-200 overflow-hidden">
              <div
                className="h-full bg-blue-600 transition-all"
                style={{ width: `${Math.round(job.progress * 100)}%` }}
              />
            </div>
            <div className="mt-2 text-xs text-slate-500">
              {Math.round(job.progress * 100)} % — {job.message}
            </div>
            {job.status === "failed" && (
              <div className="mt-4 rounded bg-red-50 p-3 text-sm text-red-700">
                {job.error}
              </div>
            )}
          </>
        )}
      </div>
    </Layout>
  );
}
