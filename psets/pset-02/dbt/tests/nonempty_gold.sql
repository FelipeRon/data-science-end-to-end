select 1 as empty_gold where not exists (select 1 from {{ ref('fact_reading') }})

