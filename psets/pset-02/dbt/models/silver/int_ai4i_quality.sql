{{ config(materialized='view') }}
select *,
    case
        when udi is null or udi <= 0 then 'invalid_udi'
        when product_id is null or product_type is null then 'missing_product'
        when product_type not in ('L', 'M', 'H') then 'invalid_type'
        when left(product_id, 1) <> product_type then 'inconsistent_product_type'
        when air_temperature_k is null or process_temperature_k is null
          or rotational_speed_rpm is null or torque_nm is null or tool_wear_min is null
            then 'missing_or_invalid_measurement'
        when air_temperature_k <= 0 or process_temperature_k <= 0
          or rotational_speed_rpm <= 0 or torque_nm < 0 or tool_wear_min < 0
            then 'out_of_domain_measurement'
        when machine_failure is null or twf is null or hdf is null
          or pwf is null or osf is null or rnf is null then 'missing_failure_flag'
        when machine_failure not in (0,1) or twf not in (0,1) or hdf not in (0,1)
          or pwf not in (0,1) or osf not in (0,1) or rnf not in (0,1)
            then 'invalid_failure_flag'
        else null
    end as rejection_reason,
    -- Se informa, no se reescribe el target: los flags no son una verdad independiente.
    case when machine_failure <> greatest(twf, hdf, pwf, osf, rnf)
         then 1 else 0 end as failure_flag_mismatch
from {{ ref('stg_ai4i') }}

