-- Grano: una observación UDI dentro de una versión SHA256 del archivo fuente.
select reading_key, udi,
    md5(product_id || '|' || product_type) as product_key,
    source_sha256 as source_key,
    air_temperature_k, process_temperature_k, rotational_speed_rpm,
    torque_nm, tool_wear_min, machine_failure, twf, hdf, pwf, osf, rnf,
    failure_flag_mismatch, loaded_at
from {{ ref('ai4i_clean') }}

