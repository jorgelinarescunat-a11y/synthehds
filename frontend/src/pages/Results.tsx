import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import {
  Bar, BarChart, CartesianGrid, ResponsiveContainer,
  Tooltip, XAxis, YAxis,
} from "recharts";
import { Layout } from "../components/Layout";
import {
  datasheetUrl, downloadUrl, getMetrics, getPreview,
} from "../lib/api";

export function Results() {
  const { jobId } = useParams<{ jobId: string }>();
  const [preview, setPreview] = useState<any | null>(null);
  const [metrics, setMetrics] = useState<any | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    if (!jobId) return;
    Promise.all([getPreview(jobId, 20), getMetrics(jobId)])
      .then(([pv, m]) => { setPreview(pv); setMetrics(m); })
      .catch(e => setErr(e.message));
  }, [jobId]);

  if (err) return <Layout><div className="text-red-600">{err}</div></Layout>;
  if (!preview || !metrics)
    return <Layout><div className="text-slate-500">Cargando resultados…</div></Layout>;

  const cat = metrics.fidelidad_estadistica.categoricas as Record<string, any>;
  const distroData = Object.entries(cat).map(([key, v]: [string, any]) => ({
    name: key,
    observado: v.observado_pct,
    esperado: v.esperado_pct,
  }));

  return (
    <Layout>
      <h1 className="text-2xl font-bold">Resultados</h1>
      <p className="text-xs text-slate-500 mt-1 font-mono">{jobId}</p>

      <section className="mt-6 grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Pacientes" value={preview.n_total} />
        <Stat
          label="Coherencia clínica"
          value={`${metrics.coherencia_clinica.score_global_pct}%`}
        />
        <Stat
          label="Combinaciones únicas"
          value={`${metrics.privacidad_unicidad.pct_unicas}%`}
        />
        <Stat
          label="Variables categóricas"
          value={Object.keys(cat).length}
        />
      </section>

      <section className="mt-6 grid grid-cols-1 lg:grid-cols-3 gap-4">
        <div className="lg:col-span-2 rounded-lg bg-white p-5 shadow-sm">
          <h3 className="font-semibold mb-3 text-sm">
            Distribuciones — observado vs YAML
          </h3>
          <div style={{ width: "100%", height: 320 }}>
            <ResponsiveContainer>
              <BarChart data={distroData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#eef" />
                <XAxis dataKey="name" tick={{ fontSize: 10 }} angle={-30} textAnchor="end" height={70} />
                <YAxis unit="%" tick={{ fontSize: 11 }} />
                <Tooltip />
                <Bar dataKey="observado" fill="#1d4ed8" name="Observado" />
                <Bar dataKey="esperado" fill="#94a3b8" name="Esperado (YAML)" />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="rounded-lg bg-white p-5 shadow-sm">
          <h3 className="font-semibold mb-3 text-sm">Descargas</h3>
          <DownloadList jobId={jobId!} />
        </div>
      </section>

      <section className="mt-6 rounded-lg bg-white p-5 shadow-sm overflow-x-auto">
        <h3 className="font-semibold text-sm mb-3">Preview — primeros 20 pacientes</h3>
        <table className="min-w-full text-xs">
          <thead>
            <tr className="text-left text-slate-500 border-b">
              {["ID", "Sexo", "Edad", "Región", "HTA", "Dislipemia", "Nefropatía", "Insulina"].map(h =>
                <th key={h} className="py-2 pr-3 font-medium">{h}</th>
              )}
            </tr>
          </thead>
          <tbody>
            {preview.preview.map((p: any) => (
              <tr key={p.patient_id} className="border-b last:border-0">
                <td className="py-2 pr-3 font-mono text-[10px]">{p.patient_id.slice(0, 8)}…</td>
                <td className="py-2 pr-3">{p.sexo}</td>
                <td className="py-2 pr-3">{p.edad}</td>
                <td className="py-2 pr-3">{p.region}</td>
                <td className="py-2 pr-3">{p.hipertension ? "✓" : "—"}</td>
                <td className="py-2 pr-3">{p.dislipemia ? "✓" : "—"}</td>
                <td className="py-2 pr-3">{p.nefropatia ? "✓" : "—"}</td>
                <td className="py-2 pr-3">{p.insulina ? "✓" : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </section>
    </Layout>
  );
}

function Stat({ label, value }: { label: string; value: any }) {
  return (
    <div className="rounded-lg bg-white p-4 shadow-sm">
      <div className="text-xs text-slate-500">{label}</div>
      <div className="text-2xl font-semibold mt-1">{value}</div>
    </div>
  );
}

function DownloadList({ jobId }: { jobId: string }) {
  const items: { label: string; href: string }[] = [
    { label: "CSV (plano)", href: downloadUrl(jobId, "csv") },
    { label: "FHIR Bundle JSON", href: downloadUrl(jobId, "fhir") },
    { label: "OMOP CDM (JSON de CSVs)", href: downloadUrl(jobId, "omop") },
    { label: "Data sheet PDF", href: datasheetUrl(jobId) },
  ];
  return (
    <ul className="space-y-2 text-sm">
      {items.map(it => (
        <li key={it.label}>
          <a
            href={it.href}
            className="text-blue-700 hover:underline"
            target="_blank" rel="noreferrer"
          >
            {it.label}
          </a>
        </li>
      ))}
    </ul>
  );
}
