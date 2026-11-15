select * exclude rejection_reason
from {{ ref('int_ai4i_quality') }}
where rejection_reason is null


