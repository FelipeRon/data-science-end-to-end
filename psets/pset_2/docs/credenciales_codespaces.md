# Credenciales para Codespaces

La revisión de la rama Felipe detectó tres archivos versionados con credenciales: `.env`, `kestra/.env.kestra` y `kestra/pset2_kestra.p8`. Se retiran del árbol actual y se añaden exclusiones de Git/Docker. **El historial sigue conteniéndolos: la clave debe tratarse como expuesta.** No se reescribe el historial ni se modifica la autenticación de Snowflake automáticamente.

## Rotación por el propietario

1. Generar en un entorno privado un par RSA nuevo de al menos 2048 bits, preferiblemente PKCS8 cifrado. Conservar la privada fuera del repositorio.
2. Un administrador de Snowflake registra la pública nueva para `PSET2_KESTRA`, valida acceso con la nueva privada y retira la pública anterior. Se puede usar el segundo slot durante la transición para no interrumpir otras integraciones; no dejar activa la clave publicada al terminar.
3. Configurar en los secretos de **Codespaces** el Base64 del PEM privado completo como `SECRET_SNOWFLAKE_PRIVATE_KEY`, y el Base64 de su contraseña como `SECRET_SNOWFLAKE_KEY_PASSWORD`. La codificación no cifra los valores; siguen siendo secretos.
4. Detener e iniciar el Codespace para recibir las variables. Ejecutar `PIPELINE_TARGET=snowflake bash kestra/scripts/codespaces.sh start` desde psets/pset_2. No imprimir los secretos para diagnosticar.
5. Revisar otros usos de la misma clave. Quitar archivos del último commit no elimina copias anteriores; una limpieza de historial, si se decide, es un trabajo separado y debe coordinarse con otros clones.

No se transfieren automáticamente secretos desde esta computadora a GitHub. Los permisos del conector permiten editar el repositorio, pero no configurar Codespaces Secrets ni rotar credenciales en la cuenta Snowflake. No se necesitan tokens pegados en el chat.

Fuentes oficiales: [secretos de Codespaces](https://docs.github.com/en/codespaces/managing-your-codespaces/managing-your-account-specific-secrets-for-github-codespaces), [rotación de claves Snowflake](https://docs.snowflake.com/en/user-guide/key-pair-auth).

