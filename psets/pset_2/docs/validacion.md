> Actualización: Snowflake es obligatorio. Las evidencias locales siguientes corresponden a la versión anterior y no validan la cadena completa actual. Esta corrección se hizo sin pruebas ni ejecuciones, por solicitud del usuario.

# Validación de la reorganización - 15/11/2026

Se probó la cadena completa con UCI AI4I real, no solo una inspección de archivos. Entorno: Docker/Linux y una instancia aislada de Kestra 2.0.7 en el puerto de prueba 18080. La configuración publicada conserva 8080 como puerto normal.

| Verificación | Resultado |
| --- | --- |
| Imagen actual | `pset2-pipeline:local`, construida con `kestra/runtime/Dockerfile` y lock completo. |
| Pruebas dentro de la imagen final, sin montajes locales | **21 aprobadas**. |
| Notebook | Ejecutado automáticamente con nbclient sobre el histórico persistente. No contiene outputs en Git. |
| Histórico / limpio | 10.000 filas históricas; 10.000 válidas; cero rechazadas en esta versión real de UCI. |
| Discrepancias target/subtipos | 27 conservadas, sin corregir arbitrariamente el target. |
| DuckDB | 10.000 filas, leídas del CSV limpio. |
| dbt | `dbt run`: 3 modelos correctos; `dbt test`: 8 pruebas aprobadas, mismo `.duckdb`. |
| Spark | 10.000 observaciones; 3 grupos; resultado igual a dbt y Pandas, tolerancia 1e-9. |
| Archivo compartido | Warehouse/Spark verifican el mismo SHA256 del CSV limpio. |
| Kestra final | Namespace `pset_2`, ejecución `4l1WK3CA9J3jnNvuxtuJux`, **SUCCESS**. |
| Backfill | Lote 0, ejecución `2FzKSDbwR0kJGkZCN8ittf`, **SUCCESS**; cero filas nuevas y total histórico 10.000. |
| Exportación | El cliente recuperó CSV limpio/histórico, notebook ejecutado y resumen al directorio local de consulta. |

El backfill se probó durante la reorganización antes del cambio final de nombre de namespace; la ejecución completa final usa el namespace nuevo y las rutas definitivas. Las dos usaron el mismo volumen de prueba y la lógica de acumulación corregida. No se borró un histórico para simular éxito de reejecución.

La evidencia agregada se conserva **una sola vez** en `evidencia/validacion_resumen.json`. Los CSV, `.duckdb`, notebooks con outputs y reportes extensos permanecen como artefactos de ejecución, fuera de Git.

En la fuente observada, las tasas por tipo fueron H=21/1003, M=83/2997 y L=235/6000. El mart responde una pregunta descriptiva; no prueba causalidad ni generalización a una planta. La evaluación de negocio mantiene costos supuestos y no autoriza implementar un modelo.

## Límites de esta validación

- No se ejecutó un Codespace remoto del usuario; sí el mismo Dockerfile, scripts, cliente API y flow en Linux/Kestra.
- La ampliación Snowflake se conserva y sus rutas se actualizaron, pero no se volvió a conectar durante esta limpieza, porque requiere claves nuevas tras la exposición anterior.
- No se modifican los volúmenes de instalaciones anteriores ni se garantiza una nota 4/4: la matriz `cumplimiento_rubrica.md` permite revisar cada criterio con evidencia.
