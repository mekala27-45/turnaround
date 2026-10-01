# The Power BI model

Public data from the Bureau of Transportation Statistics, the FAA and OurAirports, with weather from Open-Meteo under CC BY 4.0. Carriers and airports are real and appear as they do in the public record; no individual traveler appears. The findings are a portfolio analysis, not an official ranking and not travel advice.

Tables, relationships and measures; build it on Windows from this file.

## Measures

| Measure | Table | DAX |
|---|---|---|
| scheduled_flights | carrier_month | `SUM('carrier_month'[scheduled])` |
| cancellation_rate | carrier_month | `DIVIDE(SUM('carrier_month'[cancelled]), SUM('carrier_month'[scheduled]))` |
| completion_factor | carrier_month | `1 - DIVIDE(SUM('carrier_month'[cancelled]), SUM('carrier_month'[scheduled]))` |
| diversion_rate | carrier_month | `DIVIDE(SUM('carrier_month'[diverted]), SUM('carrier_month'[scheduled]))` |
| on_time_rate | carrier_month | `DIVIDE(SUM('carrier_month'[on_time]), SUM('carrier_month'[flown]))` |
| mean_arrival_delay | carrier_month | `DIVIDE(SUM('carrier_month'[arr_delay_sum]), SUM('carrier_month'[flown]))` |
| median_arrival_delay | carrier_month | `-- computed in the extract from the minute counts; DAX has no exact median over pre-aggregated counts` |
| mean_scheduled_block | carrier_month | `DIVIDE(SUM('carrier_month'[crs_elapsed_sum]), SUM('carrier_month'[flown]))` |
| mean_actual_block | carrier_month | `DIVIDE(SUM('carrier_month'[actual_elapsed_sum]), SUM('carrier_month'[flown]))` |
| mean_padding | carrier_month | `DIVIDE(SUM('carrier_month'[padding_sum]), SUM('carrier_month'[padding_flights]))` |
| padding_share | carrier_month | `DIVIDE(SUM('carrier_month'[padding_sum]), SUM('carrier_month'[padding_block_sum]))` |
| reported_late_aircraft_share | carrier_month | `DIVIDE(SUM('carrier_month'[cause_late_aircraft_sum]), (SUM('carrier_month'[cause_late_aircraft_sum]) + SUM('carrier_month'[cause_carrier_sum]) + SUM('carrier_month'[cause_nas_sum]) + SUM('carrier_month'[cause_weather_sum]) + SUM('carrier_month'[cause_security_sum])))` |
| reported_carrier_share | carrier_month | `DIVIDE(SUM('carrier_month'[cause_carrier_sum]), (SUM('carrier_month'[cause_late_aircraft_sum]) + SUM('carrier_month'[cause_carrier_sum]) + SUM('carrier_month'[cause_nas_sum]) + SUM('carrier_month'[cause_weather_sum]) + SUM('carrier_month'[cause_security_sum])))` |
| reported_nas_share | carrier_month | `DIVIDE(SUM('carrier_month'[cause_nas_sum]), (SUM('carrier_month'[cause_late_aircraft_sum]) + SUM('carrier_month'[cause_carrier_sum]) + SUM('carrier_month'[cause_nas_sum]) + SUM('carrier_month'[cause_weather_sum]) + SUM('carrier_month'[cause_security_sum])))` |
| reported_weather_share | carrier_month | `DIVIDE(SUM('carrier_month'[cause_weather_sum]), (SUM('carrier_month'[cause_late_aircraft_sum]) + SUM('carrier_month'[cause_carrier_sum]) + SUM('carrier_month'[cause_nas_sum]) + SUM('carrier_month'[cause_weather_sum]) + SUM('carrier_month'[cause_security_sum])))` |
| reported_security_share | carrier_month | `DIVIDE(SUM('carrier_month'[cause_security_sum]), (SUM('carrier_month'[cause_late_aircraft_sum]) + SUM('carrier_month'[cause_carrier_sum]) + SUM('carrier_month'[cause_nas_sum]) + SUM('carrier_month'[cause_weather_sum]) + SUM('carrier_month'[cause_security_sum])))` |
| inherited_share | inherited_month | `DIVIDE(SUM('inherited_month'[inherited_minutes_sum]), SUM('inherited_month'[arr_delay_pos_sum]))` |
| fair_ranking_effect | ranking | `AVERAGE('ranking'[adjusted_effect])` |

## Relationships

- carrier_month[carrier] to carrier[code], many to one
- route_month[carrier] to carrier[code], many to one
- inherited_month[carrier] to carrier[code], many to one
