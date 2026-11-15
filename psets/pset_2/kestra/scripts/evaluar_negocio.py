"""Evalúa referencias y sensibilidad. No entrena ni afirma un beneficio industrial."""
import argparse
import copy
import hashlib
import io
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scripts.common import report
from scripts.decision_policy import assumptions, costs, probability_threshold, rule_alert, score


def evaluate(frame, config=None):
    config = config or assumptions()
    c = costs(config)
    labels = frame['MACHINE_FAILURE'].astype(int).tolist()
    rule = [rule_alert(row, config['rule']) for row in frame.to_dict(orient='records')]
    if 'BASELINE_ALERT' in frame and frame['BASELINE_ALERT'].astype(int).tolist() != rule:
        raise ValueError('La OBT no coincide con la regla de referencia versionada')
    policies = {'never_alert': [0] * len(labels), 'always_alert': [1] * len(labels), 'expert_candidate': rule}
    scores = {name: score(labels, alerts, c['inspection'], c['missed_delay_loss'])
              for name, alerts in policies.items()}
    scenarios = []
    for inspection in config['sensitivity']['inspection_costs']:
        for loss in config['sensitivity']['missed_delay_losses']:
            values = {name: score(labels, alerts, inspection, loss)['illustrative_incremental_cost_per_1000']
                      for name, alerts in policies.items()}
            scenarios.append({'inspection': inspection, 'missed_delay_loss': loss,
                              'future_probability_threshold': probability_threshold(inspection, loss),
                              'cost_per_1000_by_policy': values, 'lowest_cost_reference': min(values, key=values.get)})
    margin_sensitivity = []
    for margin in config['sensitivity']['contribution_margins_per_hour']:
        variant = copy.deepcopy(config)
        variant['reference_plant']['contribution_margin_per_downtime_hour'] = margin
        variant_costs = costs(variant)
        margin_sensitivity.append({'contribution_margin_per_hour': margin, **variant_costs,
                                   'future_probability_threshold': probability_threshold(
                                       variant_costs['inspection'], variant_costs['missed_delay_loss'])})
    operating_sensitivity = []
    for plant in config['sensitivity']['plant_loads']:
        opportunities = plant['machines'] * plant['opportunities_per_machine_day']
        workload = scores['expert_candidate']['alert_rate'] * opportunities
        operating_sensitivity.append({**plant,
            'interpretation': 'Dimensionamiento hipotético suponiendo mezcla sintética; no tasa real de planta',
            'hypothetical_alerts_per_day': workload,
            'hypothetical_false_alerts_per_day': scores['expert_candidate']['fp'] / len(labels) * opportunities,
            'exceeds_capacity_under_assumed_mix': workload > config['reference_plant']['inspection_capacity_per_day']})
    return {'assumptions_version': config['version'], 'rule_version': config['rule']['version'],
            'cost_status': config['status'], 'horizon': 'current_observation_only',
            'costs': c, 'future_calibrated_probability_threshold': probability_threshold(c['inspection'], c['missed_delay_loss']),
            'references': scores, 'sensitivity': scenarios,
            'margin_sensitivity': margin_sensitivity, 'operating_sensitivity': operating_sensitivity,
            'future_model_gate': config['future_model_gate'],
            'deployment_authorized': False, 'causal_savings_estimated': False,
            'interpretation': 'Etiquetas observadas; costos ilustrativos. Sin modelo entrenado ni pronóstico temporal.'}


def main():
    import pandas as pd
    parser = argparse.ArgumentParser()
    parser.add_argument('--source-csv', help='CSV AI4I original; si se omite, lee la OBT de Snowflake')
    parser.add_argument('--clean-csv',help='CSV limpio canonico producido por limpiar.py')
    args = parser.parse_args()
    if args.clean_csv:
        frame=pd.read_csv(args.clean_csv).rename(columns={'TYPE':'PRODUCT_TYPE'})
        frame['SOURCE_KEY']=frame['SOURCE_SHA256']
        scope='clean_csv'
    elif args.source_csv:
        from kestra.ingesta_csv import HEADERS, COLUMNS
        raw = Path(args.source_csv).read_bytes()
        frame = pd.read_csv(io.BytesIO(raw))
        if list(frame.columns) != HEADERS:
            raise ValueError('Contrato de fuente modificado')
        frame.columns = COLUMNS
        frame = frame.rename(columns={'TYPE': 'PRODUCT_TYPE'})
        frame['SOURCE_KEY'] = hashlib.sha256(raw).hexdigest()
        scope = 'source_csv_not_snowflake_obt'
    else:
        from scripts.common import connect, database
        with connect() as conn:
            with conn.cursor() as cur:
                cur.execute(f'SELECT * FROM {database()}.OBT.AI4I_OBT')
                frame = cur.fetch_pandas_all()
        scope = 'snowflake_obt'
    results = {str(version): evaluate(group) for version, group in frame.groupby('SOURCE_KEY')}
    if not results:
        raise ValueError('No hay observaciones para evaluar')
    report('negocio.json', {'evidence_scope': scope, 'versions': results})


if __name__ == '__main__':
    main()

