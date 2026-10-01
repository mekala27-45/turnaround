{# Shared expressions, written once. #}

{% macro season(month) -%}
    cast(case when {{ month }} in (12, 1, 2) then 0 when {{ month }} in (3, 4, 5) then 1
              when {{ month }} in (6, 7, 8) then 2 else 3 end as integer)
{%- endmacro %}

{% macro hour_block(hour) -%}
    cast({{ hour }} // 3 as integer)
{%- endmacro %}

{# The rules that remove a row from every analysis. The others exclude a row from one analysis. #}
{% macro excluded_everywhere(alias='') -%}
    {%- set p = alias ~ '.' if alias else '' -%}
    ({{ p }}q_duplicate_key or {{ p }}q_actual_without_scheduled or {{ p }}q_impossible_time or {{ p }}q_elapsed_mismatch)
{%- endmacro %}

{# Arrival delay under fifteen minutes on a flight that flew to its destination: the A14 convention. #}
{% macro on_time(arr_delay) -%}
    ({{ arr_delay }} < 15)
{%- endmacro %}
