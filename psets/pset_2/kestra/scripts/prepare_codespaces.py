"""Prepara archivos locales desde Codespaces Secrets, sin imprimir credenciales."""
import argparse
import base64
import json
import os
import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULTS = {
    'SNOWFLAKE_ACCOUNT': 'MRIWLBX-HH95628', 'SNOWFLAKE_USER': 'PSET2_KESTRA',
    'SNOWFLAKE_ROLE': 'PSET2_INGEST', 'SNOWFLAKE_WAREHOUSE': 'PSET2_WH',
    'SNOWFLAKE_DATABASE': 'PSET2_MANTENIMIENTO',
    'KESTRA_USER': 'admin@kestra.io', 'KESTRA_PASSWORD': '',
}


def read_env(path):
    result = {}
    if not path.exists():
        return result
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        if not line.strip() or line.lstrip().startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        value = value.strip()
        if value.startswith('"'):
            value = json.loads(value).replace('$$', '$')
        elif value.startswith("'") and value.endswith("'"):
            value = value[1:-1].replace("\\'", "'")
        result[key.strip()] = value
    return result


def write_env(path, values):
    path.parent.mkdir(parents=True, exist_ok=True)
    # Compose interpola $. Duplicarlo evita interpretar contraseñas como variables.
    text = ''.join(f'{key}={json.dumps(str(value), ensure_ascii=False).replace(chr(36), chr(36)*2)}\n'
                   for key, value in values.items())
    path.write_text(text, encoding='utf-8')
    path.chmod(0o600)


def decode_secret(value, name):
    try:
        return base64.b64decode(value, validate=True).decode('utf-8')
    except (ValueError, UnicodeDecodeError) as exc:
        raise ValueError(f'{name} debe contener Base64 de texto UTF-8, no el valor sin codificar') from None



def normalize_private_key(value):
    """Acepta PEM directo o Base64 del PEM y devuelve una envoltura canonica."""
    value = value.strip().lstrip('\ufeff')
    if value.startswith('-----BEGIN '):
        pem = value.replace('\\n', '\n')
    else:
        try:
            pem = base64.b64decode(''.join(value.split()), validate=True).decode('utf-8')
        except (ValueError, UnicodeDecodeError):
            raise ValueError(
                'SECRET_SNOWFLAKE_PRIVATE_KEY debe ser el PEM privado completo '
                '(incluidos BEGIN/END) o su Base64; no una ruta ni una clave publica'
            ) from None
    pem = pem.strip().lstrip('\ufeff')
    labels = ('PRIVATE KEY', 'ENCRYPTED PRIVATE KEY', 'RSA PRIVATE KEY')
    label = next((label for label in labels
                  if pem.startswith(f'-----BEGIN {label}-----')), None)
    if label is None or not pem.endswith(f'-----END {label}-----'):
        raise ValueError('SECRET_SNOWFLAKE_PRIVATE_KEY no contiene un PEM privado completo')
    pem += '\n'
    return pem, base64.b64encode(pem.encode('utf-8')).decode('ascii')

def prepare(root=ROOT, environ=None, optional=False):
    env = dict(os.environ if environ is None else environ)
    local = read_env(root / '.env')
    legacy = read_env(root / 'kestra/.env.kestra')
    config = {key: env.get(key, local.get(key, default)) for key, default in DEFAULTS.items()}
    config['KESTRA_PASSWORD']=config['KESTRA_PASSWORD'] or secrets.token_urlsafe(18)
    postgres_password=env.get('POSTGRES_PASSWORD',local.get('POSTGRES_PASSWORD','')) or secrets.token_urlsafe(18)
    target='snowflake'  # Migrar tambien configuraciones locales anteriores.
    cloud = env.get('CODESPACES') == 'true'
    private_b64 = env.get('SECRET_SNOWFLAKE_PRIVATE_KEY') or (legacy.get('SECRET_SNOWFLAKE_PRIVATE_KEY') if not cloud else None)
    key_path = root / 'kestra/pset2_kestra.p8'
    if private_b64:
        private_key, private_b64 = normalize_private_key(private_b64)
    elif key_path.is_file() and env.get('CODESPACES') != 'true':
        private_key = key_path.read_text(encoding='utf-8')
        private_b64 = base64.b64encode(private_key.encode()).decode()
    else:
        if optional:
            print('Snowflake es obligatorio. Configura SECRET_SNOWFLAKE_PRIVATE_KEY y vuelve a ejecutar start.')
            return False
        else:
            raise ValueError('Falta SECRET_SNOWFLAKE_PRIVATE_KEY. Configura una clave NUEVA en Codespaces Secrets.')
    if target=='snowflake' and not private_key.strip():
        raise ValueError('La clave privada no puede estar vacía')
    password_b64 = env.get('SECRET_SNOWFLAKE_KEY_PASSWORD', '' if cloud else
                           local.get('SNOWFLAKE_PRIVATE_KEY_PASSWORD_B64', legacy.get('SECRET_SNOWFLAKE_KEY_PASSWORD', '')))
    decode_secret(password_b64, 'SECRET_SNOWFLAKE_KEY_PASSWORD')
    if private_key:
        key_path.parent.mkdir(parents=True, exist_ok=True)
        key_path.write_text(private_key, encoding='utf-8')
        key_path.chmod(0o600)
    config.update({
        'SNOWFLAKE_PRIVATE_KEY_FILE': '/run/secrets/snowflake.p8',
        'SNOWFLAKE_PRIVATE_KEY_B64': private_b64,
        'PIPELINE_TARGET':target,
        'PSET2_DATA_VOLUME':env.get('PSET2_DATA_VOLUME',local.get('PSET2_DATA_VOLUME','pset_2_history')),
        'POSTGRES_PASSWORD':postgres_password,
        'POSTGRES_PASSWORD_JSON':json.dumps(postgres_password),
        'SNOWFLAKE_PRIVATE_KEY_PASSWORD_B64': password_b64,
        'KESTRA_USER_JSON': json.dumps(config['KESTRA_USER']),
        'KESTRA_PASSWORD_JSON': json.dumps(config['KESTRA_PASSWORD']),
        'KESTRA_URL': env.get('KESTRA_URL', 'http://localhost:8080/'),
    })
    if env.get('CODESPACE_NAME') and not env.get('KESTRA_URL'):
        domain = env.get('GITHUB_CODESPACES_PORT_FORWARDING_DOMAIN', 'app.github.dev')
        config['KESTRA_URL'] = f"https://{env['CODESPACE_NAME']}-8080.{domain}/"
    write_env(root / '.env', config)
    write_env(root / 'kestra/.env.kestra', {
        'SECRET_SNOWFLAKE_PRIVATE_KEY': private_b64,
        'SECRET_SNOWFLAKE_KEY_PASSWORD': password_b64,
    })
    (root / 'output').mkdir(exist_ok=True)
    (root / 'data/processed').mkdir(parents=True,exist_ok=True)
    print('Configuración preparada. Secretos en archivos locales excluidos de Git; valores no mostrados.')
    return True


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--optional', action='store_true')
    args = parser.parse_args()
    try:
        prepare(optional=args.optional)
    except (ValueError, OSError) as exc:
        parser.exit(1, f'{exc}\n')


if __name__ == '__main__':
    main()

