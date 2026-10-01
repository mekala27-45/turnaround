{# A model with no rows passes every other test vacuously; this one refuses to. #}
{% test not_empty(model) %}
select 1 as empty from (select count(*) as n from {{ model }}) where n = 0
{% endtest %}
