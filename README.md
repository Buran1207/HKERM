# HKERM｜Hong Kong Equity Rotation Monitor

**GitHub / Streamlit 发布包：V1.1，2026-11-05**  
基于用户提供的 HKERM_Streamlit_GitHub 原代码修改；保留原有五个页面、HSCI 基准、中英文界面、成分股联动及 TradingView 跳转。

## 本次改动

1. **研究日期：日历选择器** (`st.date_input`)。日期上下限自动读取打包行情中赛道与 HSCI 共同具有的最早、最新交易日。本次数据范围为 **2026-06-25 至 2026-11-02，90 个交易日**。周末/假日选择自动回退到当日之前最近交易日，不使用以后交易日数据。选定历史日时，所有股票、收益和 RRG 轨迹均以当日为截止。
2. **观察周期：1–60 交易日连续滑块** (`st.slider`)；默认 5 日。1/5/20/60 日保留原有预计算的行业/个股收益，其他任意周期从内置未复权收盘价及窗口期初市值权重计算。原始打包数据之前缺乏连续行情时显示缺数，不推算不存在的历史。
3. **轮动四象限与轨迹改为 USERM 一致的 RRG 风格 X/Y**：相对基准始终为 **HSCI**，X=100×exp[EMA14(log RS)−EMA36(log RS)]，Y=100×X/X(5个交易日前)，四象限中心点为 (100,100)，保留原先历史方向箭头及起止标记。
4. **历史赛道深度图**：随所选周期变化（包括任意中间周期）。RRG 的 EMA14/36、5日动量固定，不随收益观察周期变化。股票筛选、速览与赛道详情增加当前所选周期的收益列。
5. **原始数据完全保留**。本次不重新取数、不触碰已冻结模型、不执行任何机器学习。两份旧的单文件 HOTFIX ZIP 已从新发布包移除，避免覆盖已更新的 `app.py`。

详细公式、可用日期以及已知偏差见 [`RRG_METHOD.md`](RRG_METHOD.md)。

## 直接部署到 GitHub / Streamlit

1. 解压发布压缩包，**把压缩包内文件放在 GitHub 仓库根目录**（不是将外层文件夹直接上传）。必须同时上传 `app.py`、`hkerm_rotation.py`、`data/`、`requirements.txt`、`README.md`、`.streamlit/config.toml`，以及可选的 `tests/` 和 `RRG_METHOD.md`。
2. 若是覆盖旧 HKERM 仓库，GitHub 中上传对应新文件并 **Commit changes**。如果使用浏览器网页上传，确认新文件 `hkerm_rotation.py` 也上传成功，否则 `app.py` 会报 `ModuleNotFoundError`。
3. 打开 [Streamlit Community Cloud](https://share.streamlit.io/) 并绑定仓库，**Main file path = `app.py`**，建议 Python 3.12。
4. 不需要 USERM 的应用密码变量，HKERM 本版没有新增访问密码验证。
5. 更新历史数据时仅需替换 `data/` 下的对应快照；**行情许可或内部研究资料未获公开分发授权时，不应把仓库或网页开放给公众**。Streamlit 网页访问控制与 GitHub 仓库可见性是两件不同的事。

### Windows 本地运行

```bat
cd /d C:\code\HKERM
py -3.12 -m pip install -r requirements.txt
py -3.12 -m streamlit run app.py
```

### 可选的计算测试

```bat
cd /d C:\code\HKERM
py -3.12 -m pip install pytest
py -3.12 -m pytest tests\test_rotation.py -q
```

## 数据现状与局限

| 数据集 | 截止日期 | 用途 |
|---|---|---|
| `data/benchmark.csv` | 2026-11-02 | HSCI 收盘价与已算好的1/5/20/60日收益 |
| `data/sector_daily.csv.gz` | 2026-11-02 | 80个研究赛道日收益、股数、广度与集中度 |
| `data/stock_daily.csv.gz` | 2026-11-02 | 581只固定HSCI研究股票池的历史行情快照；具体有价股票数可能更少 |
| `data/stock_master.csv` + `taxonomy.csv` | 固定研究分类 | 赛道与股票归属；不是逐日历史真实成分名单 |

**重要限制：** 目前仅有90个打包交易日。对首段早期历史，EMA36与5日动量需要合计41个交易日观测，较早日期不会画出伪造的RRG坐标。1/5/20/60日预计算收益可能使用了打包开始之前的价格，不能据此反向重建更早的每日RS曲线。

所有股票价格未复权；>35%日异常涨跌屏蔽只是有限的防护，并非拆股/分红的完整复权处理。行业指数是按原有市值加权日收益连乘构造的**研究代理**，不是可交易ETF或官方指数，也不是 StockCharts 授权的 JdK RS-Ratio / RS-Momentum。研究资料固定2026-10-09成分股票池及分类，历史具有幸存者偏差。

**This is a research dashboard, not a trade execution system or proprietary StockCharts RRG reproduction.**
