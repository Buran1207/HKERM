# HKERM · Hong Kong Equity Rotation Monitor

A read-only Streamlit dashboard built from the user's existing 2026-09-02 research dataset. No new iFinD extraction, training or model scoring.

## Deploy (GitHub root)

1. Unzip this archive and upload **the files inside** to the root of a new GitHub repository (not the enclosing folder). Include the hidden `.streamlit/config.toml` if supported.
2. In [Streamlit Community Cloud](https://share.streamlit.io/), create an app using this repository and set main file path to **`app.py`**.
3. Set Python to **3.12** if available. Streamlit installs `requirements.txt` automatically.
4. Share the generated Streamlit URL with your team. **For nonpublic research data, do not publish the repository publicly.** Verify team access / hosting permissions before uploading proprietary files.

## Run locally

```bat
cd C:\HKERM
py -3.12 -m pip install -r requirements.txt
py -3.12 -m streamlit run app.py
```

## Features

- Date selector covering 2026-06-30 to 2026-09-02 (46 observed trading days).
- Market overview, sector relative performance, rotation quadrants and historical trails.
- Sector detail, constituent stock search, CSV export, methodology / quality control notes.
- All data is bundled in `data/`; the website is **read-only** and will not fetch or upload fresh quotes.

## Data and model caveats

- Fixed HSCI constituents as of 2026-10-09 (581 instruments); **historical membership look-ahead**. Historical view is a fixed-universe study, not an investable backtest.
- Raw close prices are unadjusted; a 35% single-day jump screen is only a partial safeguard.
- Total-capitalization proxy is `close * totalShares`; sector weights are lagged X trading days. Returns are arithmetic weighted individual raw price returns, not a dynamically rebalanced tradable sector index.
- Sector excess is sector return less HSCI raw close-to-close return for the same trading-day window.
- Current classifications are research drafts, not all independently audited against financial statements.
- **Do not** use these observed outcomes to retrain or tune your frozen HK quant model's post-2026-08-26 out-of-sample test.
- Because the historical dataset ends 2026-09-02, the dashboard cannot honestly provide dates after that day.

## Updating data in future

Keep the schema and replace the four read-only files under `data/` (`stock_daily.csv.gz`, `sector_daily.csv.gz`, `benchmark.csv`, `stock_master.csv`) and the taxonomy CSV together with consistent as-of dates. Do not commit iFinD credentials, API tokens, local model artifacts, or unpublished research to a public repository.
