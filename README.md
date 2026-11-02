# Is the Rawasheen's Breeze Still There? Afternoon sea breeze over Historic Jeddah (Al-Balad), 1940–2025

Working paper by **Amir Khan**, Independent Researcher ([ORCID 0009-0008-5996-2841](https://orcid.org/0009-0008-5996-2841)).

**Finding:** in ERA5 (1940–2025, 753,888 hourly records), ~68% of afternoon hours (13:00–17:00) over Al-Balad bring wind from
270–360°; 67.2% in 1940–69 vs 67.7% in 1996–2025; no significant trend (Mann–Kendall τ = −0.050, p = 0.50).

- `paper.pdf` / `paper.docx` / `paper.md`: the paper
- `code/analysis.py`: fetches ERA5 via Open-Meteo (not stored here, ~21 MB) and writes all `tables/`, `figures/` and `results.json`
- `code/build_docx.py`: rebuilds `paper.docx` from `paper.md` (PDF via `soffice --headless --convert-to pdf paper.docx`)

## Reproduce
```bash
pip install -r requirements.txt
python code/analysis.py
python code/build_docx.py
```

## Cite
Khan, A. (2026). *Is the rawasheen's breeze still there? Afternoon sea-breeze persistence over Historic Jeddah (Al-Balad), 1940–2025* [Working paper]. https://github.com/amirator/al-balad-sea-breeze-era5 (Zenodo DOI: to be added). See `CITATION.cff`.

## Licences
- Code: MIT (`LICENSE`).
- Text, tables, original figures: CC BY 4.0 (`LICENSE-CONTENT.md`).
- Figure 2 photo: Saudi Press Agency, Wikimedia Commons, **CC BY-SA 4.0** (credit in `LICENSE-CONTENT.md` and the caption).
- Map basemap © OpenStreetMap contributors (ODbL). ERA5: contains modified Copernicus Climate Change Service information.
