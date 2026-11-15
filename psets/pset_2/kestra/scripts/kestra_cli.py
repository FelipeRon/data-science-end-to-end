"""Cliente stdlib: importa solo código permitido, ejecuta y espera resultados."""
import argparse
import base64
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
import uuid

from prepare_codespaces import ROOT, read_env

NAMESPACE = 'pset_2'
FLOW_ID = 'descargar_ai4i'


def namespace_files(root=ROOT):
    allowed = {'kestra': {'.py', '.json', '.sql', '.sh','.ipynb'}, 'dbt': {'.sql', '.yml'}, 'spark': {'.py'}}
    excluded = {'target', 'logs', 'dbt_packages', '__pycache__', '.pytest_cache'}
    result = []
    for folder, extensions in allowed.items():
        result.extend(p for p in (root / folder).rglob('*')
                      if p.is_file() and p.suffix in extensions and not excluded.intersection(p.relative_to(root).parts))
    return sorted(result)


def multipart(fields, file=None):
    boundary = 'pset2-' + uuid.uuid4().hex
    body = bytearray()
    for key, value in fields.items():
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="{key}"\r\n\r\n{value}\r\n'.encode())
    if file:
        name, data = file
        body.extend(f'--{boundary}\r\nContent-Disposition: form-data; name="fileContent"; filename="{name}"\r\nContent-Type: application/octet-stream\r\n\r\n'.encode())
        body.extend(data)
        body.extend(b'\r\n')
    body.extend(f'--{boundary}--\r\n'.encode())
    return bytes(body), f'multipart/form-data; boundary={boundary}'


class Client:
    def __init__(self):
        config = read_env(ROOT / '.env')
        self.api = os.environ.get('KESTRA_API', 'http://localhost:8080/api/v1/main').rstrip('/')
        user = os.environ.get('KESTRA_USER', config.get('KESTRA_USER', 'admin@kestra.io'))
        password = os.environ.get('KESTRA_PASSWORD', config.get('KESTRA_PASSWORD', ''))
        if not password:
            raise RuntimeError('Ejecuta primero prepare o start para generar credenciales locales')
        self.auth = base64.b64encode(f'{user}:{password}'.encode()).decode()

    def request(self, path, method='GET', data=None, content_type=None):
        headers = {'Authorization': 'Basic ' + self.auth}
        if content_type:
            headers['Content-Type'] = content_type
        request = Request(self.api + path, data=data, method=method, headers=headers)
        with urlopen(request, timeout=30) as response:
            body = response.read()
            return json.loads(body) if body else None

    def ready(self, timeout):
        deadline = time.monotonic() + timeout
        while True:
            try:
                self.request(f'/flows/{NAMESPACE}/{FLOW_ID}')
                return
            except HTTPError as exc:
                if exc.code == 404:  # Servidor listo, flow todavía no importado.
                    return
                if exc.code in (401, 403):
                    raise RuntimeError('Kestra rechazó las credenciales locales') from None
            except (URLError, TimeoutError, ConnectionError):
                pass
            if time.monotonic() >= deadline:
                raise RuntimeError('Kestra no quedó listo. Revisa docker compose logs --tail 80 kestra postgres')
            time.sleep(3)

    def upload(self):
        self.ready(180)
        paths = namespace_files()
        for file in paths:
            relative = file.relative_to(ROOT).as_posix()
            data, kind = multipart({}, (file.name, file.read_bytes()))
            self.request(f'/namespaces/{NAMESPACE}/files?' + urlencode({'path': '/' + relative}), 'POST', data, kind)
        source = (ROOT / 'kestra/flow_ingesta.yml').read_text(encoding='utf-8')
        config = read_env(ROOT / '.env')
        for key in ('account', 'user', 'role', 'warehouse', 'database'):
            value = config['SNOWFLAKE_' + key.upper()]
            source = re.sub(r'^  ' + key + r':.*$', lambda _: '  ' + key + ': ' + json.dumps(value), source, flags=re.MULTILINE)
        source=re.sub(r'^  data_volume:.*$',lambda _: '  data_volume: '+json.dumps(config.get('PSET2_DATA_VOLUME','pset_2_history')),source,flags=re.MULTILINE)
        try:
            self.request(f'/flows/{NAMESPACE}/{FLOW_ID}')
            method, path = 'PUT', f'/flows/{NAMESPACE}/{FLOW_ID}'
        except HTTPError as exc:
            if exc.code != 404:
                raise
            method, path = 'POST', '/flows'
        self.request(path, method, source.encode(), 'application/x-yaml')
        print(f'Flow {NAMESPACE}.{FLOW_ID} y {len(paths)} archivos del namespace actualizados.')

    def execute(self, batch_id, batch_size, wait=False, timeout=1800, target=None):
        if batch_id < -1 or batch_size <= 0:
            raise ValueError('batch_id debe ser -1 o un lote válido y batch_size debe ser positivo')
        target=target or 'snowflake'
        if target != 'snowflake':
            raise ValueError('Snowflake es obligatorio')
        data, kind = multipart({'batch_id': batch_id, 'batch_size': batch_size,'target':target})
        result = self.request(f'/executions/{NAMESPACE}/{FLOW_ID}', 'POST', data, kind)
        execution_id = result['id']
        print(f'Execution ID: {execution_id}', flush=True)
        if wait:
            self.wait(execution_id, timeout)
        return execution_id

    def wait(self, execution_id, timeout):
        deadline = time.monotonic() + timeout
        last = None
        while True:
            execution = self.request('/executions/' + execution_id)
            state = execution['state']['current']
            if state != last:
                print(f'Estado: {state}', flush=True)
                last = state
            if state == 'SUCCESS':
                self.export(execution_id)
                print('Pipeline completo correcto. Reportes JSON disponibles en Outputs de la tarea pipeline.')
                return
            if state in ('FAILED', 'WARNING', 'KILLED', 'CANCELLED'):
                raise RuntimeError(f'La ejecución terminó en {state}; revisar Logs en Kestra')
            if time.monotonic() >= deadline:
                raise RuntimeError(f'Tiempo de espera agotado; la ejecución {execution_id} puede seguir activa')
            time.sleep(3)

    def export(self, execution_id):
        tasks=self.request('/outputs/tasks/'+execution_id)
        task=next(t for t in tasks if t['taskId']=='pipeline')
        outputs=self.request('/outputs/tasks/'+execution_id+'/'+task['taskRunId'])
        destinations={'output/ai4i_clean.csv':'data/processed/ai4i_clean.csv',
                      'output/historico.csv':'data/raw/historico.csv',
                      'output/cadena_local.json':'output/cadena_local.json',
                      'output/diagnostico_ejecutado.ipynb':'output/diagnostico_ejecutado.ipynb'}
        for source,destination in destinations.items():
            uri=outputs.get('outputFiles',{}).get(source)
            if not uri: continue
            request=Request(self.api+'/executions/'+execution_id+'/file?'+urlencode({'path':uri}),headers={'Authorization':'Basic '+self.auth})
            with urlopen(request,timeout=60) as response:
                content=response.read()
            path=ROOT/destination
            path.parent.mkdir(parents=True,exist_ok=True)
            path.write_bytes(content)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('command', choices=['wait-ready', 'upload', 'execute', 'backfill'])
    parser.add_argument('--batch-id', type=int, default=-1)
    parser.add_argument('--batch-size', type=int, default=1000)
    parser.add_argument('--wait', action='store_true')
    parser.add_argument('--target',choices=['snowflake'])
    parser.add_argument('--timeout', type=int, default=1800)
    args = parser.parse_args()
    try:
        client = Client()
        if args.command == 'wait-ready':
            client.ready(args.timeout)
        elif args.command == 'upload':
            client.upload()
        elif args.command == 'execute':
            client.execute(args.batch_id, args.batch_size, args.wait, args.timeout,args.target)
        else:
            if args.batch_size <= 0:
                raise ValueError('batch-size debe ser positivo')
            for batch in range((10000 + args.batch_size - 1) // args.batch_size):
                client.execute(batch, args.batch_size, True, args.timeout,args.target)
    except HTTPError as exc:
        parser.exit(1, f'Kestra respondió HTTP {exc.code}; revisar URL, credenciales y logs.\n')
    except (ValueError, RuntimeError, URLError, OSError, KeyError) as exc:
        parser.exit(1, f'{exc}\n')


if __name__ == '__main__':
    main()

