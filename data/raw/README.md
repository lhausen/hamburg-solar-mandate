# Raw data (not tracked)

The pipeline starts from the Marktstammdatenregister bulk export
(Bundesnetzagentur), roughly 800 MB. It is not part of this repository.

To obtain it, download the *Gesamtdatenexport* with the `open_mastr` package:

```python
from open_mastr import Mastr
Mastr().download(method="bulk")
```

Place the resulting ZIP in this folder (or point the `MASTR_ZIP` environment
variable at it) and run `scripts/00_parse_mastr_bulk.py`, which writes
`mastr_solar_deutschland.csv` here. Everything downstream of that file can
also be run without it, because the aggregated panels it produces are shipped
in `data/panels/`.

The thesis uses the export retrieved in April 2026
(`Gesamtdatenexport_20260401_25.2.zip`). A later export will contain more
recent registrations and will therefore not reproduce the thesis numbers
exactly.
