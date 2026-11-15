# Limpieza y reorganización del repositorio

Ámbito: únicamente el PSet 2 y los enlaces del catálogo/devcontainer que apuntaban a él. La carpeta activa es `psets/pset_2`; no se modifica el contenido de los otros PSets ni laboratorios.

## Qué se retiró

| Grupo anterior | Decisión | Motivo |
| --- | --- | --- |
| `output/` versionado | Retirar | CSV/reportes/manifiesto de una ejecución se regeneran. El manifiesto de dbt no es código fuente. |
| Copias JSON repetidas entre `output/` y `docs/evidencia/` | Consolidar en un resumen agregado actual | Había contenido idéntico de calidad, ingesta y OBT con distintos nombres. Se evita confundir evidencia histórica con una ejecución actual. |
| `kestra/docker-compose.yml` y viejo `subir_a_kestra.sh` | Retirar | Había dos instrucciones de infraestructura/importación incompatibles; el Compose raíz y el cliente actual son la única entrada. |
| Scripts PowerShell | Retirar | Los mismos pasos ya tienen una entrada Bash/Python que funciona en Codespaces y Docker. |
| `audit_source.py`, `check_connection.py`, `validate_live.py`, `dbt.sh` | Sustituir por diagnóstico, entrypoint y comandos actuales | Auxiliares de iteraciones anteriores sin uso en la cadena nueva. |
| `dbt/.user.yml`, logs, target, caches y salidas | Excluir | Metadatos/artefactos generados, no piezas del proyecto. |
| Clave pública antigua y archivos de claves/credenciales | No trasladar | La clave privada ya se había retirado del último commit; debe rotarse. Una pública antigua asociada a esa clave tampoco es necesaria para ejecutar el proyecto. |
| PDF generado y generador del memo anterior | Retirar la versión desactualizada | Describían solamente la ruta Snowflake anterior. Se conserva el memo técnico editable actualizado y la documentación de negocio; el PDF anterior sigue recuperable en el historial. |
| README duplicado del enunciado | Retirar | La rúbrica se conserva una sola vez en `docs/rubrica.md`; README contiene la ejecución activa. |

## Qué se movió y conserva

- `Dockerfile` y dependencias exactas a `kestra/runtime/`.
- Módulos auxiliares necesarios a `kestra/scripts/`, con imports y comandos actualizados.
- Tests a `docs/tests/`.
- Rúbrica a `docs/rubrica.md`.
- Modelos dbt de Snowflake a `dbt/snowflake/` como ampliación opcional; el proyecto dbt raíz ahora es DuckDB con staging/intermedia/marts.
- Diagnóstico, limpieza y decisiones de negocio se conservan como código/documentación únicos, sin dos copias activas del proyecto.

No se borran datos ni volúmenes de tus instalaciones anteriores, ni se reescribe Git. Los cambios eliminan rutas del árbol actual y mantienen recuperabilidad por commits previos. Las copias locales de trabajo fuera de este repositorio no se tocan.

## Exclusiones

`data/`, `output/`, `.env`, claves, logs, caches, targets de ambos proyectos dbt y notebooks ejecutados no se versionan ni se incorporan a la imagen. El notebook fuente no tiene outputs. Los casos de prueba se construyen en memoria, no son archivos de datos de planta en el repositorio.
