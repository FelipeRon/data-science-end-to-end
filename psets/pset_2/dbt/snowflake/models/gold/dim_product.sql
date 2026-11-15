select distinct md5(product_id || '|' || product_type) as product_key,
    product_id, product_type
from {{ ref('ai4i_clean') }}


