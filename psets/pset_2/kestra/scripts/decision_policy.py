"""Política versionada para detección actual; no estima RUL ni una probabilidad."""
import json
import math
from pathlib import Path


def assumptions():
    return json.loads(Path(__file__).with_name('business_assumptions.json').read_text(encoding='utf-8'))


def rule_alert(row, rule=None):
    rule = rule or assumptions()['rule']
    air = float(row['AIR_TEMPERATURE_K'])
    process = float(row['PROCESS_TEMPERATURE_K'])
    rpm = float(row['ROTATIONAL_SPEED_RPM'])
    torque = float(row['TORQUE_NM'])
    wear = float(row['TOOL_WEAR_MIN'])
    product_type = row['PRODUCT_TYPE']
    if product_type not in rule['overstrain_above_min_nm']:
        raise ValueError('Tipo de producto desconocido')
    if not all(math.isfinite(x) for x in (air, process, rpm, torque, wear)):
        raise ValueError('Medición no finita')
    power = torque * rpm * (2 * math.pi / 60)
    return int((process - air < rule['heat_delta_below_k'] and rpm < rule['heat_speed_below_rpm'])
               or power < rule['power_below_w'] or power > rule['power_above_w']
               or wear * torque > rule['overstrain_above_min_nm'][product_type]
               or wear >= rule['wear_at_least_min'])


def spark_rule_expression(rule=None):
    from pyspark.sql import functions as F
    rule = rule or assumptions()['rule']
    limit = F.when(F.col('PRODUCT_TYPE') == 'L', rule['overstrain_above_min_nm']['L']) \
             .when(F.col('PRODUCT_TYPE') == 'M', rule['overstrain_above_min_nm']['M']) \
             .otherwise(rule['overstrain_above_min_nm']['H'])
    power = F.col('TORQUE_NM') * F.col('ROTATIONAL_SPEED_RPM') * F.lit(2 * math.pi / 60)
    return (((F.col('PROCESS_TEMPERATURE_K') - F.col('AIR_TEMPERATURE_K') < rule['heat_delta_below_k'])
             & (F.col('ROTATIONAL_SPEED_RPM') < rule['heat_speed_below_rpm']))
            | (power < rule['power_below_w']) | (power > rule['power_above_w'])
            | (F.col('TOOL_WEAR_MIN') * F.col('TORQUE_NM') > limit)
            | (F.col('TOOL_WEAR_MIN') >= rule['wear_at_least_min'])).cast('int')


def costs(config=None):
    config = config or assumptions()
    c = config['costs']
    margin = config['reference_plant']['contribution_margin_per_downtime_hour']
    return {
        'planned_total': c['planned_direct'] + c['planned_downtime_hours'] * margin,
        'emergency_total': c['emergency_direct'] + c['emergency_downtime_hours'] * margin,
        'inspection': c['inspection_per_alert'],
        'first_year_fixed_model_cost': 12 * c['monthly_model_operation'] + c['first_year_setup'],
        'missed_delay_loss': c['extra_delay_hours_if_missed'] * margin + c['extra_secondary_damage_if_missed']
    }


def probability_threshold(inspection, missed_delay_loss):
    if inspection <= 0 or missed_delay_loss <= 0:
        raise ValueError('Costos deben ser positivos')
    # Para costos C_TP=C_FP=inspección, C_FN=demora y C_TN=0.
    # Si el cociente supera 1, no hay una alerta económicamente favorable.
    return inspection / missed_delay_loss


def confusion(labels, alerts):
    labels, alerts = list(labels), list(alerts)
    if len(labels) != len(alerts) or not labels:
        raise ValueError('Etiquetas y alertas deben tener igual longitud no vacía')
    result = dict(tp=0, fp=0, fn=0, tn=0)
    for target, alert in zip(labels, alerts):
        if target not in (0, 1) or alert not in (0, 1):
            raise ValueError('Se requieren etiquetas y alertas binarias')
        result['tp' if target and alert else 'fn' if target else 'fp' if alert else 'tn'] += 1
    return result


def score(labels, alerts, inspection, missed_delay_loss):
    matrix = confusion(labels, alerts)
    n = sum(matrix.values())
    count = matrix['tp'] + matrix['fp']
    precision = matrix['tp'] / count if count else None
    recall = matrix['tp'] / (matrix['tp'] + matrix['fn']) if matrix['tp'] + matrix['fn'] else None
    total = inspection * count + missed_delay_loss * matrix['fn']
    return {**matrix, 'rows': n, 'alerts': count, 'precision': precision,
            'recall': recall, 'alert_rate': count / n,
            'illustrative_incremental_cost_total': total,
            'illustrative_incremental_cost_per_1000': total * 1000 / n}

