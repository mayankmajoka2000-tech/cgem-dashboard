# C-GEM Carbon Credit Intelligence - website source

Build files for the C-GEM carbon credit dashboard website (Apache Superset in Docker).
The Dockerfile rebuilds the site from the files part_00, part_01 and so on (one packed copy of dashboard version 78).
patch_v78.py holds the settings used only on the website (longer chart timeout, chart results cache).

## Price model site (GitHub Pages)

The `docs/` folder is a separate static website for the C-GEM India carbon price model (version 14). It does not change the Superset site above; the Dockerfile does not use it.

- `docs/index.html`: platform home with live numbers and links to every tool
- `docs/dashboard.html`: India Carbon Price Dashboard (prices by credit type, price index, demand against supply, model accuracy, 5,013 Indian projects)
- `docs/weekly.html` and `docs/api/weekly/`: weekly C-GEM India Carbon Index; publish a new issue with `python3 tools/weekly_index.py`
- `docs/methodology.html`: method, tests, version history, training data, price feed
- `docs/downloads/`: workbook, Python model and data files
- `docs/calculator.html`: credit price, quote check, project finance and risk, integrity, CBAM, CCTS, buyer portfolio and forward curve
- `docs/data/`: the CSV files the dashboard reads
- `docs/model/`: model coefficients (`price_model.json`) and the Python version (`cgem_price_model.py`)

To publish it: Settings → Pages → Build and deployment → Source "Deploy from a branch", branch `main`, folder `/docs`.
