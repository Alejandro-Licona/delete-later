# White Star Capital — Strategy Tracker Dashboard

## Run locally

```bash
streamlit run dashboard.py
```

For the full local dev environment (other scripts, Jupyter, etc.):

```bash
pip install -r requirements-full.txt
```

## Deploy on Streamlit Cloud

1. Push this repo to GitHub (including the `data/` folder and `ws_exclusions.py`).
2. Go to [share.streamlit.io](https://share.streamlit.io), sign in, **New app**.
3. Connect your repo and set **Main file path** to `dashboard.py`.
4. Deploy. The repo’s `requirements.txt` is already minimal (streamlit, plotly, pandas, numpy) so the Cloud build stays fast and reliable.

Data is read from `data/` at runtime; keep those CSVs committed so the deployed app has charts.
