select distinct source_sha256 as source_key, source_url,
    'UCI AI4I 2020 (synthetic)' as source_name
from {{ ref('ai4i_clean') }}

