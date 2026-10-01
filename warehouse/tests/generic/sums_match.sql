{# The model's column summed equals an expression over another model: a mart that dropped rows fails. #}
{% test sums_match(model, column_name, compare_model, compare_expression) %}
with a as (select sum({{ column_name }}) as v from {{ model }}),
     b as (select {{ compare_expression }} as v from {{ compare_model }})
select * from a, b where a.v is distinct from b.v
{% endtest %}
