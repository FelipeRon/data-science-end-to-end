"""Acumula filas originales por hash de fuente y fila: los retries no duplican."""
import fcntl
import hashlib
import io
import os
import tempfile
from pathlib import Path

import pandas as pd
from kestra.ingesta_csv import read_source, HEADERS, COLUMNS, select_batch
from scripts.common import report


def merge_history(existing,batch):
    existing,batch=existing.copy(),batch.copy()
    for frame in (existing,batch):
        frame['SOURCE_ROW']=pd.to_numeric(frame['SOURCE_ROW'],errors='raise').astype('int64').astype(str)
    return pd.concat([existing,batch],ignore_index=True).drop_duplicates(['SOURCE_SHA256','SOURCE_ROW'],keep='first')


def main():
    raw=read_source()
    frame=pd.read_csv(io.BytesIO(raw),dtype=str,keep_default_na=False)
    if list(frame.columns)!=HEADERS or len(frame)!=10000:
        raise ValueError('Cambio en contrato de AI4I: revisar diagnostico antes de aceptar otra fuente')
    frame.columns=COLUMNS
    frame['SOURCE_ROW']=range(1,len(frame)+1)
    frame['SOURCE_SHA256']=hashlib.sha256(raw).hexdigest()
    batch=select_batch(frame,int(os.environ.get('BATCH_ID','-1')),int(os.environ.get('BATCH_SIZE','1000')))
    folder=Path(os.environ.get('PSET2_DATA_DIR','data'))/'raw'
    folder.mkdir(parents=True,exist_ok=True)
    # El bloqueo cubre lectura, union y reemplazo para no perder lotes concurrentes.
    with (folder/'.historico.lock').open('a') as lock:
        fcntl.flock(lock.fileno(), fcntl.LOCK_EX)
        path=folder/'historico.csv'
        existing=pd.read_csv(path,dtype=str,keep_default_na=False) if path.exists() else pd.DataFrame(columns=batch.columns)
        before=len(existing)
        combined=merge_history(existing,batch)
        # Cada escritor tiene un temporal propio, en el mismo filesystem.
        temporary=None
        try:
            with tempfile.NamedTemporaryFile(mode='w',encoding='utf-8',newline='',
                                             dir=folder,prefix='.historico-',suffix='.tmp',
                                             delete=False) as handle:
                temporary=Path(handle.name)
                combined.to_csv(handle,index=False)
                handle.flush()
                os.fsync(handle.fileno())
            temporary.replace(path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        (folder/'source.csv').write_bytes(raw)
    report('ingesta_local.json',{'source_rows':len(frame),'selected_rows':len(batch),'inserted_rows':len(combined)-before,
           'history_rows':len(combined),'source_sha256':frame.SOURCE_SHA256.iloc[0]})


if __name__=='__main__':
    main()
