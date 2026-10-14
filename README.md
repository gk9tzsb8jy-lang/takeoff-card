# takeoff-card
## FAA declared distances

`.github/workflows/faa-declared-distances.yml` runs weekly and rebuilds `runways.json` with `tools/build_db.py`: US airports entirely from the FAA NASR 28-day airport data (lengths, true headings, elevations, displaced thresholds, TORA/ASDA/LDA), everywhere else from OurAirports. Each run writes `tools/build-report.txt`; `runways.json` is only replaced when the sanity checks pass.
