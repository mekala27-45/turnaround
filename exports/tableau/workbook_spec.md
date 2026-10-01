# The Tableau companion workbook

Public data from the Bureau of Transportation Statistics, the FAA and OurAirports, with weather from Open-Meteo under CC BY 4.0. Carriers and airports are real and appear as they do in the public record; no individual traveler appears. The findings are a portfolio analysis, not an official ranking and not travel advice.

The extracts are CSV files of the shipped marts, with exactly the marts' rows (a test holds them to it).
The route by month extract is one CSV per year under `mart_route_month/`; open it with a wildcard union
of `mart_route_month_*.csv` so the years read as one table.
Open them in Tableau Public, relate them on carrier, year and month, and build the views below.
The companion reads the same numbers as the site; the site is the reference.

| View | Source | Rows | Columns | Filters | On the site |
|---|---|---|---|---|---|
| On time rate by month | mart_carrier_month | `SUM([on_time]) / SUM([flown])` | `MAKEDATE([year], [month], 1)` | carrier | the explorer's first chart |
| Arrival delay by hour | mart_route_month joined to the hour profile on the site; here by month | `SUM([arr_delay_sum]) / SUM([flown])` | `[month]` | carrier, origin, dest, year | the explorer's second chart |
| Padding by month | mart_route_month | `SUM([padding_sum]) / SUM([flown])` | `MAKEDATE([year], [month], 1)` | carrier, route | the explorer's padding series |
| Reported cause shares | mart_carrier_month | `SUM([cause_<field>_sum]) / (sum of the five cause sums)` | `the five cause fields, pivoted` | carrier, year | the explorer's cause chart |
| The fair ranking slope chart | exports/csv/ch5_ranking.csv | `[Raw rank] and [Adjusted rank] as two columns, a line per carrier` | `Measure Names (raw, adjusted)` | none | chapter 5's chart |
