select 1 as invalid_reconciliation
where (select count(*) from {{ ref('ai4i_clean') }}) <>
      (select count(*) from {{ ref('fact_reading') }})

