import { useEffect, useState } from "react";
import { Layout } from "../components/Layout";
import { getHistory } from "../lib/api";

export function History() {
  const [items, setItems] = useState<any[] | null>(null);
  const [err, setErr] = useState<string | null>(null);

  useEffect(() => {
    getHistory().then(setItems).catch(e => setErr(e.message));
  }, []);

  return (
    <Layout>
      <h1 className="text-2xl font-bold">Historial de cohortes</h1>
      {err && <div className="text-red-600 mt-4">{err}</div>}
      {!items && !err && <div className="text-slate-500 mt-4">Cargando…</div>}
      {items && items.length === 0 && (
        <div className="text-slate-500 mt-4">Aún no has generado ninguna cohorte.</div>
      )}
      {items && items.length > 0 && (
        <table className="mt-6 min-w-full bg-white rounded-lg shadow-sm">
          <thead>
            <tr className="text-left text-xs text-slate-500 border-b">
              <th className="py-3 px-4 font-medium">Dataset ID</th>
              <th className="py-3 px-4 font-medium">Creado</th>
              <th className="py-3 px-4 font-medium">Pacientes</th>
              <th className="py-3 px-4 font-medium">Foco</th>
            </tr>
          </thead>
          <tbody>
            {items.map(it => (
              <tr key={it.dataset_id} className="text-sm border-b last:border-0">
                <td className="py-3 px-4 font-mono text-xs">
                  {it.dataset_id.slice(0, 13)}…
                </td>
                <td className="py-3 px-4">{new Date(it.created_at).toLocaleString()}</td>
                <td className="py-3 px-4">{it.n_patients}</td>
                <td className="py-3 px-4">{it.config?.region_focus ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Layout>
  );
}
