import base64
import importlib.util
import json
from pathlib import Path
import sys

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from prepare_codespaces import prepare, read_env, write_env
from kestra_cli import namespace_files


def secret(value):
    return base64.b64encode(value.encode()).decode()


def test_preparation_from_codespace_secrets_does_not_print_credentials(tmp_path, capsys):
    pem = '-----BEGIN PRIVATE KEY-----\nTEST_ONLY_NOT_A_REAL_KEY\n-----END PRIVATE KEY-----\n'
    password = 'test-$password-with-"quotes"-and-\\slashes'
    env = {'CODESPACES':'true', 'CODESPACE_NAME':'test-space',
           'SECRET_SNOWFLAKE_PRIVATE_KEY':secret(pem), 'SECRET_SNOWFLAKE_KEY_PASSWORD':secret('key-pass'),
           'KESTRA_PASSWORD':password, 'SNOWFLAKE_WAREHOUSE':'OTHER_WH'}
    assert prepare(tmp_path, env)
    values = read_env(tmp_path / '.env')
    assert values['KESTRA_PASSWORD'] == password
    assert json.loads(values['KESTRA_PASSWORD_JSON']) == password
    assert values['SNOWFLAKE_WAREHOUSE'] == 'OTHER_WH'
    assert values['KESTRA_URL'] == 'https://test-space-8080.app.github.dev/'
    assert (tmp_path / 'kestra/pset2_kestra.p8').read_text() == pem
    assert read_env(tmp_path/'kestra/.env.kestra')['SECRET_SNOWFLAKE_PRIVATE_KEY'] == secret(pem)
    assert password not in capsys.readouterr().out


def test_codespace_never_reuses_published_legacy_key(tmp_path):
    write_env(tmp_path/'kestra/.env.kestra', {'SECRET_SNOWFLAKE_PRIVATE_KEY':secret('old-key')})
    with pytest.raises(ValueError, match='Falta SECRET_SNOWFLAKE_PRIVATE_KEY'):
        prepare(tmp_path, {'CODESPACES':'true'})
    assert prepare(tmp_path, {'CODESPACES':'true'}, optional=True) is False


def test_invalid_base64_and_missing_secret_leave_no_new_files(tmp_path):
    with pytest.raises(ValueError, match='Base64'):
        prepare(tmp_path, {'SECRET_SNOWFLAKE_PRIVATE_KEY':'not!base64'})
    assert not (tmp_path/'.env').exists()
    with pytest.raises(ValueError, match='Falta SECRET'):
        prepare(tmp_path, {})


def test_namespace_upload_excludes_secrets_and_generated_files(tmp_path):
    paths = ['scripts/main.py','scripts/params.json','dbt/models/gold.sql',
             'dbt/target/compiled/unsafe.sql','scripts/__pycache__/bad.py',
             'spark/job.py','kestra/ingesta_csv.py','kestra/.env.kestra','kestra/key.p8']
    for path in paths:
        target=tmp_path/path
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_text('test')
    included = [p.relative_to(tmp_path).as_posix() for p in namespace_files(tmp_path)]
    assert included == ['dbt/models/gold.sql','kestra/ingesta_csv.py','scripts/main.py','scripts/params.json','spark/job.py']
