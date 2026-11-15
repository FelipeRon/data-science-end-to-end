"""Diagnóstico y limpieza compartidos por notebook y pipeline, sin imputaciones ocultas."""
import argparse
import hashlib
import json
import os
from pathlib import Path

import pandas as pd

MEASURES = ['AIR_TEMPERATURE_K','PROCESS_TEMPERATURE_K','ROTATIONAL_SPEED_RPM','TORQUE_NM','TOOL_WEAR_MIN']
FLAGS = ['MACHINE_FAILURE','TWF','HDF','PWF','OSF','RNF']
NUMERIC = ['UDI'] + MEASURES + FLAGS


def normalize_number(series):
    values=pd.to_numeric(series.astype('string').str.strip().str.replace(',', '.', regex=False), errors='coerce')
    return values.replace([float('inf'),float('-inf')],pd.NA)


def diagnose(frame):
    normalized = frame.copy()
    missing = {c:int((frame[c].isna() | frame[c].fillna('').astype(str).str.strip().eq('')).sum()) for c in NUMERIC + ['PRODUCT_ID','TYPE']}
    mixed = {c:int(frame[c].fillna('').astype(str).str.contains(',',regex=False).sum()) for c in MEASURES}
    failed_casts = {c:int((normalize_number(frame[c]).isna() & frame[c].fillna('').astype(str).str.strip().ne('')).sum()) for c in NUMERIC}
    for c in NUMERIC:
        normalized[c] = normalize_number(frame[c])
    return {
        'rows':len(frame),'missing_by_column':missing,'comma_decimal_by_column':mixed,
        'failed_numeric_casts':failed_casts,
        'duplicate_version_udi':int(normalized.duplicated(['SOURCE_SHA256','UDI']).sum()),
        'failure_flag_mismatches':int((normalized['MACHINE_FAILURE'] != normalized[FLAGS[1:]].max(axis=1)).sum()),
        'strategies':{
            'missing':'No imputar: rechazar con motivo porque no hay soporte para inventar mediciones.',
            'formats':'Quitar espacios; coma decimal a punto; convertir tipos con errores auditables.',
            'duplicates':'Misma version+UDI: conservar menor SOURCE_ROW de forma determinista; auditar descarte.',
            'validity':'UDI entero positivo, tipos L/M/H coherentes con producto, medidas fisicas basicas y flags 0/1.',
            'mismatch':'Conservar y marcar: no se conoce cual etiqueta corregir.'}}


def clean(frame):
    out = frame.copy().fillna('')
    out['PRODUCT_ID'] = out['PRODUCT_ID'].astype(str).str.strip()
    out['TYPE'] = out['TYPE'].astype(str).str.strip().str.upper()
    for c in NUMERIC:
        out[c] = normalize_number(out[c])
    reason = pd.Series('', index=out.index)
    def reject(mask, label):
        reason.loc[reason.eq('') & mask.fillna(True)] = label
    reject(out[NUMERIC].isna().any(axis=1) | out['PRODUCT_ID'].eq(''), 'missing_or_invalid_value')
    reject((out['UDI'] <= 0) | (out['UDI'] % 1 != 0), 'invalid_udi')
    reject(~out['TYPE'].isin(['L','M','H']) | out['PRODUCT_ID'].str[0].ne(out['TYPE']), 'invalid_product_type')
    reject((out['AIR_TEMPERATURE_K'] <= 0) | (out['PROCESS_TEMPERATURE_K'] <= 0) |
           (out['ROTATIONAL_SPEED_RPM'] <= 0) | (out['TORQUE_NM'] < 0) | (out['TOOL_WEAR_MIN'] < 0), 'invalid_measurement')
    reject(~out[FLAGS].isin([0,1]).all(axis=1), 'invalid_failure_flag')
    for c in ['ROTATIONAL_SPEED_RPM','TOOL_WEAR_MIN']:
        reject(out[c] % 1 != 0, 'non_integer_measurement')
    out['REJECTION_REASON'] = reason
    valid = out.loc[reason.eq('')].copy()
    if 'SOURCE_ROW' not in valid:
        valid['SOURCE_ROW'] = range(len(valid))
    valid['SOURCE_ROW'] = pd.to_numeric(valid['SOURCE_ROW'],errors='raise')
    valid = valid.sort_values(['SOURCE_SHA256','UDI','SOURCE_ROW'],kind='stable')
    duplicates = valid.duplicated(['SOURCE_SHA256','UDI'])
    dropped = valid.loc[duplicates].copy()
    dropped['REJECTION_REASON'] = 'duplicate_version_udi'
    rejected = pd.concat([out.loc[reason.ne('')], dropped], ignore_index=True)
    valid = valid.loc[~duplicates].drop(columns='REJECTION_REASON')
    for c in ['UDI','ROTATIONAL_SPEED_RPM','TOOL_WEAR_MIN'] + FLAGS:
        valid[c] = valid[c].astype('int64')
    valid['READING_KEY'] = [hashlib.md5(f'{h}|{u}'.encode()).hexdigest() for h,u in zip(valid.SOURCE_SHA256,valid.UDI)]
    valid['FAILURE_FLAG_MISMATCH'] = (valid.MACHINE_FAILURE != valid[FLAGS[1:]].max(axis=1)).astype(int)
    assert len(frame) == len(valid) + len(rejected), 'Se perdieron filas sin justificacion'
    assert valid.READING_KEY.is_unique
    return valid, rejected


def main():
    parser=argparse.ArgumentParser()
    base=Path(os.environ.get('PSET2_DATA_DIR','data'))
    parser.add_argument('--input',type=Path,default=base/'raw/historico.csv')
    parser.add_argument('--output',type=Path,default=base/'processed/ai4i_clean.csv')
    args=parser.parse_args()
    raw=pd.read_csv(args.input,dtype=str,keep_default_na=False)
    audit=diagnose(raw)
    good,bad=clean(raw)
    args.output.parent.mkdir(parents=True,exist_ok=True)
    good.to_csv(args.output,index=False)
    bad.to_csv(args.output.with_name('rechazados.csv'),index=False)
    audit.update(valid_rows=len(good),rejected_rows=len(bad),rejection_reasons=bad.REJECTION_REASON.value_counts().to_dict())
    Path('output').mkdir(exist_ok=True)
    Path('output/calidad_local.json').write_text(json.dumps(audit,indent=2),encoding='utf-8')
    print(json.dumps({'raw':len(raw),'valid':len(good),'rejected':len(bad)}))


if __name__=='__main__':
    main()
