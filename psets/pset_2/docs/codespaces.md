# Codespaces y migración de rutas

La ruta activa es **psets/pset_2**. Los auxiliares viven en `kestra/scripts`, el Dockerfile y dependencias en `kestra/runtime`, y las pruebas en `docs/tests`. La raíz solo tiene los tres archivos funcionales solicitados y los dos archivos ocultos de exclusiones.

El devcontainer conserva Docker-in-Docker, Java 17 y los servicios de los otros laboratorios; se actualizó únicamente la ruta de preparación y el README abierto. El postStart prepara configuración, no ejecuta cargas automáticamente. Usar al menos cuatro núcleos y reconstruir el contenedor cuando cambie su configuración.

La ruta DuckDB no necesita secretos Snowflake. La preparación genera contraseñas distintas de Kestra/PostgreSQL y las conserva en `.env`, que no se versiona. El cliente lee esas mismas credenciales; no se publican contraseñas por defecto en Compose.

El histórico vive en el volumen `pset_2_history`, montado por Compose y el runner de Kestra. El runner requiere montaje de volúmenes para conservar el histórico; la configuración habilita esa función y el flow monta únicamente ese volumen de datos, sin montar el repositorio ni credenciales del host. La API se utiliza por localhost; el puerto de navegador debe permanecer Private.

Después de ejecutar desde Kestra, el cliente descarga copias de consulta del histórico, CSV limpio, notebook ejecutado y resumen de cadena a tu Codespace. No son una segunda fuente para el pipeline; la fuente canónica permanece en el volumen compartido. Todas las copias se excluyen de Git.

Para detener conservar datos: `bash kestra/scripts/codespaces.sh stop`. El nombre de proyecto Compose cambió a pset_2 para evitar mezclar contraseñas nuevas con el PostgreSQL de la instalación anterior. No se borran los volúmenes antiguos. Snowflake opcional requiere rotar la clave anteriormente expuesta y configurar secretos nuevos, tal como indica `credenciales_codespaces.md`.
