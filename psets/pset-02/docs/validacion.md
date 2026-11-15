# Evidencia de validación - 12/11/2026

## Mejora por comentarios del PSet 1

La formulación vigente es detección del estado actual, no predicción del siguiente ciclo ni RUL. El pipeline añade la candidata de regla `UCI_PHYSICS_WEAR200_v1` a la OBT y emite `negocio.json` con costos explícitamente ilustrativos, nueve escenarios de inspección/demora, tres de margen/hora y cuatro de carga operativa hipotética.

La mejora aprobó **13 tests locales**, incluidos costos de TP/FP/FN, umbral de 2,5%, límites de la regla y consistencia entre expresión Spark y función Python. Evidencia: `evidencia/pruebas_mejora.xml`. El recorrido inicial de la mejora terminó en SUCCESS (`2s6BSQyfvgfAIjNA7toxoI`); la evidencia de la versión final se registra en `evidencia/kestra_mejora_pset1.json` y los reportes `evidencia/mejora_*.json`.

La regla del CSV completo obtuvo TP=330, FP=678, FN=9, TN=8983 (recall 97,35%, precisión 32,74%); es una descripción del dataset, no evaluación externa ni validación de expertos reales. Las referencias no utilizan flags ni el target para decidir. El reporte conserva `deployment_authorized: false` y `causal_savings_estimated: false`: sin modelo entrenado, costos confirmados y piloto real, no se afirma viabilidad de implementación.

`docs/negocio_y_decision.md` responde uno a uno los ocho comentarios y contiene la solicitud concreta al patrocinador. El memo mantiene seis páginas. La evidencia original que sigue corresponde a la construcción inicial del pipeline, antes de añadir este contrato de decisión.

La validación se ejecutó contra la cuenta Snowflake del proyecto y el Kestra local, no solo con revisión estática.

## Resultados

| Comprobación | Resultado observado | Evidencia |
| --- | --- | --- |
| Entorno Docker | Imagen `pset2-pipeline:local` construida con versiones fijadas; Kestra 2.0.7 y PostgreSQL 18 activos | `Dockerfile`, `requirements.lock.txt`, Compose |
| Pruebas locales | 8 aprobadas: cobertura completa de lotes, índices inválidos, joins correctos, duplicación de dimensión y hechos huérfanos | `evidencia/pruebas.xml` |
| Fuente UCI | 10.000 filas, 14 columnas, 0 celdas nulas, 0 UDI duplicados | `evidencia/fuente.json` |
| Carga RAW completa | 10.000 filas almacenadas | `evidencia/ingesta.json` |
| Reejecución completa | 0 filas nuevas, total RAW sigue en 10.000 | `evidencia/kestra_ingesta.json` |
| Backfill lote 0 por Docker | Seleccionó 1.000 filas, insertó 0, total RAW 10.000 | `evidencia/backfill_lote_0.json` |
| dbt en Snowflake | 8 modelos construidos y 24 tests aprobados; 32 resultados sin errores ni omisiones | `evidencia/kestra_run_results.json` |
| Calidad en Snowflake | 10.000 válidos, 0 rechazados, 27 discrepancias target/subtipos, 339 fallas | `evidencia/kestra_calidad.json` |
| Spark y OBT | Gold=10.000; OBT=10.000; 0 claves repetidas; 10.000 filas verificadas en Snowflake | `evidencia/kestra_obt.json` |
| Kestra completo | `SUCCESS`: descargar, extraer y pipeline | `evidencia/kestra_completo.json` |
| Backfill lote 9 por Kestra | `SUCCESS` con `batch_id=9`, `batch_size=1000` | `evidencia/kestra_backfill.json` |
| Memo PDF | 6 páginas, | `PSet2_memo_Ron.pdf` |

## Ejecuciones de Kestra

- Completa: `1sczhToyQelLFf0HXV8ZwR`.
- Backfill último lote: `7ixKcx0OVDDF5OdYOYRsK2`.
- Interfaz local: [http://localhost:8080](http://localhost:8080), namespace `pset2`, flow `descargar_ai4i`.

La primera prueba de integración (`2LgFNJXukhDl9Fr2ZeQW2g`) falló antes de ejecutar la carga por una variable `workingDir` no disponible en la evaluación de `env` de Kestra 2.0.7. Se corrigió a `PYTHONPATH: "."`; las ejecuciones completas y de backfill posteriores aprobaron. Los permisos iniciales de la cuenta se corrigieron con `scripts/permisos_pendientes.sql`, ejecutado por el usuario desde Snowsight.

## Alcance y límites

Se probaron ejecución completa, reejecución sin duplicados, lotes 0 y 9 contra Snowflake, y cobertura exacta de todos los lotes con tests locales. No se borró RAW para simular una carga histórica desde cero, ni se ejecutaron diez reconstrucciones completas innecesarias después de cargar el archivo entero. El script de backfill encola todos los lotes para cuando sea necesario.

Los tests no validan exactitud física ni capacidad de anticipar fallas futuras. AI4I es sintético y carece de fechas de observación. Las discrepancias se conservaron; no se inventaron correcciones, registros rechazados ni estadísticas. La precisión frente a mediciones reales sigue sin poder evaluarse con esta fuente.

