# Adaptación a GitHub Codespaces - 15/11/2026

## Cambios

| Archivo | Comportamiento |
| --- | --- |
| `.devcontainer/devcontainer.json` del repositorio | Mantiene Docker-in-Docker, Java y servicios del curso; pide 4 núcleos y reenvía 8080. Al iniciar solo intenta preparar secretos si están disponibles. |
| `scripts/prepare_codespaces.py` | Lee Codespaces Secrets, crea archivos locales con permisos restringidos y no imprime sus valores. Configura URL y parámetros de conexión. |
| `scripts/kestra_cli.py` | Cliente Python estándar para readiness, importación selectiva de namespace, creación/actualización del flow, ejecución y espera de estados. |
| `scripts/codespaces.sh` | Comandos prepare/start/run/backfill/test/status/stop desde Bash; independiente de la carpeta de invocación. |
| `docker-compose.yml` | URL pública del Codespace separada de la API local; credenciales YAML escapadas correctamente. Mantiene volúmenes, Spark, PostgreSQL y Kestra. |
| `README.md` | Instrucciones desde un Codespace nuevo; conflicto de merge resuelto. Texto original del curso conservado como referencia. |
| `.gitignore` y `.dockerignore` | Excluyen archivos de credenciales, claves, artefactos y backups. |

Se retiran del árbol actual `.env`, `kestra/.env.kestra` y `kestra/pset2_kestra.p8`, que estaban versionados. No se reescribe el historial ni se rota la clave en Snowflake desde el conector. Es necesario completar esa rotación y configurar los nuevos secretos antes de una carga real.

## Validación realizada

- 17 pruebas aprobadas en un contenedor Linux con las dependencias del proyecto: las 13 pruebas de datos/regla/costos previas y 4 nuevas de preparación, credenciales, falta de secretos y selección de archivos de namespace.
- Sintaxis Bash verificada con `bash -n`.
- Devcontainer JSONC validado; no se reemplazó la configuración de los otros laboratorios.
- Compose validado con credenciales ficticias; se verificó en un contenedor de prueba la preservación de `$`, comillas y barras en una contraseña, y la construcción de la URL del Codespace.
- Los secretos y artefactos generados no forman parte de la selección de archivos que se sube al namespace.

Estas comprobaciones se realizaron localmente en Docker/Linux. **No prueban que un Codespace remoto ya haya ejecutado Snowflake**. El conector GitHub permite editar el repositorio; esta sesión no tiene acceso de ejecución a tu máquina Codespaces ni acceso a su almacén de secretos. La evidencia Snowflake anterior, en docs/evidencia, corresponde a la instalación previa.

## Activación por el propietario

1. Rotar la clave que estaba versionada y configurar `SECRET_SNOWFLAKE_PRIVATE_KEY` y, si aplica, `SECRET_SNOWFLAKE_KEY_PASSWORD` como secretos de Codespaces autorizados para este repositorio.
2. Sincronizar Felipe sin descartar cambios locales, detener/reiniciar el Codespace para recibir los secretos y reconstruir el contenedor si corresponde al cambio de devcontainer.
3. Ejecutar `bash scripts/codespaces.sh start` y después `bash scripts/codespaces.sh run` desde psets/pset-02.
4. Abrir 8080 desde Ports, mantener Private y verificar SUCCESS y los outputs.

No ejecutar `git reset --hard`, no publicar claves y no borrar volúmenes para completar esta adaptación. No se envían mensajes a terceros ni se activa un nuevo Codespace de pago automáticamente.
