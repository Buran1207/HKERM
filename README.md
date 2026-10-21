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

## 2026-10-21 页面交互修复

- Sidebar 下拉框采用高对比度白底深色选中值；下拉选项也明确使用深色文字。
- 市场总览增加「赛道成分股速览」：选赛道查看股票、市值代理、成交额及多期限价格收益。
- 轮动地图增加「查看地图赛道成分股」，快速展示市值前25只。
- 个股筛选现在按日期、行业、指数和关键词实时过滤；选中具体股票后展示指标与历史走势图，不再只是静态大表。
- 保留2026-09-02截止的原数据，不新增采集、不连接训练模型。
- 解压本ZIP后将根目录的 app.py、requirements.txt、data/、.streamlit/、README.md 等直接覆盖 GitHub 仓库根目录。提交后等待 Streamlit Cloud 重新部署。


## 2026-10-21 UI 增强
- 标题全用陈述式，轮动地图改为「赛道成分股」。
- 轨迹独立成图，箭头指向较晚日期；空心圆标记起点，菱形标记终点。
- 总览速览、轮动地图、赛道深度、个股筛选四张股票表均添加「TradingView ↗」可点击列；个股详情提供直接跳转按钮。
- 港股代码 `0700.HK` → `https://www.tradingview.com/symbols/HKEX-700/`。网站不处理 TradingView 账户认证，用户浏览器已登录时由 TradingView 维持会话。
