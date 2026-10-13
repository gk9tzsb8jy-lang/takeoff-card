# takeoff-card
## FAA declared distances

`.github/workflows/faa-declared-distances.yml` runs weekly. It downloads the FAA NASR airport CSV for the current 28-day cycle and adds TORA/ASDA to `runways.json` (`tools/faa_dd.py`). Run it from the Actions tab after rebuilding `runways.json` from OurAirports.
