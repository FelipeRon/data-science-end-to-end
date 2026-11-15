import pytest

from scripts.decision_policy import assumptions, costs, probability_threshold, rule_alert, score


def normal(**changes):
    row = dict(AIR_TEMPERATURE_K=300, PROCESS_TEMPERATURE_K=310,
               ROTATIONAL_SPEED_RPM=1500, TORQUE_NM=40,
               TOOL_WEAR_MIN=100, PRODUCT_TYPE='L')
    return {**row, **changes}


def test_economic_threshold_and_reference_totals():
    c = costs()
    assert c['planned_total'] == 1400
    assert c['emergency_total'] == 4600
    assert c['missed_delay_loss'] == 2000
    assert c['first_year_fixed_model_cost'] == 3600
    assert probability_threshold(c['inspection'], c['missed_delay_loss']) == pytest.approx(.025)


def test_cost_matrix_counts_inspection_for_true_and_false_alerts():
    r = score([1,1,0,0], [1,0,1,0], 50, 2000)
    assert (r['tp'],r['fn'],r['fp'],r['tn']) == (1,1,1,1)
    assert r['illustrative_incremental_cost_total'] == 2100
    assert r['precision'] == .5 and r['recall'] == .5


def test_rule_wear_boundary_and_binary_only_inputs():
    assert rule_alert(normal(TOOL_WEAR_MIN=199)) == 0
    assert rule_alert(normal(TOOL_WEAR_MIN=200)) == 1
    with pytest.raises(ValueError):
        score([1,0], [1], 50, 2000)
    with pytest.raises(ValueError):
        rule_alert(normal(PRODUCT_TYPE='X'))
    with pytest.raises(ValueError):
        rule_alert(normal(TORQUE_NM=float('nan')))


def test_rule_overstrain_boundary_is_strict_and_type_specific():
    # Menos de 200 min de desgaste y potencia dentro del rango para aislar OSF.
    assert rule_alert(normal(TOOL_WEAR_MIN=180, TORQUE_NM=62, ROTATIONAL_SPEED_RPM=1200,
                             PROCESS_TEMPERATURE_K=311, PRODUCT_TYPE='L')) == 1
    assert rule_alert(normal(TOOL_WEAR_MIN=180, TORQUE_NM=62, ROTATIONAL_SPEED_RPM=1200,
                             PROCESS_TEMPERATURE_K=311, PRODUCT_TYPE='M')) == 0


def test_no_predictions_yet_means_no_deployment_claim():
    import pandas as pd
    from scripts.evaluar_negocio import evaluate
    frame = pd.DataFrame([{**normal(), 'MACHINE_FAILURE':0},
                          {**normal(TOOL_WEAR_MIN=220), 'MACHINE_FAILURE':1}])
    r = evaluate(frame)
    assert len(r['sensitivity']) == 9
    assert r['deployment_authorized'] is False
    assert r['causal_savings_estimated'] is False
    assert r['horizon'] == 'current_observation_only'
    assert [x['missed_delay_loss'] for x in r['margin_sensitivity']] == [1400,2000,3200]
    assert len(r['operating_sensitivity']) == 4

