-- The quarantine report counts every reported row, and the excluded rows are the ones missing from the fact table.
with report as (select sum(rows) as rows, sum(excluded) as excluded from {{ ref('mart_quarantine') }}),
     source as (select count(*) as rows from {{ ref('stg_flights') }}),
     fact as (select count(*) as rows from {{ ref('fct_flights') }})
select * from report, source, fact
where report.rows <> source.rows or source.rows - report.excluded <> fact.rows
