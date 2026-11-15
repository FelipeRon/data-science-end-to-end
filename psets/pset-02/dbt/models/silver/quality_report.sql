{{ config(materialized='view') }}
select source_sha256,
    count(*) as source_rows,
    count_if(rejection_reason is not null) as rejected_rows,
    count_if(rejection_reason is null) as valid_rows,
    count_if(rejection_reason = 'missing_product') as missing_product_rows,
    count_if(rejection_reason = 'missing_or_invalid_measurement') as invalid_measurement_rows,
    sum(failure_flag_mismatch) as failure_flag_mismatches,
    count(*) - count(distinct reading_key) as duplicate_keys,
    sum(machine_failure) as machine_failure_rows,
    avg(machine_failure) as failure_rate,
    min(air_temperature_k) as min_air_temperature_k,
    max(air_temperature_k) as max_air_temperature_k,
    min(torque_nm) as min_torque_nm,
    max(torque_nm) as max_torque_nm
from {{ ref('int_ai4i_quality') }}
group by source_sha256

