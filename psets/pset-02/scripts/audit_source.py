"""Métricas de la fuente original, independientes de la ejecución en Snowflake."""
import hashlib
import io
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from kestra.ingesta_csv import read_source, HEADERS
from scripts.common import report


def main():
    import pandas as pd
    raw = read_source()
    df = pd.read_csv(io.BytesIO(raw))
    if list(df.columns) != HEADERS:
        raise ValueError('Contrato de columnas modificado')
    flags = ['TWF', 'HDF', 'PWF', 'OSF', 'RNF']
    report('fuente.json', {
        'source_sha256': hashlib.sha256(raw).hexdigest(),
        'rows': len(df), 'columns': len(df.columns),
        'missing_cells': int(df.isna().sum().sum()),
        'duplicate_udi': int(df.UDI.duplicated().sum()),
        'machine_failures': int(df['Machine failure'].sum()),
        'failure_rate': float(df['Machine failure'].mean()),
        'flag_target_mismatches': int((df['Machine failure'] != df[flags].max(axis=1)).sum()),
        'type_counts': df['Type'].value_counts().to_dict(),
        'measurement_ranges': {c: {'min': float(df[c].min()), 'max': float(df[c].max())}
                               for c in HEADERS[3:8]},
        'evidence_scope': 'CSV descargado de UCI; no demuestra ejecución en Snowflake'
    })


if __name__ == '__main__':
    main()
