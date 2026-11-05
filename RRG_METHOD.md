# HKERM RRG 坐标与自选观察周期说明（2026-11-05）

## 1. 数据与 HSCI 基准

- 相对基准始终为 **恒生综合指数 HSCI**，从 `data/benchmark.csv` 的 `close` 获取，未替换成 HSI/HSCEI/恒生科技指数。
- 原版 `sector_daily.csv.gz` 中的 `ret_1` 是各研究赛道当日总市值代理加权原始股价收益。逐日连乘生成研究用赛道价格指数：

  `SectorIndex[t] = SectorIndex[t-1] * (1 + sector_ret_1[t])`

  同时用 HSCI 每日收盘价构造 `HSCIIndex[t]`。为了避免把包外数据当作内部已知历史，最早打包日期为共同基期。当某赛道中间缺失日度收益时，新的连续片段重新进行 EMA 预热。
- 用相对价格序列 `RS[t] = SectorIndex[t] / HSCIIndex[t]`，横纵轴只用截止日及此前数据。

## 2. 横轴：相对强度趋势 X

```
L[t] = ln(RS[t])
EMA_fast[t] = EMA(L[t], span=14, adjust=False, min_periods=14)
EMA_slow[t] = EMA(L[t], span=36, adjust=False, min_periods=36)
X[t] = 100 * exp(EMA_fast[t] - EMA_slow[t])
```

- `X > 100`：最近的平滑相对强度趋势高于更长周期，赛道相对于 HSCI 呈现较强趋势。
- `X < 100`：近期相对趋势弱于更长期趋势。
- **这是 USERM 使用的对数EMA几何比值版本**，不是直接对原始RS做算术 EMA14(RS)/EMA36(RS)，也不是 StockCharts/JdK 的授权原始公式。两者经济直觉接近，数值并不严格相同。

## 3. 纵轴：最近五个交易日的相对趋势变化 Y

```
Y[t] = 100 * X[t] / X[t-5]
```

- `Y > 100`：相对趋势比五个交易日前改善。
- `Y < 100`：相对趋势比五个交易日前减弱。
- 100代表中性线，Y=101不代表ETF或行业绝对上涨1%，仅表示指标X相对于5日前升高1%。
- 至少36个历史点才能形成X，且Y还需额外5个交易日，因此在打包历史前40个交易日缺少完整 RRG 坐标是**正确行为**。

| 位置 | 条件 | 解释 |
|---|---|---|
| 右上（领先强化） | X≥100 且 Y≥100 | 相对趋势较强且继续改善 |
| 右下（领先减弱） | X≥100 且 Y<100 | 相对趋势较强但动量转弱 |
| 左上（落后改善） | X<100 且 Y≥100 | 相对趋势偏弱但正在改善 |
| 左下（落后持续） | X<100 且 Y<100 | 相对趋势偏弱且继续恶化 |

四象限是**研究图表**，并非直接买卖建议；即使赛道相对HSCI变强，仍可能发生绝对跌幅。

## 4. 自选观察周期与RRG的区别

- **观察周期滑块：1–60个交易日，步长1。** 影响赛道相对收益、排名、广度、成分股展示和赛道深度图，**不改变**固定的RRG EMA14/EMA36/5日坐标。
- 对 `h ∈ {1,5,20,60}`，沿用既有预计算的 `ret_h`、`excess_h`、`n_h`、`breadth_h`、`concentration_h`、`hsciret_h`，以保留旧版口径及已有早期历史收益。
- 对其他h，使用当时实际可用 `P[t]` 与 `P[t-h]`：

  `stock_return_i = P_i[t]/P_i[t-h] - 1`

  `weight_i = (P_i[t-h] * shares_i[t-h]) / Σ(P_j[t-h] * shares_j[t-h])`

  `sector_return_h = Σ_i(weight_i * stock_return_i)`

  `sector_excess_h = sector_return_h - (HSCI_close[t]/HSCI_close[t-h]-1)`

  仅有两端有效、期初市值代理正值且观察窗内没有绝对单日原始价格跳变超过35%的股票进入计算。上涨广度为有效股票中X日涨幅为正的占比，集中度为最大期初市值权重。
- 只使用**精确匹配的历史日期**，不前填缺失股票价格，不用未来价格填补。如果所选日期过早以致缺少h个打包交易日，非预计算周期会显示缺值。

## 5. 研究日期选择

- 日期范围自动计算为打包的 `sector_daily` 与 HSCI `benchmark.csv` 的共同交易日期：目前 `2026-06-25` 至 `2026-11-02`。
- 使用 Streamlit 日期日历选择器；周末/假日取**此前最近交易日**，不会回退到之后的交易日。
- 即使选择最早的2026-06-25，页面仍可显示存在的基本行情、预计算收益以及个股信息，只是 RRG 不会生成缺少历史支持的点。

## 6. 与StockCharts的关系

StockCharts 对官方 Relative Rotation Graph 的公开解释是：横轴为 JdK RS-Ratio，纵轴为 JdK RS-Momentum，两轴都围绕100；RRG轨迹长度可以调节，基准可以选HSCI等市场指数。官方指标有专有计算细节，本程序使用上述完全公开、可重现的 EMA 近似，与USERM同步，但**不能声称计算结果与 StockCharts JdK 数值完全相同**。

参考：

- [StockCharts RRG Charts](https://help.stockcharts.com/charts-and-tools/other-charting-tools/rrg-charts)
- [StockCharts ChartSchool: Relative Rotation Graphs](https://chartschool.stockcharts.com/table-of-contents/chart-analysis/chart-types/relative-rotation-graphs-rrg-charts)
- [StockCharts ChartSchool: RRG Relative Strength](https://chartschool.stockcharts.com/table-of-contents/technical-indicators-and-overlays/technical-indicators/rrg-relative-strength)

## 7. 风险与历史解释

固定2026-10-09 HSCI成分股集合用于回溯，属于固定研究股票池，不是历史真实指数成分。行业交易收益未复权、历史日成分股分类非逐日点时；如遇拆股、分红、换手或者极端行情，原始行情和衍生的轮动代理可能出现误差。此图不表示实际资金净流入，研究日期也不能用来模拟已经知道未来信息的下单策略。
