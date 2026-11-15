-- Pregunta: que tipo de producto presenta mayor proporcion observada de fallas?
select SOURCE_SHA256, TYPE, count(*) as OBSERVATIONS,
    sum(MACHINE_FAILURE)::bigint as FAILURES,
    avg(MACHINE_FAILURE::double) as FAILURE_RATE,
    avg(TORQUE_NM) as AVG_TORQUE_NM
from {{ ref('int_ai4i') }}
group by SOURCE_SHA256, TYPE
