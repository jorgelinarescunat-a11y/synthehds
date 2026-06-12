import { Link } from "react-router-dom";

export function Layout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-slate-50 text-slate-800">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link to="/" className="flex items-center gap-2">
            <div className="h-8 w-8 rounded bg-blue-700 flex items-center justify-center text-white font-bold text-sm">
              S
            </div>
            <span className="text-lg font-semibold">SynthEHDS</span>
            <span className="text-xs text-slate-400 ml-1">MVP</span>
          </Link>
          <nav className="flex items-center gap-5 text-sm">
            <Link to="/wizard" className="hover:text-blue-700">
              Generar cohorte
            </Link>
            <Link to="/history" className="hover:text-blue-700">
              Historial
            </Link>
          </nav>
        </div>
      </header>
      <main className="mx-auto max-w-6xl px-6 py-10">{children}</main>
      <footer className="mt-16 border-t border-slate-200 py-6 text-center text-xs text-slate-400">
        Datos 100 % sintéticos · EHDS-compliant · No usar para conclusiones clínicas
      </footer>
    </div>
  );
}
