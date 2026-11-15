import pandas as pd
from kestra.calidad.limpiar import clean, diagnose


def row(**changes):
    values=dict(UDI='1',PRODUCT_ID='L123',TYPE='L',AIR_TEMPERATURE_K='300',PROCESS_TEMPERATURE_K='310',
                ROTATIONAL_SPEED_RPM='1500',TORQUE_NM='40',TOOL_WEAR_MIN='10',MACHINE_FAILURE='0',
                TWF='0',HDF='0',PWF='0',OSF='0',RNF='0',SOURCE_SHA256='version',SOURCE_ROW='1')
    return {**values,**changes}


def test_formats_duplicates_missing_and_invalid_are_accounted():
    raw=pd.DataFrame([row(TORQUE_NM=' 40,5 ',TYPE=' l '),row(SOURCE_ROW='2'),
                      row(UDI='2',SOURCE_ROW='3',TORQUE_NM=''),
                      row(UDI='3',SOURCE_ROW='4',MACHINE_FAILURE='9')])
    good,bad=clean(raw)
    assert len(good)==1 and len(bad)==3
    assert good.TORQUE_NM.iloc[0]==40.5 and good.TYPE.iloc[0]=='L'
    assert set(bad.REJECTION_REASON)=={'duplicate_version_udi','missing_or_invalid_value','invalid_failure_flag'}
    assert diagnose(raw)['comma_decimal_by_column']['TORQUE_NM']==1


def test_mismatches_are_retained_and_versions_not_collapsed():
    raw=pd.DataFrame([row(MACHINE_FAILURE='1'),row(SOURCE_SHA256='another',MACHINE_FAILURE='1')])
    good,bad=clean(raw)
    assert len(good)==2 and bad.empty
    assert good.READING_KEY.is_unique and good.FAILURE_FLAG_MISMATCH.sum()==2


def test_history_retry_is_idempotent_after_csv_roundtrip():
    from scripts.ingesta_historico import merge_history
    existing=pd.DataFrame([row(SOURCE_ROW='1')])
    batch=pd.DataFrame([row(SOURCE_ROW=1),row(UDI='2',SOURCE_ROW=2)])
    first=merge_history(existing,batch)
    assert len(first)==2
    assert len(merge_history(first.astype(str),batch))==2
