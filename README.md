# N600NJ performance card

Offline takeoff, landing and weight & balance card for N600NJ (Aerostar 600A), served by GitHub Pages from `main` at https://gk9tzsb8jy-lang.github.io/takeoff-card/. Add it to the iPhone/iPad home screen; it works offline through `sw.js`. Bump the `-vN` part of `VERSION` in `sw.js` on every change.

## FAA runway data

`.github/workflows/faa-declared-distances.yml` runs Thursdays at 0902Z, one minute after a new 28-day FAA cycle takes effect, and rebuilds `runways.json` with `tools/build_db.py`: US airports entirely from FAA NASR (lengths, true headings, elevations, displaced thresholds, TORA/ASDA/LDA), everywhere else from OurAirports. KSPG reads from the same data. Each run writes `tools/build-report.txt`; `runways.json` is only replaced when the sanity checks pass.

## Backup

A copy is also deployed to Netlify at https://n600nj-card.netlify.app by a weekly scheduled task that builds from this repo.
