-- Ninguna fila puede perderse silenciosamente: válida o rechazada.
select 1 as invalid_reconciliation
where (select count(*) from {{ source('raw', 'ai4i') }}) <>
    (select count(*) from {{ ref('ai4i_clean') }}) +
    (select count(*) from {{ ref('ai4i_rejected') }})


