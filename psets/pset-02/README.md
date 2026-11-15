<<<<<<< HEAD
# PSet 2: Pipeline de datos del proyecto

**Asignado:** Semana 4, Sesión 1. **Vence:** Semana 7, Sesión 2.

El pipeline de datos de tu proyecto, corriendo de principio a fin: la ingesta que contenerizaste en el PSet 1, orquestada, con la calidad de los datos resuelta, cargada a un warehouse y modelada en capas. Cada pieza la construiste en el Ejercicio 3 de una sesión de las Semanas 4 a 6, y el Laboratorio Integrador (Semana 7, Sesión 1) las conecta. Lo que se califica es que la cadena funcione completa: que cada etapa entregue exactamente el archivo o la tabla que la siguiente lee.

## Entregables

Todo en [`../proyecto/`](../proyecto/), en estas carpetas:

| Pieza | Dónde | Sale de |
|---|---|---|
| El flow de Kestra, con reintento y horario | `orquestacion/flow_proyecto.yml` | Semana 4, Sesión 1 |
| El diagnóstico de calidad | `calidad/diagnostico_proyecto.ipynb` | Semana 4, Sesión 2 |
| La limpieza, como script | `calidad/limpiar.py` | Semana 7, Sesión 1 |
| La carga a DuckDB | `warehouse/construir_warehouse.py` | Semana 5, Sesión 1 |
| El modelado en capas | `warehouse/dbt/` | Semana 5, Sesión 2 |
| El job de Spark sobre el histórico | `procesamiento/job_spark.py` | Semana 6, Sesión 1 |
| Streaming, si tu proyecto lo justifica | `procesamiento/productor.py` y `procesamiento/consumidor.py` | Semana 6, Sesión 2 |

Si corregiste el `Dockerfile`, la ingesta o la infraestructura del PSet 1 para que la cadena funcione, esos cambios también entran: el pipeline corre sobre la versión actual.

En `proyecto/README.md`, completa la sección **Cómo correr el pipeline de datos**: los comandos, en orden y desde qué carpeta, para ir de la fuente al warehouse. Al final de esa sección, un párrafo que diga si tu proyecto necesita streaming o le alcanza con batch, con el criterio de la Semana 6, Sesión 2: ¿la decisión que habilita tu proyecto pierde valor con datos de horas o días de antigüedad?

## Lo que reviso

Sigo tu `README.md` desde un Codespace nuevo, comando por comando. Si un paso necesita algo que no está escrito (una carpeta que hay que crear a mano, una variable que solo existe en tu máquina, un archivo que no está en el repositorio ni dice cómo obtenerlo), la cadena se corta ahí.

Los mismos cruces de la checklist del integrador: el flow corre el tag actual de tu imagen; `limpiar.py` corre sobre el histórico que acumuló tu pipeline, no sobre un archivo de ejemplo; el warehouse carga el archivo limpio y su cuenta de filas coincide con la del archivo; `dbt run` y `dbt test` usan el mismo `.duckdb` que construyó la carga; y el resultado de Spark coincide con el de dbt o pandas sobre el mismo dato.

## Cómo se evalúa

La rúbrica, con sus cuatro criterios y niveles, está en [`rubrica.md`](./rubrica.md). Para entregar, sigue la sección "Cómo entregar" de [`psets/README.md`](../README.md): el tag de este PSet es `pset-02`.
=======
# PSet 2 - Detección de fallas presentes con AI4I

Pipeline batch reproducible: **UCI → Kestra → Snowflake RAW → dbt BRONZE/SILVER/GOLD → Spark → Snowflake OBT**.

La fuente es [AI4I 2020 de UCI](https://archive.ics.uci.edu/dataset/601/ai4i+2020+predictive+maintenance+dataset), un CSV sintético de 10.000 observaciones. No contiene marcas de tiempo de las mediciones: el horario del flow representa una revisión programada de la fuente, no llegada de nuevos sensores.

**Formulación corregida tras el PSet 1:** el target es la falla de la lectura actual, con horizonte `t=0`. Este proyecto no estima vida útil ni la falla del siguiente ciclo. La acción propuesta es priorizar revisión humana, sin paradas automáticas. La selección se basa en correspondencia entre datos, target y acción; la utilidad en planta sigue condicionada a datos y costos reales.

## Estructura

```text
pset-02/
  docker-compose.yml       # Kestra, PostgreSQL, Spark y runner del pipeline
  Dockerfile               # Python 3.11, Java 17, Spark 3.5.5 y dbt Snowflake 1.9.4
  requirements.lock.txt    # Versiones exactas del entorno verificado
  .env.example
  kestra/                  # Flow e ingesta; claves y .env.kestra solo locales
  dbt/                     # Bronze, Silver, Gold y tests
  spark/construir_obt.py   # Joins y validación de la OBT
  scripts/                 # Preparación, carga a Kestra y backfill
  tests/                   # Casos de lotes, joins y errores
  docs/                    # Memo técnico, diagramas y evidencia
  output/                  # Reportes JSON de cada ejecución; no versionar
```

Las carpetas `plantilla-dbt/` y `plantilla-spark/`, si siguen presentes, se conservan como referencia original; el pipeline usa `dbt/` y `spark/`. El antiguo Compose dentro de `kestra/` es una configuración anterior: ejecutar los comandos desde la raíz con el nuevo Compose.

## 1. Preparación local

Requiere Docker Desktop con contenedores Linux, Docker Compose >= 2.24 y PowerShell 7 (`pwsh`). Recomendada una máquina con al menos 4 núcleos y 8 GB de memoria disponibles para los contenedores.

Desde PowerShell, en la raíz del proyecto:

```powershell
Set-Location 'C:\Users\ronfe\Desktop\Pset2\psets\pset-02'
pwsh -File .\scripts\preparar.ps1
docker compose build pipeline
docker compose up -d
docker compose ps
```

`preparar.ps1` genera `.env` desde `.env.example` si no existe, reutiliza la contraseña Base64 de `kestra/.env.kestra` y comprueba la clave local `kestra/pset2_kestra.p8`. No imprime ni sobrescribe secretos existentes. Si cambia la cuenta/warehouse/usuario, ajustar `.env` y las variables no secretas del flow.

Kestra: [http://localhost:8080](http://localhost:8080), usuario local `admin@kestra.io`, contraseña local `Admin1234`. Esperar a que termine de iniciar; para diagnosticar:

```powershell
docker compose logs --tail 80 kestra postgres
```

La imagen `pset2-pipeline:local` debe existir en el mismo Docker que usa Kestra. El runner tiene `pullPolicy: NEVER`: utiliza la imagen construida localmente.

## 2. Snowflake y credenciales

Configuración del proyecto existente:

| Parámetro | Valor |
| --- | --- |
| Cuenta | `MRIWLBX-HH95628` |
| Usuario | `PSET2_KESTRA` |
| Rol | `PSET2_INGEST` |
| Warehouse | `PSET2_WH` (X-Small, auto-suspend recomendado 60 s) |
| Base de datos | `PSET2_MANTENIMIENTO` |
| Esquemas | `RAW`, `BRONZE`, `SILVER`, `GOLD`, `OBT` |

En una cuenta nueva, un administrador ejecuta `scripts/bootstrap.sql`, adaptando nombres y creando/asociando previamente el usuario y su clave pública. Para esta cuenta, si faltan permisos sobre la base/esquemas existentes, ejecutar `scripts/permisos_pendientes.sql` en Snowsight con un rol autorizado. El pipeline no eleva su rol ni usa ACCOUNTADMIN.

La clave privada se conserva en `kestra/pset2_kestra.p8`, montada en solo lectura para ejecución manual. Para Kestra se reutiliza `kestra/.env.kestra`:

```dotenv
SECRET_SNOWFLAKE_PRIVATE_KEY=<Base64 del PEM completo de la clave privada>
SECRET_SNOWFLAKE_KEY_PASSWORD=<Base64 de la contraseña de cifrado, o valor vacío>
```

`secret()` de Kestra decodifica la envoltura Base64; el Python del proyecto admite PEM o DER Base64. La contraseña de cifrado de la clave es distinta de la contraseña de Snowsight. `.env` usa `SNOWFLAKE_PRIVATE_KEY_PASSWORD_B64` para evitar problemas con caracteres especiales.

Después de modificar `.env.kestra`:

```powershell
docker compose up -d --force-recreate kestra
```

No subir `.env`, `.env.kestra`, claves privadas, backups ni `output/`. Las exclusiones están en `.gitignore` y `.dockerignore`. Si una clave ya se publicó, rotarla; ignorarla después no la retira del historial.

## 3. Ejecutar desde Kestra

```powershell
pwsh -File .\scripts\subir_a_kestra.ps1 -Execute
```

El script sube el árbol de código al namespace preservando sus rutas, crea/actualiza `pset2.descargar_ai4i` y muestra el ID de ejecución. En Kestra comprobar las tareas `descargar`, `extraer` y `pipeline`. No usar el antiguo script que solo subía `ingesta_csv.py`: ahora se necesitan también dbt, Spark y los módulos compartidos.

La tarea `pipeline` ejecuta en orden:

1. Ingesta: contrato del CSV, staging temporal, `write_pandas` y `MERGE` a `RAW.AI4I_OBSERVATIONS`.
2. `dbt debug` y `dbt build`: crea Bronze, Silver, Gold y ejecuta tests.
3. Spark: lee Gold, valida claves/joins, calcula features y escribe `OBT.AI4I_OBT`.
4. Evaluación de referencia: calcula confusión de la regla versionada y sensibilidad de costos, guardando `negocio.json`; no entrena un modelo ni declara ahorros reales.

Cualquier error hace fallar la tarea y el flow. Hay retries de descarga y del pipeline (intervalo 30 s, `maxAttempts: 3`), y un handler de error. Repetir el pipeline es seguro respecto a RAW porque su clave es `(SOURCE_SHA256, UDI)`; Gold se reconstruye con dbt y la OBT se publica solo tras validar la tabla nueva. El límite de concurrencia de Kestra es 1. No lanzar ejecuciones manuales por Docker al mismo tiempo que Kestra, porque ese límite solo protege ejecuciones del flow.

El trigger es **viernes a las 08:00, America/Guayaquil** y carga la fuente completa por defecto. Como AI4I es estático, una reejecución del mismo archivo inserta cero filas nuevas. Una revisión del contenido produce otro SHA256 y se conserva como otra versión; no equivale a nuevas observaciones independientes para entrenar un modelo.

## 4. Backfill reproducible

Los lotes se definen por posición tras ordenar UDI: no se inventan fechas de medición.

```powershell
# Reprocesar el lote 0 (primeras 1000 filas).
pwsh -File .\scripts\subir_a_kestra.ps1 -Execute -BatchId 0 -BatchSize 1000

# Encolar los 10 lotes; Kestra los procesa en serie.
pwsh -File .\scripts\backfill.ps1
```

`batch_id=-1` significa fuente completa. Con tamaño 1000, los IDs válidos son 0..9; tamaños no positivos o índices fuera de rango fallan explícitamente. Si el dataset ya está cargado, repetir los lotes debe mantener el conteo de RAW, sin duplicados. En una base vacía los lotes acumulan los registros; dbt/Spark procesan el histórico acumulado después de cada lote.

## 5. Ejecutar herramientas manualmente

Siempre desde la raíz, después de preparar `.env` y construir la imagen:

```powershell
# Recorrido completo sin scheduler.
docker compose run --rm pipeline

# Solo dbt (el wrapper prepara la clave efímera que usa el perfil).
docker compose run --rm pipeline sh scripts/dbt.sh build

# Solo OBT con Spark, requiere Gold construido.
docker compose run --rm spark

# Tests de lotes, joins, duplicados y huérfanos; no usan Snowflake.
docker compose run --rm pipeline pytest -q
```

El perfil dbt y el macro `generate_schema_name` publican exactamente en `BRONZE`, `SILVER` y `GOLD`, sin prefijos adicionales. La clave descifrada se suministra a dbt como variable `DBT_ENV_SECRET_PRIVATE_KEY`; no se guarda en el perfil.

## 6. Calidad, grano y OBT

RAW conserva las 14 columnas originales como texto, más hash, URL, lote y timestamp de carga. La ingesta valida el contrato de 10.000 filas y UDI único; no imputa ni elimina registros por reglas de negocio.

Bronze tipa y normaliza. Silver clasifica registros válidos/rechazados y registra el motivo; no hay descartes silenciosos. Se validan nulos, dominios, coherencia del tipo de producto y banderas binarias. Las discrepancias target/subtipos se conservan, porque no hay una referencia independiente que permita decidir cuál corregir. `SILVER.QUALITY_REPORT` presenta métricas por hash.

La auditoría directa de UCI realizada el 12/11/2026 obtuvo **10.000 filas, 14 columnas, 0 celdas nulas, 0 UDI duplicados, 339 fallas (3,39%) y 27 discrepancias target/subtipos**. Esta evidencia de fuente es distinta de la evidencia de ejecución Snowflake, registrada en `docs/validacion.md`.

Gold: `FACT_READING` al grano `(source_sha256, udi)`, dimensiones `DIM_PRODUCT` y `DIM_SOURCE`. Los tests verifican claves únicas/no nulas, categorías, relaciones, dominios y reconciliación Raw/Silver/Gold. Ver los diagramas y decisiones en `docs/`.

Spark realiza los joins y comprueba que cada dimensión tenga una sola fila por clave, que no haya huérfanos y que conteo/unicidad no cambien. Calcula delta de temperatura y potencia mecánica. Excluye los flags de subtipo de la OBT para evitar fuga del target. `MACHINE_FAILURE` es la etiqueta, no una feature; IDs, hashes, procedencia y fecha de carga tampoco deben usarse como features. El dataset carece de horizonte de predicción temporal; valida clasificación sobre observaciones sintéticas, no demuestra anticipación de fallas futuras.

La OBT añade `BASELINE_ALERT` y `BASELINE_RULE_VERSION` como referencias de comparación, **excluidas de las features**. La candidata a regla de expertos `UCI_PHYSICS_WEAR200_v1` está documentada y ejecutada en `scripts/decision_policy.py`; falta aprobación de mantenimiento. Los parámetros de planta, costos, sensibilidad y criterios de aceptación están en `scripts/business_assumptions.json`.

El caso ilustrativo usa USD 50 por inspección y USD 2000 por demora de una falla omitida, con costo también para una alerta correcta. Para una futura probabilidad calibrada del estado actual, el umbral es `50/2000 = 2,5%`, no el rango 60-70% del pitch. Los nueve escenarios cambian ese umbral entre 0,625% y 10%. **Aún no existe una probabilidad de modelo en este PSet**; la regla es binaria.

El reporte `negocio.json` se calcula por versión de fuente. No proyecta las filas a semanas/años ni considera toda reparación como evitable. Para justificar un futuro modelo se propone >=10% de reducción de costo frente a la mejor referencia, IC95% de ahorro con límite inferior >0, recall >=80%, precisión >=30%, <=5 revisiones/día y beneficio neto positivo tras costos fijos. Todo ello requiere validación con datos reales y patrocinador, no se presenta como ya alcanzado.

El reporte incluye sensibilidad al margen por hora y al volumen de oportunidades por equipo/día. El dimensionamiento operativo supone explícitamente la mezcla sintética para examinar capacidad; no es una predicción de incidentes reales ni una anualización de las filas.

Ver [contrato de decisión y respuesta a los ocho comentarios](docs/negocio_y_decision.md): comparación de las tres ideas, consecuencias de errores RUL, procedimiento CMMS/ERP para estimar costos, entregables por etapa y solicitud concreta de acceso al patrocinador.

```powershell
# Recalcular la referencia y sensibilidad sobre la OBT existente.
docker compose run --rm pipeline python scripts/evaluar_negocio.py
```

Para 10.000 filas, el conector Python transporta datos a/desde Snowflake y Spark ejecuta las transformaciones en `local[2]`. El uso de `fetch_pandas_all/toPandas` limita la escala al driver; para mayor volumen se requiere un conector distribuido Spark-Snowflake.

## 7. Verificar resultados

Los JSON de ingesta, calidad, OBT y negocio quedan como outputs de la tarea Kestra o en `output/` al ejecutar Compose. También se conservan `manifest.json` y `run_results.json` de dbt. Los costos de negocio son supuestos identificados, separados de las métricas observadas.

```sql
SELECT SOURCE_SHA256, COUNT(*) AS FILAS, COUNT(DISTINCT UDI) AS UDI_UNICOS
FROM PSET2_MANTENIMIENTO.RAW.AI4I_OBSERVATIONS GROUP BY 1;
SELECT * FROM PSET2_MANTENIMIENTO.SILVER.QUALITY_REPORT;
SELECT COUNT(*) FROM PSET2_MANTENIMIENTO.GOLD.FACT_READING;
SELECT COUNT(*), COUNT(DISTINCT READING_KEY)
FROM PSET2_MANTENIMIENTO.OBT.AI4I_OBT;
```

Para una sola versión completa sin rechazos, los conteos son 10.000. Después de reejecutar deben permanecer iguales y el reporte de ingesta debe mostrar `inserted_rows: 0`.

## 8. Entrega y límites

`docs/memo_tecnico.md` contiene el documento técnico editable; `docs/PSet2_memo_Ron.pdf` tiene 6 páginas y autor Ron. Antes de entregar, ajustar el nombre con los apellidos reales al formato solicitado `PSet2_memo_<apellido_1>_<apellido_2>.pdf`. Revisar los resultados reales en `docs/validacion.md`.

Se usa batch por tratarse de una fuente estática y una revisión semanal suficiente para esta práctica. Streaming se justificaría con telemetría continua y decisiones con latencia de segundos; requeriría fuente de eventos, tiempos de evento, deduplicación, watermarking y almacenamiento incremental. No se implementa streaming.

Para detener conservando datos: `docker compose down`. No usar `down -v` si se desean conservar los metadatos de Kestra. Los volúmenes del antiguo Compose pueden tener otro nombre; este proyecto raíz usa el nombre `pset2` y no migra ni elimina automáticamente sus volúmenes anteriores.

Referencias: enunciado `CD_PSet_2 (1).pdf`, [secretos Kestra](https://kestra.io/docs/how-to-guides/secrets), [dbt schemas](https://docs.getdbt.com/docs/build/custom-schemas), [Snowflake Python/pandas](https://docs.snowflake.com/en/developer-guide/python-connector/python-connector-pandas).
>>>>>>> 7af60a9 (Pset2V1)
