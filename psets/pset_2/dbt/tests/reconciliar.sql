select 1 as mismatch
where (select count(*) from {{ source('raw','ai4i_clean') }}) <>
      (select sum(OBSERVATIONS) from {{ ref('mart_fallas_por_tipo') }})
