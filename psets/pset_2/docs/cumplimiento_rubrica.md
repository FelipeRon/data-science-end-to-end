# Correspondencia con la rúbrica

Esta matriz indica implementación y evidencia, no asigna una nota ni garantiza una calificación. La rúbrica vigente requiere DuckDB aunque el enunciado anterior trabajado usaba Snowflake; se conserva DuckDB para esa conciliación y Snowflake es obligatorio por el alcance del proyecto.

| Criterio | Implementación verificable | Evidencia a revisar |
| --- | --- | --- |
| 1. Orquestación | Una imagen `pset2-pipeline:local` construida por Compose desde `kestra/runtime/Dockerfile`; flow con descarga, extracción y cadena completa. Retry solo en descarga: 3/30 s para red transitoria. Cron semanal por fuente estática, no copiado como frecuencia de sensores. | Flow, README y estado final/outputs de Kestra. |
| 2. Calidad | Notebook `kestra/calidad/diagnostico.ipynb`: faltantes, duplicados, casts, formatos y consistencia, cada uno con estrategia/porqué. Usa las mismas funciones de `limpiar.py`, que opera independientemente sobre el histórico persistente completo. Rechazados auditables y archivo limpio canónico. | Notebook ejecutado en output, calidad_local.json, rechazados y tests de casos difíciles. |
| 3. Warehouse/dbt/Spark | DuckDB carga solo CSV limpio y verifica conteo. dbt tiene staging/intermedia/marts; claves unique/not_null; run/test contra el mismo path. Mart de proporción de fallas por tipo. Spark lee exactamente el CSV limpio y compara agregado con dbt/Pandas. | warehouse_local.json, dbt_local_tests.json, spark_local.json y cadena_local.json. |
| 4. Cadena/documentación | Dos comandos desde Codespace nuevo, con secretos obligatorios de Snowflake. Histórico persistente y exportaciones de consulta. README especifica orden, rutas, credenciales locales generadas, pruebas, backfill y batch vs streaming. Datos y contraseñas locales excluidos de Git. | Reproducción desde README, estructura del árbol y ausencia de CSV/DuckDB/secretos versionados. |

`data/processed/ai4i_clean.csv` existe en ejecución, no como archivo del repositorio. Las cuatro carpetas solicitadas forman la estructura versionada; el dataset real se descarga/produce cuando corre el pipeline. Los outputs del notebook no se guardan en el notebook fuente versionado.

La limpieza no introduce fechas ficticias, no cambia el target para forzar consistencia y no elimina versiones diferentes como si fueran duplicados. Los casos defectuosos de tests son fixtures pequeños construidos en código, no problemas inventados en UCI. El notebook muestra los resultados del histórico real de cada ejecución.
