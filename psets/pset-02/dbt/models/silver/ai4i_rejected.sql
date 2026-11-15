{{ config(materialized='view') }}
select * from {{ ref('int_ai4i_quality') }} where rejection_reason is not null

