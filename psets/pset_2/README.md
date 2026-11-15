# PSet 2 - Detección de fallas presentes AI4I

La ruta de evaluación cumple la [rúbrica](docs/rubrica.md): **UCI → histórico → diagnóstico → limpiar.py → CSV limpio → DuckDB → dbt staging/intermedia/marts → Spark y reconciliación**. Kestra orquesta la misma imagen definida por Dockerfile/Compose. **Snowflake es obligatorio**: la cadena completa termina con RAW, dbt BRONZE/SILVER/GOLD y Spark OBT. DuckDB se conserva para la conciliación exigida por la rúbrica.

## Estructura versionada

```text
psets/pset_2/
├── docker-compose.yml
├── .env.example
├── README.md
├── kestra/     # flow, calidad/, scripts/ y runtime/Dockerfile + lock
├── dbt/        # staging/intermedia/marts; snowflake/ para Snowflake obligatorio
├── spark/      # job_batch.py y construir_obt.py para OBT Snowflake
└── docs/       # rúbrica, diagnóstico de cambios, documentación y tests/
```

`.gitignore` y `.dockerignore` son configuración oculta. `data/`, `output/`, logs, notebooks ejecutados y bases `.duckdb` se generan en ejecución y no se suben a Git. El directorio anterior `psets/pset-02` se retiró para evitar dos copias activas. Los archivos únicos útiles se trasladaron; lo reemplazado sigue recuperable en el historial.

## Ejecutar desde un Codespace nuevo

1. Abrir la rama **Felipe** en Codespaces. Para un Codespace existente, desde la raíz del repo ejecutar `git pull --ff-only origin Felipe` sin descartar cambios locales. La configuración `.devcontainer` usa Docker-in-Docker y requiere al menos 4 núcleos. Reconstruir el contenedor para aplicar cambios de configuración.
2. Configurar Codespaces Secrets:  `SECRET_SNOWFLAKE_PRIVATE_KEY` (Base64 del PEM privado completo) y `SECRET_SNOWFLAKE_KEY_PASSWORD` (Base64 de la contraseña; vacío si no está cifrada). Autorizar el repositorio y detener/iniciar el Codespace para recibirlos. Ver [credenciales y permisos](docs/credenciales_codespaces.md).

3. Ejecutar desde la raíz del repositorio:

```bash
cd psets/pset_2
bash kestra/scripts/codespaces.sh start
bash kestra/scripts/codespaces.sh run
```

**La cadena completa requiere Snowflake y sus credenciales.** `start` migra configuraciones anteriores a `PIPELINE_TARGET=snowflake`; sin clave privada se detiene. La primera descarga de imágenes puede tardar varios minutos. `start` prepara `.env`, genera contraseñas locales aleatorias, construye `pset2-pipeline:local`, levanta PostgreSQL/Kestra e importa el código de namespace. `run` vuelve a importar el código actual, ejecuta y espera el estado final. No ejecutar `run` después de modificar dependencias sin volver a ejecutar `start` para reconstruir la imagen.

4. En **Ports**, abrir **8080** con visibilidad **Private**. Para consultar las credenciales locales generadas, ejecutar deliberadamente:

```bash
bash kestra/scripts/codespaces.sh credentials
```

No compartir su salida. El flow es `pset_2.descargar_ai4i`; las tres tareas deben terminar en `SUCCESS`. Al terminar, el cliente exporta a tu Codespace `data/raw/historico.csv`, `data/processed/ai4i_clean.csv`, `output/cadena_local.json` y `output/diagnostico_ejecutado.ipynb`. Son copias de consulta del volumen persistente; ninguna se versiona.

## Cadena y archivos exactos

| Paso | Implementación | Entrada y salida |
| --- | --- | --- |
| Histórico | `kestra/scripts/ingesta_historico.py` | CSV real UCI a `data/raw/historico.csv`; SHA256 y fila de origen evitan duplicar retries. |
| Diagnóstico | `kestra/calidad/diagnostico.ipynb` | Lee todo el histórico acumulado; documenta verificación, estrategia y porqué de cada problema. Se ejecuta automáticamente, sin abrirlo a mano. |
| Limpieza | `kestra/calidad/limpiar.py` | Histórico a `data/processed/ai4i_clean.csv`, rechazados con motivo y `output/calidad_local.json`. Comparte funciones con el notebook. |
| Warehouse | `kestra/scripts/warehouse_local.py` | Lee únicamente el CSV limpio y carga `raw.ai4i_clean` en `data/warehouse/pset2.duckdb`; compara filas y unicidad. |
| dbt | `dbt/` | `dbt run` y `dbt test` usan exactamente ese mismo `.duckdb`, por `PSET2_DUCKDB_PATH`. |
| Spark | `spark/job_batch.py` | Lee el mismo CSV limpio, agrega por tipo/versión y exige igualdad con dbt y Pandas. |

`PSET2_DATA_DIR=/workspace/data` apunta al volumen persistente `pset_2_history`. Kestra lo monta en su runner y Compose lo usa para ejecuciones manuales. El límite de concurrencia del flow es 1; no lanzar a la vez ejecuciones manuales, porque ese límite no las protege. Cambiar el nombre del volumen crea otro histórico, no lo migra.

El mart `mart_fallas_por_tipo` responde: **¿qué tipo de producto presenta mayor proporción observada de fallas?** Incluye observaciones, fallas, tasa y torque medio por versión y tipo. Es descriptivo, sin interpretación causal ni pronóstico del siguiente ciclo. Ver el [diagrama de arquitectura](docs/arquitectura.mmd) y el [modelo dimensional de Snowflake](docs/modelo_dimensional.mmd).

## Reintento y horario justificados

- UCI es un ZIP estático. Una comprobación **semanal, viernes 08:00 America/Guayaquil**, permite detectar cambios de versión sin descargarlo cada día. Es una revisión académica de integridad propuesta, no llegada de datos de sensores ni un SLA de planta. El hash distingue versiones.
- Solo la descarga tiene `maxAttempts: 3`, `interval: PT30S`: tolera fallos breves de red/HTTP sin insistir continuamente contra UCI. Si persiste el error, falla de forma visible.
- No se reintentan automáticamente errores deterministas de contrato, limpieza, SQL o reconciliación: se revisan los logs y el diagnóstico. Reejecutar después de corregirlos no duplica el histórico.
- `Dockerfile` está en `kestra/runtime/`; Compose construye desde la raíz con ese archivo. Tanto Compose como el flow usan **`pset2-pipeline:local`**, sin un segundo tag divergente. Tras reconstruir el Codespace, ejecutar `start` para restablecer la imagen local.

## Backfill y pruebas

```bash
# Reprocesar un lote; no inventa fechas de medición.
bash kestra/scripts/codespaces.sh run --batch-id 0 --batch-size 1000

# Encolar y esperar todos los lotes en orden.
bash kestra/scripts/codespaces.sh backfill --batch-size 1000

# Pruebas sin servicios ni credenciales externas.
bash kestra/scripts/codespaces.sh test
```

Con tamaño 1000, los lotes válidos son 0..9; `-1` selecciona toda la fuente. El volumen acumula lotes por SHA256 y fila original. La limpieza conserva una sola observación válida por versión y UDI, audita duplicados y mantiene versiones distintas.

## Ejecutar etapas manualmente

Después de `start` o de preparar y construir la imagen:

```bash
docker compose run --rm pipeline
docker compose run --rm pipeline python kestra/calidad/limpiar.py
docker compose run --rm spark
```

La primera orden ejecuta **toda** la cadena, incluidos notebook, `dbt run` y `dbt test`. Los archivos se mantienen dentro del mismo volumen y los reportes quedan en `output/`. Para inspeccionar el CSV canónico sin cambiar el volumen:

```bash
docker compose run --rm pipeline python -c "import pandas as pd; d=pd.read_csv('/workspace/data/processed/ai4i_clean.csv'); print(d.shape)"
```

`output/cadena_local.json` debe indicar el mismo conteo y hash del CSV para warehouse/Spark, `dbt_run=SUCCESS`, `dbt_test=SUCCESS`, `spark_matches_dbt=true` y `spark_matches_pandas=true`. La ejecución completa validada tuvo 10.000 filas y tres grupos del mart. Ver [cumplimiento de rúbrica](docs/cumplimiento_rubrica.md) y [validación](docs/validacion.md).

## Snowflake obligatorio

Para ejecutar el alcance obligatorio Raw/Bronze/Silver/Gold/OBT de Snowflake, configurar claves **nuevas** mediante Codespaces Secrets como explica [credenciales_codespaces.md](docs/credenciales_codespaces.md). La clave anteriormente versionada debe rotarse; quitarla del último commit no la elimina del historial.

```bash
PIPELINE_TARGET=snowflake bash kestra/scripts/codespaces.sh start
bash kestra/scripts/codespaces.sh run --target snowflake
```

La cadena ejecuta primero todas las verificaciones DuckDB y luego la carga/modelado Snowflake. El proyecto dbt/snowflake conserva source/ref, Bronze/Silver/Gold, hechos/dimensiones y tests; `spark/construir_obt.py` construye la OBT en Snowflake. Los esquemas/roles se preparan con los SQL de `kestra/scripts/` por un administrador. Snowflake necesita permisos y secretos reales. `output/cadena_local.json` acredita solo la conciliación local; `output/cadena_completa.json` se genera únicamente después de completar Snowflake. Esta corrección se realizó sin ejecutar pruebas ni el pipeline.

## Alcance, datos y mantenimiento

AI4I permite detección del estado presente (t=0), no RUL ni predicción del próximo ciclo. El notebook documenta nulos, duplicados, tipos, formatos y discrepancias sin inventar problemas. Los 27 desacuerdos target/subtipos se conservan porque no hay verdad independiente. Los costos y reglas de expertos propuestos se mantienen en [negocio_y_decision.md](docs/negocio_y_decision.md); son supuestos, no ahorro demostrado.

Se usa **batch** porque la fuente es estática y una revisión semanal no requiere baja latencia. Streaming solo se justificaría con telemetría continua y acciones que pierdan valor en segundos/minutos; no existe esa fuente ni SLA validado, por lo que no se implementa productor/broker/consumidor innecesarios.

```bash
bash kestra/scripts/codespaces.sh status
docker compose logs --tail 80 kestra postgres
bash kestra/scripts/codespaces.sh stop
```

No usar `down -v` para diagnosticar: eliminaría datos persistentes. El proyecto Compose nuevo se llama `pset_2`; los volúmenes anteriores de `pset2` no se borran ni migran automáticamente. La lista de archivos retirados/movidos está en [limpieza del repositorio](docs/limpieza_repositorio.md).
