-- Conversión explícita; los fallos de conversión se vuelven NULL y son auditables.
select
    md5(source_sha256 || '|' || udi) as reading_key,
    try_to_number(udi)::integer as udi,
    nullif(trim(product_id), '') as product_id,
    upper(nullif(trim(type), '')) as product_type,
    try_to_double(air_temperature_k) as air_temperature_k,
    try_to_double(process_temperature_k) as process_temperature_k,
    try_to_number(rotational_speed_rpm)::integer as rotational_speed_rpm,
    try_to_double(torque_nm) as torque_nm,
    try_to_number(tool_wear_min)::integer as tool_wear_min,
    try_to_number(machine_failure)::integer as machine_failure,
    try_to_number(twf)::integer as twf,
    try_to_number(hdf)::integer as hdf,
    try_to_number(pwf)::integer as pwf,
    try_to_number(osf)::integer as osf,
    try_to_number(rnf)::integer as rnf,
    source_sha256, source_url, batch_id, loaded_at
from {{ source('raw', 'ai4i') }}


