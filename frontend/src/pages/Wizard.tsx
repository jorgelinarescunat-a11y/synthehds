import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { Layout } from "../components/Layout";
import { CohortConfig, generateCohort } from "../lib/api";

const COMORBIDITIES = [
  "hipertension", "dislipemia", "nefropatia",
  "retinopatia", "neuropatia", "cardiopatia",
];

export function Wizard() {
  const nav = useNavigate();
  const [submitting, setSubmitting] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [cfg, setCfg] = useState<CohortConfig>({
    n_patients: 200,
    edad_min: 18,
    edad_max: 90,
    sex_distribution: "real_world",
    region_focus: "any",
    forzar_comorbilidades: [],
    excluir_comorbilidades: [],
    generar_notas_clinicas: false,
    output_formats: ["csv", "fhir", "omop"],
    seed: null,
  });

  function toggleArr(field: "forzar_comorbilidades" | "excluir_comorbilidades", v: string) {
    setCfg(c => ({
      ...c,
      [field]: c[field].includes(v) ? c[field].filter(x => x !== v) : [...c[field], v],
    }));
  }

  async function submit() {
    setSubmitting(true);
    setErr(null);
    try {
      const r = await generateCohort(cfg);
      nav(`/job/${r.job_id}`);
    } catch (e: any) {
      setErr(e.message);
      setSubmitting(false);
    }
  }

  return (
    <Layout>
      <h1 className="text-2xl font-bold">Configurar cohorte</h1>
      <p className="text-sm text-slate-500 mt-1">
        Define los parámetros del dataset sintético.
      </p>

      <div className="mt-6 space-y-6 rounded-lg bg-white p-6 shadow-sm">
        <Field label="Número de pacientes (50–10 000)">
          <input
            type="number" min={50} max={10000} value={cfg.n_patients}
            onChange={e => setCfg({ ...cfg, n_patients: Number(e.target.value) })}
            className={inputCls}
          />
        </Field>

        <div className="grid grid-cols-2 gap-4">
          <Field label="Edad mínima">
            <input
              type="number" min={18} max={90} value={cfg.edad_min}
              onChange={e => setCfg({ ...cfg, edad_min: Number(e.target.value) })}
              className={inputCls}
            />
          </Field>
          <Field label="Edad máxima">
            <input
              type="number" min={18} max={90} value={cfg.edad_max}
              onChange={e => setCfg({ ...cfg, edad_max: Number(e.target.value) })}
              className={inputCls}
            />
          </Field>
        </div>

        <Field label="Distribución de sexo">
          <select
            value={cfg.sex_distribution}
            onChange={e => setCfg({ ...cfg, sex_distribution: e.target.value as any })}
            className={inputCls}
          >
            <option value="real_world">Real (literatura)</option>
            <option value="balanced">Equilibrado 50/50</option>
            <option value="more_men">Más hombres (70 %)</option>
            <option value="more_women">Más mujeres (70 %)</option>
          </select>
        </Field>

        <Field label="Foco regional">
          <select
            value={cfg.region_focus}
            onChange={e => setCfg({ ...cfg, region_focus: e.target.value as any })}
            className={inputCls}
          >
            <option value="any">Toda España</option>
            <option value="alta">Prevalencia alta (sur)</option>
            <option value="media">Prevalencia media</option>
            <option value="baja">Prevalencia baja (norte)</option>
          </select>
        </Field>

        <Field label="Forzar comorbilidades (todos los pacientes la tienen)">
          <div className="flex flex-wrap gap-2">
            {COMORBIDITIES.map(c => (
              <Chip
                key={`f-${c}`}
                active={cfg.forzar_comorbilidades.includes(c)}
                onClick={() => toggleArr("forzar_comorbilidades", c)}
              >
                {c}
              </Chip>
            ))}
          </div>
        </Field>

        <Field label="Excluir comorbilidades (ningún paciente la tiene)">
          <div className="flex flex-wrap gap-2">
            {COMORBIDITIES.map(c => (
              <Chip
                key={`e-${c}`}
                active={cfg.excluir_comorbilidades.includes(c)}
                onClick={() => toggleArr("excluir_comorbilidades", c)}
              >
                {c}
              </Chip>
            ))}
          </div>
        </Field>

        <Field label="Notas clínicas con Claude (más lento)">
          <label className="inline-flex items-center gap-2">
            <input
              type="checkbox" checked={cfg.generar_notas_clinicas}
              onChange={e => setCfg({ ...cfg, generar_notas_clinicas: e.target.checked })}
            />
            <span className="text-sm">Generar nota SOAP por encuentro</span>
          </label>
        </Field>

        <Field label="Seed (opcional — reproducibilidad)">
          <input
            type="number"
            value={cfg.seed ?? ""}
            onChange={e => setCfg({ ...cfg, seed: e.target.value ? Number(e.target.value) : null })}
            className={inputCls}
            placeholder="aleatorio"
          />
        </Field>

        {err && <div className="text-sm text-red-600">{err}</div>}

        <button
          disabled={submitting}
          onClick={submit}
          className="rounded bg-blue-700 px-6 py-2 text-white text-sm font-medium hover:bg-blue-800 disabled:opacity-50"
        >
          {submitting ? "Enviando…" : "Generar cohorte"}
        </button>
      </div>
    </Layout>
  );
}

const inputCls =
  "w-full rounded border border-slate-300 px-3 py-2 text-sm focus:border-blue-500 focus:outline-none";

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div>
      <label className="block text-sm font-medium text-slate-700 mb-1">{label}</label>
      {children}
    </div>
  );
}

function Chip({
  active, children, onClick,
}: {
  active: boolean;
  children: React.ReactNode;
  onClick: () => void;
}) {
  return (
    <button
      onClick={onClick}
      className={
        "rounded-full border px-3 py-1 text-xs transition " +
        (active
          ? "bg-blue-700 border-blue-700 text-white"
          : "border-slate-300 hover:bg-slate-100")
      }
    >
      {children}
    </button>
  );
}
