import { Link } from "react-router-dom";
import { Layout } from "../components/Layout";

export function Landing() {
  return (
    <Layout>
      <section className="rounded-lg bg-white p-10 shadow-sm">
        <h1 className="text-3xl font-bold text-slate-900">
          Datos sintéticos de diabetes T2 en España
        </h1>
        <p className="mt-3 text-slate-600 max-w-2xl">
          Genera cohortes realistas pero no sensibles para prototipar modelos
          de IA, validar pipelines clínicos y formar a equipos data science.
          Sin pacientes reales — distribuciones epidemiológicas, Bayesian
          Network y reglas clínicas.
        </p>
        <div className="mt-6 flex gap-3">
          <Link
            to="/wizard"
            className="rounded bg-blue-700 px-5 py-2 text-white text-sm font-medium hover:bg-blue-800"
          >
            Generar cohorte
          </Link>
          <Link
            to="/history"
            className="rounded border border-slate-300 px-5 py-2 text-sm font-medium hover:bg-slate-100"
          >
            Ver historial
          </Link>
        </div>
      </section>

      <section className="mt-8 grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card title="Fuentes oficiales">
          5 estudios españoles (Di@bet.es, BDCAP, SIMETAP, Cantabria,
          RedgedapS) citados en el data sheet PDF.
        </Card>
        <Card title="Estándares de salida">
          CSV plano, FHIR Bundle JSON y OMOP CDM v5.4 (5 tablas).
        </Card>
        <Card title="EHDS-compliant">
          Declaración legal explícita, sin datos identificables,
          uso secundario investigador/formativo.
        </Card>
      </section>
    </Layout>
  );
}

function Card({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-5">
      <h3 className="font-semibold text-slate-800">{title}</h3>
      <p className="mt-2 text-sm text-slate-600">{children}</p>
    </div>
  );
}
