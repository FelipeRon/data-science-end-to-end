# PSet 2 - Cadena de datos reproducible

Autor: Ron. Reorganización conforme a la rúbrica del curso, 15/11/2026.

## Arquitectura y alcance

La ruta evaluable usa UCI AI4I, Kestra, CSV histórico/limpio, DuckDB, dbt y Spark. La ruta opcional conserva Snowflake RAW/BRONZE/SILVER/GOLD/OBT. Se separan explícitamente porque no son equivalentes ante una rúbrica que exige un mismo archivo limpio y un mismo `.duckdb`.

El target es la falla presente de una observación (t=0). El dataset sintético no ofrece una ventana validada para anticipar fallas futuras ni vida útil restante. Los costos y criterios de negocio siguen siendo propuestas documentadas, no evidencia de rentabilidad.

## Ingesta y calidad

El histórico se acumula por hash del CSV y número de fila original, permitiendo retries/backfill sin duplicar observaciones de una versión. No se pierden duplicados de UDI antes del diagnóstico. El notebook examina todo el histórico persistente, sin depender de un archivo de juguete.

La limpieza comparte código con el notebook: normaliza formatos y tipos, rechaza valores ausentes/inválidos con motivo y deduplica por versión+UDI conservando SOURCE_ROW menor. Se conservan discrepancias target/subtipos. Las filas válidas y rechazadas reconcilian exactamente con el histórico.

## Warehouse y procesamiento

El único archivo limpio canónico es `data/processed/ai4i_clean.csv`. Warehouse valida conteo y clave, y carga DuckDB. dbt implementa staging, intermedia y marts; `dbt run` y `dbt test` usan el mismo archivo `.duckdb`. El mart compara proporción observada de fallas por tipo y versión.

Spark lee el mismo archivo limpio, verifica grano, calcula el agregado y exige igualdad con dbt y Pandas dentro de tolerancia numérica. Los reportes guardan SHA256 del CSV y conteos, por lo que la coincidencia no se basa solo en nombres de archivo.

## Operación

El viernes 08:00 se revisa una fuente estática para detectar versiones nuevas sin descargar diariamente. Solo se reintenta la descarga (3 intentos, 30 segundos) por fallos transitorios de red; los errores deterministas de calidad/modelos fallan de forma visible. El volumen del histórico persiste entre ejecuciones. El flow serializa sus ejecuciones, pero no comandos manuales externos.

No se implementa streaming sin eventos ni necesidad demostrada de baja latencia. Un Codespace detenido no ejecuta el cron. Las instrucciones y limitaciones están en README; la evidencia concreta y el alcance de la validación están en `validacion.md`.
