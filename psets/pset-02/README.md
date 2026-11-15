# PSet 2 - AI4I desde GitHub Codespaces

Pipeline: **UCI → Kestra → Snowflake RAW → dbt BRONZE/SILVER/GOLD → Spark → Snowflake OBT**.

El objetivo es detectar fallas **presentes** y priorizar revisión humana (`MACHINE_FAILURE`, horizonte t=0). AI4I es sintético, sin timestamps de medición ni trayectorias por activo: no demuestra predicción del siguiente ciclo, vida útil restante ni ahorro industrial. Las reglas y los costos se documentan en [negocio_y_decision.md](docs/negocio_y_decision.md).

## Arranque en Codespaces

### 1. Sincronizar la rama Felipe

Desde la raíz del repositorio en el Codespace:

```bash
git switch Felipe
git pull --ff-only origin Felipe
```

Si Git indica cambios locales, conservarlos y resolverlos antes de sincronizar; no usar reset ni sobrescribirlos a ciegas. El README anterior tenía marcadores de merge; el texto del curso se conserva como [referencia](docs/enunciado_repositorio_original.md).

El devcontainer ya utiliza Docker-in-Docker y Java 17. Se ajustó el mínimo a 4 núcleos, se añadió el puerto 8080 y una preparación opcional al iniciar. Para aplicar estos cambios, usar **Codespaces: Rebuild Container**. Un Codespace existente de 2 núcleos debe cambiar primero su tipo de máquina. No se levantan servicios ni se hacen cargas Snowflake automáticamente al reconstruir.

### 2. Configurar secretos NUEVOS

Se detectó que `.env`, `kestra/.env.kestra` y la clave privada estaban versionados. Se retiran de la versión actual, pero los commits anteriores aún los contienen. **Rotar la clave en Snowflake antes de reutilizar la integración.** No volver a usar la clave publicada ni copiar sus valores a un commit.

En **Settings → Secrets and variables → Codespaces** del repositorio, o en tus secretos personales de Codespaces autorizados para este repositorio, configurar:

| Nombre | Valor |
| --- | --- |
| `SECRET_SNOWFLAKE_PRIVATE_KEY` | Base64 del contenido completo de una clave privada NUEVA registrada en Snowflake. |
| `SECRET_SNOWFLAKE_KEY_PASSWORD` | Base64 de la contraseña de cifrado; omitir si la clave nueva no está cifrada. |

Los secretos deben ser de **Codespaces**, no solo de Actions. Detener y volver a iniciar un Codespace que ya estaba abierto después de crearlos. No enviar contraseñas ni claves por el chat. La rotación y el acceso a secretos son acciones del propietario; este commit no configura secretos de la cuenta ni elimina el historial de Git.

Guía de rotación y procedimiento: [credenciales_codespaces.md](docs/credenciales_codespaces.md).

Los parámetros no secretos tienen estos valores por defecto y se pueden sobrescribir con variables de entorno antes de preparar:

```text
SNOWFLAKE_ACCOUNT=MRIWLBX-HH95628
SNOWFLAKE_USER=PSET2_KESTRA
SNOWFLAKE_ROLE=PSET2_INGEST
SNOWFLAKE_WAREHOUSE=PSET2_WH
SNOWFLAKE_DATABASE=PSET2_MANTENIMIENTO
```

La preparación genera `.env`, `kestra/.env.kestra`, la clave local y `output/`; usa permisos restringidos y no imprime valores secretos. En Codespaces exige el secreto de entorno, sin reutilizar silenciosamente una clave heredada del repositorio. Los archivos generados están excluidos de Git y del contexto Docker.

### 3. Levantar e importar

Desde la raíz del repositorio:

```bash
cd psets/pset-02
bash scripts/codespaces.sh start
```

Este comando prepara la configuración, construye `pset2-pipeline:local`, arranca PostgreSQL/Kestra, espera a que la API responda e importa el flow y sus archivos de namespace. Actualiza las variables de conexión del flow a partir de `.env`. No requiere PowerShell ni instala paquetes Python en el entorno del curso.

En **Ports**, abrir **8080** y mantener su visibilidad **Private**. El navegador usa la dirección HTTPS del Codespace; los scripts hablan con `localhost:8080` dentro de él. Credenciales locales por defecto: `admin@kestra.io` / `Admin1234`. Se pueden personalizar con `KESTRA_USER` y `KESTRA_PASSWORD` antes de preparar; la configuración preserva caracteres especiales.

### 4. Ejecutar todo y esperar el resultado

```bash
bash scripts/codespaces.sh run
```

Muestra el ID y los cambios de estado. Termina con error si falla una tarea. El éxito exige `SUCCESS` en descargar, extraer y pipeline. Los reportes `ingesta.json`, `calidad.json`, `obt.json`, `negocio.json` y los artefactos dbt quedan en **Outputs** de la tarea pipeline en Kestra.

Para un lote o para el backfill completo:

```bash
# Primeras 1000 observaciones al ordenar por UDI.
bash scripts/codespaces.sh run --batch-id 0 --batch-size 1000

# Todos los lotes, de forma secuencial, esperando cada resultado.
bash scripts/codespaces.sh backfill --batch-size 1000
```

`batch_id=-1` carga la fuente completa; con tamaño 1000, los lotes válidos son 0..9. Repetirlos no debe duplicar RAW. No representan fechas históricas de una máquina. El trigger es viernes 08:00, America/Guayaquil; solo corre mientras el Codespace y Kestra estén activos.

## Pruebas, ejecución manual y diagnóstico

Las pruebas no necesitan secretos ni Snowflake:

```bash
bash scripts/codespaces.sh test
```

Después de `prepare`/`start`, se puede ejecutar manualmente sin Kestra:

```bash
docker compose run --rm pipeline
docker compose run --rm pipeline sh scripts/dbt.sh build
docker compose run --rm spark
docker compose run --rm pipeline python scripts/evaluar_negocio.py
```

Estos reportes quedan en `output/`. No ejecutar Docker manual y Kestra simultáneamente: el límite de concurrencia del flow no protege comandos externos.

```bash
bash scripts/codespaces.sh status
docker compose logs --tail 80 kestra postgres
bash scripts/codespaces.sh stop
```

`stop` conserva los contenedores y volúmenes; `docker compose down` también conserva los volúmenes salvo que se añada `-v`. No borrar volúmenes para resolver un error de credenciales. Tras reconstruir un Codespace, volver a ejecutar `start`: la imagen local puede necesitar reconstruirse.

| Error | Qué revisar |
| --- | --- |
| Falta `SECRET_SNOWFLAKE_PRIVATE_KEY` | Secretos de Codespaces, acceso de este repositorio y reinicio tras agregarlos. |
| Docker no responde | Reconstruir el devcontainer; usa Docker-in-Docker. |
| Kestra tarda en iniciar | Logs de Kestra/PostgreSQL; esperar la descarga inicial de imágenes. |
| API 401/403 | Credenciales locales de Kestra consistentes con `.env`; volver a ejecutar `start` tras cambiarlas. |
| Error JWT Snowflake | Clave nueva registrada para el usuario correcto; contraseña y cuenta correctas. |
| Sin permisos Snowflake | Un administrador debe revisar `scripts/bootstrap.sql` o `scripts/permisos_pendientes.sql`. El pipeline no eleva su rol. |
| Imagen no encontrada | Ejecutar `start` en el mismo Docker que utiliza Kestra. |

## Capas y verificaciones del PSet

- **RAW.AI4I_OBSERVATIONS:** columnas originales como texto, URL, SHA256, lote y carga. MERGE por versión y UDI permite retries/backfill idempotentes.
- **BRONZE.STG_AI4I:** tipos y normalización, sin descartar filas silenciosamente.
- **SILVER:** válidos, rechazados con motivo y reporte de calidad. Se conservan las discrepancias target/subtipos.
- **GOLD:** FACT_READING, DIM_PRODUCT y DIM_SOURCE con source()/ref() y tests de claves/relaciones/reconciliación.
- **OBT.AI4I_OBT:** Spark une Gold, valida el grano y añade delta térmico, potencia y baseline versionado. La publicación ocurre después de validar una tabla nueva.

El grano es `(source_sha256, udi)`. TWF/HDF/PWF/OSF/RNF se excluyen de la OBT por fuga del target. MACHINE_FAILURE es etiqueta; IDs, trazabilidad y columnas de baseline no son features. Spark usa local[2] y transporte Python/Pandas adecuado a 10.000 filas; no es una implementación distribuida de gran volumen.

La auditoría previa encontró 10.000 filas, 339 fallas (3,39%), 0 nulos/UDI duplicados y 27 discrepancias target/subtipos. Los costos y la planta de referencia siguen siendo supuestos; el reporte de sensibilidad no demuestra ROI real. El umbral 2,5% es para una futura probabilidad calibrada del estado actual, no una probabilidad ya servida por este PSet.

```sql
SELECT SOURCE_SHA256, COUNT(*), COUNT(DISTINCT UDI)
FROM PSET2_MANTENIMIENTO.RAW.AI4I_OBSERVATIONS GROUP BY 1;
SELECT * FROM PSET2_MANTENIMIENTO.SILVER.QUALITY_REPORT;
SELECT COUNT(*) FROM PSET2_MANTENIMIENTO.GOLD.FACT_READING;
SELECT COUNT(*), COUNT(DISTINCT READING_KEY)
FROM PSET2_MANTENIMIENTO.OBT.AI4I_OBT;
```

Para una sola versión completa sin rechazos, cada conteo es 10.000. Una reejecución debe informar `inserted_rows: 0`.

## Documentación y alcance

Ver [memo técnico](docs/memo_tecnico.md), [reglas y negocio](docs/negocio_y_decision.md), [validación histórica](docs/validacion.md) y [adaptación a Codespaces](docs/codespaces.md). La evidencia previa de Snowflake es de la instalación local; no se presenta como una ejecución remota del Codespace. El PDF mantiene el formato de seis páginas; ajustar su nombre de entrega con los apellidos reales.

La infraestructura conserva su definición en el Compose raíz. No ejecutar el antiguo Compose dentro de kestra/ ni el antiguo script que sube solo un archivo: la importación actual necesita también el proyecto dbt, Spark y los scripts compartidos.

Batch es suficiente para la fuente estática. Streaming requeriría eventos, timestamps y latencia operativa justificada; no se implementa. Las plantillas originales y la documentación del curso se conservan, pero el pipeline usa los directorios dbt/ y spark/ de este PSet.
