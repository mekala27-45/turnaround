# Decisions

Dated entries, newest last. Entries tagged `correction` render into the corrections log at the end
of the story and on the corrections page. Numbers here are the ones the decision was made on; the
current values are in `RESULTS.md`, rendered from the manifest.

## 2026-09-30: the name is turnaround

The time an aircraft spends at the gate between legs is where its day is won or lost, and the
chapter on inherited delay is about exactly that interval. `blocktime` was the other candidate; it
names the schedule, not the place the delay moves through.

## 2026-09-30: the data comes in through the PC, not the build machine

The machine that built this repository could not reach transtats.bts.gov, registry.faa.gov or
open-meteo.com. `deploy/fetch-data.ps1` downloaded every monthly on time file, the registry and the
weather on a Windows machine that could, and the files were staged into the build. OurAirports is
read from its GitHub mirror, which is the same file the project publishes.

## 2026-09-30: weather at the FAA Core 30, not at every airport

The brief asks for hourly weather at every airport in the data for the whole window. Open-Meteo's
free tier allows 10,000 calls a day, and it counts a request for more than two weeks of one
location as several calls: a year at one airport is about 26 calls, so roughly 380 airports for
eleven and a half years is on the order of 110,000 calls, eleven days of quota. The weather is
pulled at the thirty airports the FAA itself uses for its delay statistics, about 360 requests, and
the weather chapter estimates on flights between two of them. The README's first paragraph says so.

## 2026-09-30: no visibility field

Open-Meteo's historical archive has no visibility variable (the forecast API does, the reanalysis it
archives does not). Low cloud cover and the WMO weather code, whose fog and thunderstorm codes are
the conditions that close runways, stand in for it. Temperature, precipitation, snowfall, wind speed
and gusts are pulled as the brief asks.

## 2026-09-30: three palette slots moved by the validator

The ported validator rejected four adjacent pairs in the brief's palette on lightness and chroma
separation: dark slots one and two (vermilion and blue at the same lightness, 0.654 and 0.655), dark
slots six, seven and eight, and light slots seven and eight. Each was moved by the smallest
lightness step that passes, hue and chroma kept: dark slot two `#5B8DEF` to `#6A9DFF`, dark slot seven
`#2E9DD3` to `#44AEE5`, light slot eight `#95561F` to `#93541D`. The validator now passes both modes
and the dark card; its own figures (worst adjacent colour vision separation 12.5 light and 12.4 dark)
replace the brief's.

## 2026-09-30: the derived flight files are not committed

Seventy million rows of derived parquet would put several gigabytes in the repository. The marts
the story, the site, the workbook and the BI extracts read are committed, with the manifest; the
monthly flight parquet is rebuilt from the raw files by `make data`, and the rederive starts there.

## 2026-09-30: the FAA registry keeps the aircraft, not the owner

The releasable registry carries the registrant's name and street address for every aircraft,
including private owners. Only the tail number, manufacturer, model, type, engine type, seats and
year built survive ingest; the identifier scan fails on any registrant column name or the raw
registry header in a committed file.
