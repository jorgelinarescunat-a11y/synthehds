# SynthEHDS

Generador de datasets sintéticos de pacientes con **diabetes tipo 2 en
España**, alineado con los principios del **European Health Data Space
(EHDS)** para uso secundario de datos de salud en investigación,
prototipado de modelos de IA y formación en data science clínica.

> ⚠️ Este proyecto **no usa datos reales** de pacientes. Genera datos
> completamente sintéticos a partir de distribuciones estadísticas
> públicas, reglas clínicas codificadas y modelos probabilísticos.

---

## Tabla de contenidos

- [Stack](#stack)
- [Instalación y arranque](#instalación-y-arranque)
- [Uso](#uso)
- [Estructura del proyecto](#estructura-del-proyecto)
- [Metodología](#metodología)
- [Fuentes científicas](#fuentes-científicas)
- [Limitaciones del MVP](#limitaciones-del-mvp)
- [Tests](#tests)
- [Licencia](#licencia)

---

## Stack

| Capa            | Tecnología |
|-----------------|------------|
| Backend         | Python 3.11+, FastAPI, Pydantic v2 |
| Generación stat | pandas, numpy, scipy, **pgmpy** (Bayesian Network), faker |
| LLM (opcional)  | Anthropic Claude (notas SOAP en español) |
| Frontend        | React + Vite + TypeScript + Tailwind CSS + Recharts |
| Persistencia    | SQLite local (preparado para PostgreSQL) |
| Estándares      | CSV, **FHIR R4 Bundle JSON**, **OMOP CDM v5.4** |
| PDF data sheet  | reportlab |
| Testing         | pytest |

---

## Instalación y arranque

### 1. Backend

```bash
cd backend
python -m venv .venv

# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt

# Variables de entorno
cp ../.env.example ../.env
# Edita ../.env y, si quieres notas clínicas, añade ANTHROPIC_API_KEY=sk-…

# Arranca la API
uvicorn app.main:app --reload --port 8000
```

- Health check: <http://localhost:8000/health>
- Docs interactivos (Swagger): <http://localhost:8000/docs>

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

Vite arranca en <http://localhost:5173>. Hay un proxy configurado contra
`localhost:8000`, así que no hace falta tocar nada de CORS si arrancas
ambos en paralelo.

---

## Uso

1. Abre <http://localhost:5173>.
2. Click en **Generar cohorte** → completa el wizard:
   - tamaño 50–10 000,
   - rango de edad, distribución de sexo, región,
   - comorbilidades a forzar/excluir,
   - notas clínicas con Claude (sí/no),
   - seed (opcional, para reproducibilidad).
3. Polling de progreso → pantalla de resultados con:
   - 20 filas de preview,
   - gráficos comparando distribuciones observadas vs YAML,
   - cards con métricas de calidad,
   - descargas: **CSV**, **FHIR Bundle**, **OMOP**, **Data sheet PDF**.
4. **Historial** lista todas las cohortes generadas.

### Endpoints REST

| Método | Ruta | Descripción |
|---|---|---|
| `POST` | `/api/cohorts/generate` | Inicia un job — devuelve `job_id` |
| `GET`  | `/api/cohorts/{job_id}/status` | Estado: `queued`/`running`/`done`/`failed` |
| `GET`  | `/api/cohorts/{job_id}/data?format=csv\|fhir\|omop` | Descarga del dataset |
| `GET`  | `/api/cohorts/{job_id}/metrics` | JSON con las 4 métricas de calidad |
| `GET`  | `/api/cohorts/{job_id}/preview?limit=20` | Vista previa para UI |
| `GET`  | `/api/cohorts/{job_id}/datasheet` | PDF firmado con metodología y citas |
| `GET`  | `/api/cohorts` | Historial paginado |

La generación corre en `BackgroundTasks` de FastAPI (suficiente para
MVP; migración a Celery/RQ trivial).

---

## Estructura del proyecto

```
synthehds/
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app + CORS + startup
│   │   ├── api/
│   │   │   ├── cohorts.py           # endpoints /api/cohorts/*
│   │   │   └── storage.py           # SQLite vía SQLAlchemy
│   │   ├── generators/
│   │   │   ├── bayesian_model.py    # Bayesian Network (pgmpy)
│   │   │   ├── pipeline.py          # cohorte + encuentros + faker
│   │   │   └── yaml_loader.py
│   │   ├── models/cohort.py         # modelos Pydantic
│   │   ├── exporters/
│   │   │   ├── csv_exporter.py
│   │   │   ├── fhir_exporter.py     # FHIR R4 Bundle
│   │   │   ├── omop_exporter.py     # OMOP CDM v5.4 (5 tablas)
│   │   │   └── datasheet.py         # PDF reportlab
│   │   ├── narratives/claude_notes.py   # notas SOAP con Claude (opt)
│   │   ├── quality/metrics.py       # fidelidad, correlación, privacidad, coherencia
│   │   ├── vocabularies/            # ICD-10, SNOMED-CT, ATC, LOINC
│   │   └── data/
│   │       └── diabetes_t2_spain.yaml   # fuente de verdad
│   ├── tests/                       # pytest
│   ├── pytest.ini
│   └── requirements.txt
├── frontend/
│   ├── index.html
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   └── src/
│       ├── main.tsx + index.css
│       ├── components/Layout.tsx
│       ├── lib/api.ts               # cliente fetch
│       └── pages/
│           ├── Landing.tsx
│           ├── Wizard.tsx
│           ├── JobProgress.tsx
│           ├── Results.tsx
│           └── History.tsx
├── .env.example
└── README.md
```

---

## Metodología

Enfoque **híbrido en cuatro capas**, ninguna usa datos reales como
entrenamiento:

### 1. Distribuciones estadísticas

Cada prevalencia, media y desviación está extraída de literatura
española revisada por pares y guardada en
[`backend/app/data/diabetes_t2_spain.yaml`](backend/app/data/diabetes_t2_spain.yaml).
Cada valor lleva un comentario `# [N]` con la cita de origen.

### 2. Reglas clínicas codificadas

Recomendaciones de prescripción (`reglas_prescripcion` en el YAML) se
implementan en las CPTs de la red bayesiana y en la lógica de
filtrado del pipeline.

### 3. Bayesian Network (pgmpy)

`backend/app/generators/bayesian_model.py` define **18 nodos discretos**
(demografía, control glucémico, comorbilidades, fármacos) y **22
aristas**. Cada `TabularCPD` lleva un docstring `fuente:` que indica
qué valor del YAML la justifica.

Las variables continuas (HbA1c %, IMC, biomarcadores, presión arterial,
FGe) se muestrean a posteriori con distribuciones normales truncadas
**condicionadas a las categorías** que produce la BN.

Los **encuentros longitudinales** (3-5 visitas en 1-3 años por paciente)
evolucionan estocásticamente: la HbA1c tiende a mejorar si el
tratamiento es coherente con las reglas del YAML, y empeora con
probabilidad de no adherencia ≈ 20 %.

### 4. Claude — solo para narrativa, nunca para estadística

Si el usuario activa el flag `generar_notas_clinicas`, cada encuentro
incluye una **nota SOAP en español médico** (80-150 palabras) generada
por `claude-sonnet-4-5`. El LLM **solo parafrasea** los datos
estructurados que ya produjo la BN — no inventa cifras. Hay caché por
hash de inputs para no regenerar notas idénticas. Si la API falla,
el encuentro queda sin nota y el pipeline continúa.

---

## Fuentes científicas

Las cinco fuentes se citan **íntegramente** tanto en el YAML como en
el data sheet PDF que acompaña a cada dataset:

1. **Soriguer F, Goday A, Bosch-Comas A, et al.** *Prevalence of diabetes
   mellitus and impaired glucose regulation in Spain: the Di@bet.es Study.*
   Diabetologia. 2012;55:88-93.
2. **Ministerio de Sanidad.** *Prevalencia de diabetes mellitus en 2016 en
   España según la Base de Datos Clínicos de Atención Primaria (BDCAP).*
   Endocrinología, Diabetes y Nutrición. 2021. DOI:
   10.1016/j.endinu.2020.03.019
3. **Ruiz-García A, et al.** *Prevalencia de diabetes mellitus en el ámbito
   de la atención primaria española y su asociación con factores de riesgo
   cardiovascular. Estudio SIMETAP-DM.* Clínica e Investigación en
   Arteriosclerosis. 2020.
4. *Estudio Cantabria sobre retinopatía diabética.* Atención Primaria.
   2020. DOI: 10.1016/j.aprim.2018.09.004
5. **Mata-Cases M et al. RedgedapS.** *Características clínicas y
   tratamiento antidiabético en DM2 en atención primaria española.*
   Medicina de Familia SEMERGEN. 2021.

---

## Limitaciones del MVP

- **No es validación clínica.** Los datasets sirven para prototipado,
  benchmarking metodológico y formación — nunca para conclusiones
  médicas ni para entrenar modelos que se usarán en producción
  asistencial.
- **No genera imagen médica** (radiografías, OCT, etc.), datos
  genómicos ni señales fisiológicas (ECG, EEG).
- **Cobertura clínica acotada** a diabetes tipo 2 en población adulta
  española. Otros perfiles (DM1, gestacional, pediátrica) no están
  modelados.
- **Temporalidad limitada** a un horizonte de 1-3 años con 3-5
  encuentros — no captura trayectorias completas multidécada.
- **Variables continuas via normal truncada** — no se modelan colas
  pesadas ni mixtures. Para investigación que requiera distribuciones
  más realistas (p. ej. triglicéridos lognormal), conviene
  post-procesar.
- **OMOP**: rellenamos `*_source_value` con códigos ICD-10/ATC/LOINC
  pero dejamos `*_concept_id = 0`. Los pipelines OHDSI deben mapear
  vía ATHENA antes de usarlo en estudios reales.
- **Generación asíncrona simple** con `BackgroundTasks` — apta para
  MVP local; para producción con concurrencia alta, usar Celery/RQ.
- **Frontend mínimo** — no incluye autenticación, gestión de usuarios
  ni multi-tenancy. Una sola instancia local.

---

## Tests

```bash
cd backend
pytest -v
```

Cobertura actual:

| Módulo | Tests |
|---|---|
| `bayesian_model.py` | 12 — estructura, rangos, marginales (vs YAML), correlaciones |
| `pipeline.py` | 6 — tamaño, IDs únicos, filtros forzar/excluir, rango etario |
| `exporters/*` | 7 — columnas CSV, estructura FHIR, tablas OMOP |
| `quality/metrics.py` | 4 — fidelidad, correlaciones direccionales, privacidad, coherencia |
| `api/*` | 1 ciclo end-to-end completo (generación → descargas → PDF) |

---

## Variables de entorno

Copia `.env.example` a `.env` y rellena lo necesario:

```env
ANTHROPIC_API_KEY=         # opcional, solo si quieres notas SOAP
DATABASE_URL=sqlite:///./synthehds.db
ENVIRONMENT=development
CORS_ORIGINS=http://localhost:5173
```

---

## Licencia

Pendiente de definir. Si reutilizas el código, **cita las cinco fuentes
científicas** anteriores en tu publicación o aplicación derivada.
