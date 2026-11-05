"""HKERM | Hong Kong Equity Rotation Monitor — read-only research dashboard."""
from pathlib import Path
import io
import re
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from hkerm_rotation import (resolve_asof, rrg_coordinates, rrg_state,
                            sector_horizon_snapshot, stock_period_returns, sector_horizon_history)

BASE=Path(__file__).resolve().parent
st.set_page_config(page_title='HKERM | Hong Kong Equity Rotation Monitor',page_icon='📈',layout='wide',initial_sidebar_state='expanded')
CSS='''<style>
.block-container{padding-top:1.3rem;padding-bottom:2rem;max-width:1540px}
[data-testid="stSidebar"]{background:#111e32}
[data-testid="stSidebar"] label,[data-testid="stSidebar"] .stCaption,[data-testid="stSidebar"] p{color:#eaf2ff!important}
/* The date picker and sliders should work on the dark sidebar. */
[data-testid="stSidebar"] [data-testid="stDateInput"] input{background:#fff!important;color:#15243a!important;-webkit-text-fill-color:#15243a!important}
[data-testid="stSidebar"] [data-testid="stDateInput"] svg{color:#15243a!important}
/* Select boxes use a LIGHT background. Text in both chosen values and options must be DARK. */
[data-testid="stSidebar"] [data-baseweb="select"] > div{background:#fff!important;border:1px solid #9baec5!important}
[data-testid="stSidebar"] [data-baseweb="select"] [role="combobox"],
[data-testid="stSidebar"] [data-baseweb="select"] [role="combobox"] *,
[data-testid="stSidebar"] [data-baseweb="select"] input,
[data-testid="stSidebar"] [data-baseweb="select"] span,
[data-testid="stSidebar"] [data-baseweb="select"] div[data-testid="stMarkdownContainer"]{color:#15243a!important;-webkit-text-fill-color:#15243a!important;opacity:1!important}
[data-testid="stSidebar"] [data-baseweb="select"] svg{fill:#15243a!important;color:#15243a!important}
[data-baseweb="popover"] [role="option"], [data-baseweb="popover"] [role="option"] *{color:#15243a!important;-webkit-text-fill-color:#15243a!important}
[data-baseweb="popover"] [aria-selected="true"]{background:#d9eaf9!important}
h1,h2,h3{letter-spacing:-.035em}h1{font-weight:750!important}
.kicker{color:#7893ad;font-size:12px;font-weight:700;letter-spacing:2px}
.info{font-size:12px;color:#64748b}.section{font-size:13px;color:#718096;text-transform:uppercase;letter-spacing:1.1px}
div[data-testid="stMetric"]{background:#f5f8fc;border:1px solid #e6ecf3;padding:14px;border-radius:10px}
div[data-testid="stMetricLabel"]{font-weight:600}
div[data-testid="stMetricValue"]{font-size:1.7rem}
</style>''' 
st.markdown(CSS,unsafe_allow_html=True)
# Display language is a presentation preference only; source data and classification keys remain unchanged.
with st.sidebar:
    language=st.selectbox('Language / 语言', ['English', '中文'], index=0, key='hkerm_language')
EN=language=='English'
_TRANSLATIONS={
 '研究日期 / As of':'Research date / As of','观察周期':'Lookback period','研究行业':'Research industry',
 '全部行业':'All industries','赛道最低有效股票数':'Minimum valid stocks per sector',
 '数据止于 2026-09-02':'Data through 2026-09-02',
 '固定2026-10-09成分名单回看；非历史真实指数成分。':'Constituent list fixed as of 2026-10-09; not historical index membership.',
 '研究试算 · 未复权价格 · 非交易信号':'Research only · Unadjusted prices · Not trading signals',
 '市场总览':'Market overview','轮动地图':'Rotation map','赛道深度':'Sector explorer','个股筛选':'Stock explorer','方法与数据质量':'Methodology & data quality',
 '领先强化':'Leading & strengthening','领先减弱':'Leading & weakening','落后改善':'Lagging & improving','落后持续':'Lagging & weakening',
 '相对强弱排行榜':'Relative performance ranking','状态分布':'Rotation state distribution','研究提醒':'Research notes',
 '赛道成分股速览':'Sector constituents quick view','选择赛道 · 查看成分股':'Select sector · View constituents',
 '全部赛道排名':'All sector rankings','相对强度 × 边际动量':'Relative strength × momentum',
 '历史轮动轨迹':'Historical rotation trajectories','选择赛道查看轨迹':'Select sectors for trajectories',
 '轨迹长度（交易日）':'Trajectory length (sessions)','赛道成分股':'Sector constituents',
 '查看地图赛道成分股':'View constituents of a mapped sector','选择细分赛道':'Select subindustry',
 '赛道股票（按当日总市值代理排序）':'Sector stocks (ranked by market-cap proxy)',
 '个股筛选 · 研究日股票查询':'Stock screener · As-of research',
 '输入股票代码、公司名称或赛道':'Search ticker, company or sector',
 '指数成员筛选':'Index membership','股票所属行业':'Stock industry','全部':'All',
 '选择股票 · 显示下方详情及历史走势':'Select stock · Show details and price history',
 '数据说明与质量控制':'Methodology and data quality','核心公式':'Key formulas','数据来源':'Data sources',
 '数据质量摘要':'Data quality summary','母池股票数':'Universe stocks','现有细分赛道':'Subindustries','网页可选日期':'Available dates',
 'HSCI':'HSCI','排名':'Rank','一级行业':'Industry','细分赛道':'Subindustry','状态':'State',
 '有效股数':'Valid stocks','上涨广度':'Positive breadth','最大市值权重':'Largest-stock cap weight',
 '超额日变化':'Daily excess change', 'RRG相对趋势 X':'RRG relative trend X', 'RRG相对动量 Y':'RRG relative momentum Y', '历史不足':'Insufficient history', '所选日非交易日，已自动回退至':'Non-trading day: reverted to', 'RRG需要至少36个交易日趋势数据及额外5日动量历史；选定日期暂不满足。':'RRG needs at least 36 sessions for trend plus 5 additional sessions for momentum; insufficient as-of history.', '历史曲线展示RRG相对趋势X与5日动量Y；自选周期收益使用当前日期重新计算。':'This historical chart shows RRG X and 5-session Y; the selected-period return is calculated at the research date.','总市值代理(亿)':'Cap proxy (HKD 100m)','成交额(百万)':'Turnover (HKD m)',
 '股票代码':'Ticker','公司名称':'Company','分类核验':'Mapping review','名称':'Name','股票':'Ticker',
 '代码':'Ticker','收盘价':'Close','分类来源':'Mapping source','核验状态':'Review status',
 '市值代理_亿':'Cap proxy (HKD 100m)','总市值代理(亿)':'Cap proxy (HKD 100m)',
 '当前可用收盘价':'Last available close','5日价格收益':'5D price return',
 '总市值代理（亿）':'Cap proxy (HKD 100m)','收盘价':'Close','未复权收盘价':'Unadjusted close',
 '交易日期':'Trading date','赛道超额收益':'Sector excess return','相对HSCI超额':'Excess vs HSCI',
 '最大股票市值权重':'Largest-stock cap weight','领先赛道：':'Leading sectors: ',
 '相对落后：':'Lagging sectors: ','选择':'Select',
 '当前筛选：':'Filtered: ','只股票':' stocks','赛道股票共 ':'Sector stocks: ',
 ' 只；按所选日期的总市值代理降序排列，缺失市值置后。':' (ranked by as-of cap proxy, missing last).',
 '当前日期与最低股票数条件下没有有效赛道，请调低左侧最低有效股票数。':'No qualifying sectors. Lower the minimum valid-stock threshold.',
 '当前筛选条件下没有可分析的赛道。':'No qualifying sectors for this selection.',
 '没有符合条件的股票。请清除搜索词，或将指数/行业筛选改为「全部」。':'No matching stocks. Clear the query or set filters to All.',
 '所选日期无该股票行情。可以尝试选择另一只股票或其他研究日期。':'No price data for this stock on the selected date. Try another stock or date.',
 '所选赛道在此日期缺少足够的连续轨迹记录。':'Insufficient history for the chosen sector trajectories.',
 '下载当前日期赛道排名 CSV':'Download sector rankings CSV', '下载该赛道股票数据':'Download sector stocks CSV',
 '下载当前筛选股票 CSV':'Download filtered stocks CSV','在 TradingView 打开该股票 ↗':'Open this stock in TradingView ↗',
 '打开图表 ↗':'Open chart ↗','TradingView ↗':'TradingView ↗',
}
_TRANSLATIONS['口径：赛道X日收益＝窗口期初总市值代理（收盘价×总股本）加权个股X日原始价格收益；赛道X日超额＝赛道X日收益－恒生综指同期收益。未复权，极端原始价格跳变窗口已过滤。']='Method: X-day sector return is weighted by start-of-window market-cap proxy (close × total shares); sector excess equals sector return minus the corresponding HSCI return. Unadjusted prices; extreme raw-price jump windows are excluded.'
_TRANSLATIONS['四象限采用USERM一致的公开近似定义：RS＝赛道日收益连乘构造的相对价格÷HSCI；X＝100×exp(EMA14(ln RS)－EMA36(ln RS))；Y＝100×X÷5个交易日前的X。以100为中性线；不是StockCharts专有JdK指标。']='RRG-style coordinates use USERM’s public approximation: RS = chained sector daily-return proxy / HSCI; X = 100 × exp(EMA14(log RS) − EMA36(log RS)); Y = 100 × X / X from five sessions earlier. Both center at 100. These are not proprietary JdK indicators.'
_TRANSLATIONS['无需跳转页面：选择任意赛道，立即查看其中所有股票及市值排序。行业筛选与研究日期同步生效。']='Select a sector to view its stocks and cap-proxy ranking without leaving this page. Industry and date filters apply.'
_TRANSLATIONS['强势≠资金净流入。成交量、价格及南向持仓属于不同证据；当前数据尚未纳入南向资金或业绩催化。']='Relative strength does not imply net capital inflow. Volume, price and Southbound holdings are distinct evidence. Southbound flows and earnings catalysts are not included.'
_TRANSLATIONS['箭头方向＝较早交易日 → 较晚交易日；空心圆为起点，菱形为终点。横轴为RRG相对趋势X，纵轴为5日RRG相对动量Y，均以100为中性线。']='Arrows point from earlier to later sessions; an open circle shows the start and a diamond shows the end. X is RRG-style relative trend; Y is five-session RRG momentum; both center at 100.'
_TRANSLATIONS['最多显示按市值排序前25只；完整名单可在「市场总览」的赛道速览查看。']='Displays up to 25 largest stocks; the full constituent list is on Market overview.'
_TRANSLATIONS['用途：按照股票、行业、指数成员资格过滤581股，然后选中单只股票查看具体价格、收益和历史走势。所有筛选和图表随左侧研究日期变化。']='Filter 581 stocks by ticker, industry and index membership; select a stock for prices, returns and history. All views follow the research date.'
_TRANSLATIONS['该页采用研究用固定成分股分类；个别公司分类仍未按年报全部核验。龙头高度集中时，赛道走势可能主要代表单只股票。']='Sector classifications use a fixed research universe. Some company mappings remain provisional. Highly concentrated sectors may track a single large stock.'
_TRANSLATIONS['研究范围']='Coverage'
_TRANSLATIONS['复权限制']='Corporate-action adjustments'
_TRANSLATIONS['历史前视']='Look-ahead risk'
_TRANSLATIONS['日度轮动动量']='Daily rotation momentum'
_TRANSLATIONS['上涨广度']='Positive breadth'
_TRANSLATIONS['最大市值权重']='Largest cap weight'
_TRANSLATIONS['研究页面不显示南向净流入或基本面催化']='Southbound flows and fundamental catalysts are not shown'
_TRANSLATIONS['上传的港股原始日行情 data.zip；2026年10月9日四个恒生指数成分股CSV；HKERM统一研究工作簿20260902（赛道及分类）']='Uploaded HK daily quotes data.zip; four Hang Seng constituent CSVs dated 2026-10-09; HKERM sector mapping workbook (2026-09-02).'
_TRANSLATIONS['若后续重新生成数据，只需保持 data/ 中CSV结构一致并更新仓库；当前版本不连接iFinD、不调用量化模型、不修改本地训练数据。']='To refresh data, maintain the CSV schemas under data/ and update the repository. The site does not connect to iFinD, run quant models or modify training data.'
_TRANSLATIONS['跑赢HSCI的赛道']='Sectors outperforming HSCI'
_TRANSLATIONS['有效股票数中位数']='Median valid stocks'
_TRANSLATIONS['原始价格收益']='raw price return'
_TRANSLATIONS['相对HSCI超额收益']='Excess return vs HSCI'
_TRANSLATIONS['超额收益日变化']='Daily excess-return momentum'
_TRANSLATIONS['相对收益']='Excess return'
_TRANSLATIONS['请选择']='Select'
_TRANSLATIONS['选择赛道']='Select sector'
_TRANSLATIONS['当前日期']='Selected date'
_TRANSLATIONS['历史价格（截至所选日）']='Historical prices (through selected date)'
_TRANSLATIONS['当前可用收盘价']='Last available close'
_TRANSLATIONS['细分赛道：']='Sector: '
_TRANSLATIONS['分类状态：']='Mapping status: '
_TRANSLATIONS['在 TradingView 打开该股票 ↗']='Open in TradingView ↗'
_TRANSLATIONS['使用浏览器现有 TradingView 会话；账号登录由 TradingView 管理。']='Uses your existing browser TradingView session. Login is managed by TradingView.'
_TRANSLATIONS['例如：0700、腾讯、半导体']='e.g. 0700, Tencent, Semiconductors'
_TRANSLATIONS['赛道股票共']='Sector members: '
_TRANSLATIONS['起点']='Start'
_TRANSLATIONS['终点']='End'
_TRANSLATIONS['已选赛道']='Selected sectors'
_TRANSLATIONS['相对HSCI超额']='Excess vs HSCI'
_TRANSLATIONS['所选日期无该股票行情。可以尝试选择另一只股票或其他研究日期。']='No prices for this stock on the selected date. Choose another stock or date.'
def T(s):
    if not EN: return s
    out=str(s)
    for zh,en in sorted(_TRANSLATIONS.items(),key=lambda x:-len(x[0])):
        out=out.replace(zh,en)
    out=out.replace('个交易日',' sessions').replace('D收益(%)','D return (%)').replace('D收益%','D return %').replace('D赛道收益','D sector return').replace('D超额vs HSCI','D excess vs HSCI').replace('D加权收益','D weighted return')
    return out

def display_states(series):return series.map(lambda x:T(x))

COLORS={'rise':'#168c78','fall':'#d65c61','navy':'#172d49','blue':'#3e79ae','gold':'#d5a453'}

@st.cache_data(show_spinner=False)
def load():
 d=BASE/'data'
 s=pd.read_csv(d/'sector_daily.csv.gz',dtype={'sector_id':str,'sector':str},parse_dates=['date'])
 p=pd.read_csv(d/'stock_daily.csv.gz',dtype={'code':str},parse_dates=['date'])
 m=pd.read_csv(d/'stock_master.csv',dtype={'code':str,'sector_id':str})
 t=pd.read_csv(d/'taxonomy.csv',dtype={'sector_id':str})
 b=pd.read_csv(d/'benchmark.csv',parse_dates=['date'])
 for col in ['HSI','HSCEI','HSTECH']:m[col]=pd.to_numeric(m[col],errors='coerce').fillna(0).astype(int)
 return s,p,m,t,b
sectors,prices,master,tax,bench=load()
sectors=sectors.merge(tax[['sector_id','industry']],on='sector_id',how='left')
# Research-calendar dates are actual bundled sessions shared by sector and HSCI.
calendar=pd.DatetimeIndex(sorted(set(sectors.date)&set(bench.date)))
if calendar.empty:
 st.error('No common sector/HSCI trading dates in data.');st.stop()

@st.cache_data(show_spinner=False)
def cached_rrg(sector_data,benchmark_data):
 return rrg_coordinates(sector_data,benchmark_data)

rrg=cached_rrg(sectors[['date','sector_id','ret_1']],bench[['date','close']])
with st.sidebar:
 st.markdown(T('### HKERM'))
 st.caption(T('HONG KONG EQUITY ROTATION MONITOR'))
 st.divider()
 requested=st.date_input(T('研究日期 / As of'),
                         value=calendar[-1].date(),
                         min_value=calendar[0].date(),
                         max_value=calendar[-1].date(),
                         format='YYYY-MM-DD')
 horizon=st.slider(T('观察周期'),min_value=1,max_value=60,value=5,step=1,
                   help=('Number of trading sessions for performance ranking. RRG EMA14/36 and 5-session momentum are independent of this setting.' if EN
                         else '收益排行榜观察窗口（交易日）；RRG的EMA14/36与5日动量固定，不受此滑块影响。'))
 industry_choice=st.selectbox(T('研究行业'),[T('全部行业')]+sorted(tax.industry.dropna().unique().tolist()))
 min_n=st.slider(T('赛道最低有效股票数'),1,10,3)
 st.divider()
 st.caption(('Available range: ' if EN else '原始数据可选范围：')+f'{calendar[0].date()} — {calendar[-1].date()}')
 st.caption(T('固定2026-10-09成分名单回看；非历史真实指数成分。'))
 st.caption(T('研究试算 · 未复权价格 · 非交易信号'))

asof=resolve_asof(requested,calendar)
selected=asof.strftime('%Y-%m-%d')
if asof.date()!=requested:
 st.info(f"{'Requested calendar date' if EN else '所选日期'} {requested} "
         f"{'is not a trading day. Using prior session:' if EN else '不是交易日，自动显示此前最近一个交易日：'} {selected}")

snapshot,bm=sector_horizon_snapshot(sectors,prices,master,bench,asof,horizon)
stock_custom=stock_period_returns(prices,bench,asof,horizon)
frame=snapshot.merge(tax[['sector_id','industry']],on='sector_id',how='left')
frame=frame.merge(rrg.loc[rrg.date==asof,['sector_id','x','y']].rename(
    columns={'x':'rrg_x','y':'rrg_y'}),on='sector_id',how='left')
if industry_choice!=T('全部行业'):
 frame=frame[frame.industry==industry_choice]
ret=f'ret_{horizon}';ex=f'excess_{horizon}';num=f'n_{horizon}'
breadth=f'breadth_{horizon}';con=f'concentration_{horizon}'
frame=frame[(frame[num]>=min_n)&frame[ex].notna()].copy().sort_values(ex,ascending=False)
frame['state']=[rrg_state(x,y) for x,y in zip(frame.rrg_x,frame.rrg_y)]
frame['rank']=np.arange(1,len(frame)+1)

def pct(x):return f'{x:+.2%}' if pd.notna(x) else '—'
def tradingview_url(code):
    """Official TradingView HKEX instrument page; keep login/session with TradingView."""
    value=str(code).strip().upper()
    m=re.fullmatch(r'(\d{1,5})(?:\.HK)?',value)
    if not m: return None
    ticker=str(int(m.group(1)))
    return f'https://www.tradingview.com/symbols/HKEX-{ticker}/'

def linked_stock_table(table, code_column, label='TradingView ↗'):
    """Provide real clickable per-stock external links, alongside all original columns."""
    result=table.copy()
    # Resolve the ticker from raw schema first. Some callers already localize headers.
    # Never assume a Chinese column exists when the UI is in English.
    candidates=[code_column,T(code_column),'股票代码','股票','代码','Ticker','code']
    found=next((candidate for candidate in candidates if candidate in result.columns),None)
    if found is None:
        st.error(T('缺少股票代码字段；无法建立TradingView链接。'))
        st.dataframe(result,use_container_width=True,hide_index=True)
        return
    # Add URL before changing display headers. The link column is independent of language.
    result['TradingView ↗']=result[found].map(tradingview_url)
    result=result.rename(columns={c:T(c) for c in result.columns if c!='TradingView ↗'})
    st.dataframe(result,use_container_width=True,hide_index=True,
        height=min(650,80+len(result)*35),
        column_config={'TradingView ↗':st.column_config.LinkColumn('TradingView ↗',display_text=T('打开图表 ↗'))})

def figstyle(fig,height=420):
 fig.update_layout(template='plotly_white',height=height,margin=dict(l=10,r=20,t=32,b=20),font=dict(family='Arial, sans-serif',size=12,color='#20334a'),paper_bgcolor='#ffffff',plot_bgcolor='#ffffff',hoverlabel=dict(bgcolor='white'),legend=dict(orientation='h',y=1.12,x=0))
 return fig

def view_table(df,columns=None):
 st.dataframe(df if columns is None else df[columns],use_container_width=True,hide_index=True,height=min(650,80+len(df)*35))

def sector_constituents(sid, asof, limit=None):
    """Point-in-time *prices*, fixed current membership; no returns are recomputed."""
    cols=['code','close','amount','cap','ret_1','ret_5','ret_20','ret_60']
    members=master.loc[master.sector_id==sid,['code','name','sector','mapping_review']].merge(
        prices.loc[prices.date==asof,cols],on='code',how='left'
    ).sort_values('cap',ascending=False,na_position='last')
    members=members.merge(stock_custom,on='code',how='left')
    members['总市值代理(亿)']=(members.cap/1e8).round(1)
    members['成交额(百万)']=(members.amount/1e6).round(1)
    for h in (1,5,20,60):members[f'{h}D收益(%)']=(members[f'ret_{h}']*100).round(2)
    members[f'{horizon}D收益(%)']=(members.ret_custom*100).round(2)
    shown=['code','name','总市值代理(亿)','成交额(百万)',f'{horizon}D收益(%)',
           '1D收益(%)','5D收益(%)','20D收益(%)','60D收益(%)','mapping_review']
    visible=members[list(dict.fromkeys(shown))].rename(
        columns={'code':'股票代码','name':'公司名称','mapping_review':'分类核验'})
    # Keep stable raw column names for all downstream consumers; localize only on display.
    return visible if limit is None else visible.head(limit)

def stock_chart(stock_code, asof):
    h=prices[(prices.code==stock_code)&(prices.date<=asof)].sort_values('date').copy()
    if h.empty:
        st.warning(T('所选日期无该股票行情。可以尝试选择另一只股票或其他研究日期。'))
        return
    obj=master[master.code==stock_code].iloc[0]
    last=h.iloc[-1]
    a,b,c=st.columns(3)
    a.metric(T('当前可用收盘价'),f"{last['close']:.3f}" if pd.notna(last['close']) else '—')
    value=stock_custom.loc[stock_custom.code==stock_code,'ret_custom']
    b.metric(T(f'{horizon}日价格收益'),pct(value.iloc[0]) if len(value) else '—')
    c.metric(T('总市值代理（亿）'),f"{last['cap']/1e8:,.1f}" if pd.notna(last['cap']) else '—')
    fig=go.Figure(go.Scatter(x=h.date,y=h.close,mode='lines+markers',line=dict(color=COLORS['blue'],width=2.7),name=T('收盘价')))
    fig.update_layout(xaxis_title=T('交易日期'),yaxis_title=T('未复权收盘价'),title=f"{obj['name']} · {stock_code} | "+('Historical prices' if EN else '历史价格'))
    st.plotly_chart(figstyle(fig,340),use_container_width=True)
    st.caption((f"Sector: {obj['sector']} · Mapping: {obj['mapping_review']}. Unadjusted price history is limited to bundled dates." if EN else f"细分赛道：{obj['sector']} ｜ 分类状态：{obj['mapping_review']}。走势图仅覆盖网页内置交易日，未复权。"))

def description():
 st.caption(T('口径：赛道X日收益＝窗口期初总市值代理（收盘价×总股本）加权个股X日原始价格收益；赛道X日超额＝赛道X日收益－恒生综指同期收益。未复权，极端原始价格跳变窗口已过滤。'))

st.markdown('<div class="kicker">HKERM  /  INSTITUTIONAL MARKET MONITOR</div>',unsafe_allow_html=True)
st.title('Hong Kong Equity Rotation Monitor' if EN else '香港股票行业轮动监测')
st.caption((f'As of {selected} · Fixed HSCI research universe 581 stocks · Qualifying sectors {len(frame)}/{len(tax)} · Daily' if EN else f'研究日期 {selected}　·　HSCI固定成分研究池 581只　·　当前有效赛道 {len(frame)} / {len(tax)}　·　数据频率：日度'))
tabs=st.tabs([T(x) for x in ['市场总览','轮动地图','赛道深度','个股筛选','方法与数据质量']])

with tabs[0]:
 a,b,c,d=st.columns(4)
 a.metric(f'HSCI {horizon}D '+('raw price return' if EN else '原始价格收益'),pct(bm))
 b.metric(T('跑赢HSCI的赛道'),f'{int((frame[ex]>0).sum())} / {len(frame)}')
 c.metric(T('领先强化'),int((frame.state=='领先强化').sum()))
 d.metric(T('有效股票数中位数'),f'{frame[num].median():.0f}' if len(frame) else '—')
 st.markdown(T('### 相对强弱排行榜'))
 left,right=st.columns([1.35,1])
 with left:
  top=pd.concat([frame.head(12),frame.tail(8)]).drop_duplicates('sector_id').sort_values(ex)
  fig=px.bar(top,x=ex,y='sector',orientation='h',color=ex,color_continuous_scale=['#d56667','#eff2f5','#178b7a'],color_continuous_midpoint=0,hover_data=['industry',num,'rank'])
  fig.update_coloraxes(showscale=False);fig.update_xaxes(tickformat='.0%');fig.update_layout(xaxis_title=T('相对HSCI超额收益'),yaxis_title=None)
  st.plotly_chart(figstyle(fig,580),use_container_width=True)
 with right:
  st.markdown(T('**状态分布**'))
  states=frame.state.value_counts().reset_index();states.columns=['state','count'];states['state']=display_states(states['state'])
  fig=px.pie(states,names='state',values='count',hole=.69,color='state',color_discrete_map={T('领先强化'):'#168c78',T('领先减弱'):'#d4aa56',T('落后改善'):'#497cae',T('落后持续'):'#d65c61'})
  fig.update_traces(textposition='inside',textinfo='percent',insidetextorientation='horizontal',textfont=dict(size=14,color='white'),hovertemplate='%{label}: %{value} · %{percent}<extra></extra>')
  fig.update_layout(template='plotly_white',height=380,margin=dict(l=8,r=8,t=30,b=100),showlegend=True,
      legend=dict(orientation='h',x=.5,xanchor='center',y=-.08,yanchor='top',font=dict(size=12)),
      uniformtext_minsize=11,uniformtext_mode='hide',paper_bgcolor='#fff')
  st.plotly_chart(fig,use_container_width=True)
  st.caption('Quadrants are available after the RRG warm-up period; earlier dates show insufficient history.' if EN else '四象限须满足RRG历史预热要求；更早的日期显示历史不足。')
  st.markdown(T('**研究提醒**'))
  st.info(T('强势≠资金净流入。成交量、价格及南向持仓属于不同证据；当前数据尚未纳入南向资金或业绩催化。'))
  if len(frame):
   top3='、'.join(frame.head(3).sector.tolist());weak='、'.join(frame.tail(3).sector.tolist())
   st.markdown((f'**Leading sectors:** {top3}\n\n**Lagging sectors:** {weak}' if EN else f'**领先赛道：**{top3}。\n\n**相对落后：**{weak}。'))
 description()
 st.markdown(T('### 赛道成分股速览'))
 st.caption(T('无需跳转页面：选择任意赛道，立即查看其中所有股票及市值排序。行业筛选与研究日期同步生效。'))
 if len(frame):
  quick_ids=frame.sector_id.tolist()
  quick=st.selectbox(T('选择赛道 · 查看成分股'),quick_ids,format_func=lambda x:next((r['sector'] for _,r in frame[frame.sector_id==x].iterrows()),x),key='overview_quick_sector')
  subset=sector_constituents(quick,asof)
  st.caption((f'{len(subset)} stocks; descending as-of cap proxy, missing last.' if EN else f'赛道股票共 {len(subset)} 只；按所选日期的总市值代理降序排列，缺失市值置后。'))
  linked_stock_table(subset,'股票代码')
 else:
  st.warning(T('当前日期与最低股票数条件下没有有效赛道，请调低左侧最低有效股票数。'))
 st.markdown(T('### 全部赛道排名'))
 listing=frame[['rank','industry','sector','state',num,ret,ex,breadth,con,'rrg_x','rrg_y']].copy()
 listing.columns=[T('排名'),T('一级行业'),T('细分赛道'),T('状态'),T('有效股数'),T(f'{horizon}D赛道收益'),T(f'{horizon}D超额vs HSCI'),T('上涨广度'),T('最大市值权重'),T('RRG相对趋势 X'),T('RRG相对动量 Y')];listing[T('状态')]=display_states(listing[T('状态')])
 st.dataframe(listing,use_container_width=True,hide_index=True,column_config={T(f'{horizon}D赛道收益'):st.column_config.NumberColumn(format='%.2f%%'),T(f'{horizon}D超额vs HSCI'):st.column_config.NumberColumn(format='%.2f%%')}) if False else view_table(listing.assign(**{T(f'{horizon}D赛道收益'):(listing[T(f'{horizon}D赛道收益')]*100).round(2),T(f'{horizon}D超额vs HSCI'):(listing[T(f'{horizon}D超额vs HSCI')]*100).round(2),T('上涨广度'):(listing[T('上涨广度')]*100).round(1),T('最大市值权重'):(listing[T('最大市值权重')]*100).round(1),T('RRG相对趋势 X'):listing[T('RRG相对趋势 X')].round(3),T('RRG相对动量 Y'):listing[T('RRG相对动量 Y')].round(3)}))
 st.download_button(T('下载当前日期赛道排名 CSV'),frame.to_csv(index=False).encode('utf-8-sig'),file_name=f'HKERM_sector_{selected}_{horizon}D.csv',mime='text/csv')

with tabs[1]:
 st.markdown(T('### 相对强度 × 边际动量'))
 st.caption(T('四象限采用USERM一致的公开近似定义：RS＝赛道日收益连乘构造的相对价格÷HSCI；X＝100×exp(EMA14(ln RS)－EMA36(ln RS))；Y＝100×X÷5个交易日前的X。以100为中性线；不是StockCharts专有JdK指标。'))
 if len(frame):
  f=frame.dropna(subset=['rrg_x','rrg_y']).copy()
  if len(f):
   f['display_state']=display_states(f['state'])
   fig=px.scatter(f,x='rrg_x',y='rrg_y',size=num,color='display_state',hover_name='sector',
       hover_data=['industry',num,con],size_max=29,
       color_discrete_map={T('领先强化'):'#168c78',T('领先减弱'):'#d5a453',
                           T('落后改善'):'#3e79ae',T('落后持续'):'#d65c61'})
   fig.add_hline(y=100,line_color='#b8c8d5',line_width=1)
   fig.add_vline(x=100,line_color='#b8c8d5',line_width=1)
   fig.update_xaxes(title=T('RRG相对趋势 X'),tickformat='.2f')
   fig.update_yaxes(title=T('RRG相对动量 Y'),tickformat='.2f')
   st.plotly_chart(figstyle(fig,590),use_container_width=True)
  else:
   st.info(T('RRG需要至少36个交易日趋势数据及额外5日动量历史；选定日期暂不满足。'))
  st.markdown(T('### 历史轮动轨迹'))
  ids=frame.sector_id.tolist();labels=dict(zip(frame.sector_id,frame.sector))
  chosen=st.multiselect(T('选择赛道查看轨迹'),options=ids,default=ids[:4],format_func=lambda x:labels.get(x,x),max_selections=8)
  days=st.slider(T('轨迹长度（交易日）'),3,25,10)
  # A standalone history chart, with real arrowheads oriented from earlier to later days.
  trail_fig=go.Figure()
  palette=px.colors.qualitative.Safe
  count=0
  for idx,sid in enumerate(chosen):
   hist=rrg[(rrg.sector_id==sid)&(rrg.date<=asof)].sort_values('date').dropna(subset=['x','y']).tail(days+1)
   if len(hist)<2:continue
   x=hist['x'].to_numpy(dtype=float);y=hist['y'].to_numpy(dtype=float)
   color=palette[idx % len(palette)]
   dates_h=hist.date.dt.strftime('%Y-%m-%d').tolist()
   trail_fig.add_trace(go.Scatter(x=x,y=y,mode='lines+markers',
       line=dict(width=2.6,color=color),marker=dict(size=6,color=color),
       name=labels.get(sid,sid),customdata=dates_h,
       hovertemplate='%{customdata}<br>RRG X %{x:.3f}<br>RRG Y %{y:.3f}<extra>'+labels.get(sid,sid)+'</extra>'))
   # Arrowheads at selected segments, including the final segment. Avoid zero-length arrows.
   stride=max(1,(len(x)-1)//5)
   positions=sorted(set(list(range(stride,len(x),stride))+[len(x)-1]))
   for j in positions:
    if abs(x[j]-x[j-1])+abs(y[j]-y[j-1])<1e-12:continue
    trail_fig.add_annotation(x=float(x[j]),y=float(y[j]),ax=float(x[j-1]),ay=float(y[j-1]),
      xref='x',yref='y',axref='x',ayref='y',showarrow=True,
      arrowhead=3,arrowsize=1.1,arrowwidth=2,arrowcolor=color,opacity=.9)
   trail_fig.add_trace(go.Scatter(x=[x[0]],y=[y[0]],mode='markers',
       marker=dict(symbol='circle-open',size=13,color=color,line=dict(width=2,color=color)),
       showlegend=False,hovertemplate='起点 '+dates_h[0]+'<extra></extra>'))
   trail_fig.add_trace(go.Scatter(x=[x[-1]],y=[y[-1]],mode='markers+text',
       marker=dict(symbol='diamond',size=11,color=color),text=['终点'],textposition='top center',
       showlegend=False,hovertemplate='终点 '+dates_h[-1]+'<extra></extra>'))
   count+=1
  trail_fig.add_hline(y=100,line_color='#becbd8',line_width=1)
  trail_fig.add_vline(x=100,line_color='#becbd8',line_width=1)
  trail_fig.update_xaxes(title=T('RRG相对趋势 X'),tickformat='.2f')
  trail_fig.update_yaxes(title=T('RRG相对动量 Y'),tickformat='.2f')
  st.caption(T('箭头方向＝较早交易日 → 较晚交易日；空心圆为起点，菱形为终点。横轴为RRG相对趋势X，纵轴为5日RRG相对动量Y，均以100为中性线。'))
  if count:st.plotly_chart(figstyle(trail_fig,580),use_container_width=True,key='trails')
  else:st.info(T('所选赛道在此日期缺少足够的连续轨迹记录。'))
  st.markdown(T('#### 赛道成分股'))
  quick_sid=st.selectbox(T('查看地图赛道成分股'),ids,format_func=lambda x:labels.get(x,x),key='rotation_quick_sector')
  linked_stock_table(sector_constituents(quick_sid,asof,limit=25),'股票代码')
  st.caption(T('最多显示按市值排序前25只；完整名单可在「市场总览」的赛道速览查看。'))
 description()

with tabs[2]:
 options=frame.sector_id.tolist()
 if not options:st.warning(T('当前筛选条件下没有可分析的赛道。'))
 else:
  sid=st.selectbox(T('选择细分赛道'),options,format_func=lambda v:next((x for x in frame.loc[frame.sector_id==v,'sector']),v))
  focus=frame[frame.sector_id==sid].iloc[0]
  c1,c2,c3,c4=st.columns(4)
  c1.metric(T(f'{horizon}D加权收益'),pct(focus[ret]));c2.metric(T('相对HSCI超额'),pct(focus[ex]));c3.metric(T('上涨广度'),pct(focus[breadth]));c4.metric(T('最大股票市值权重'),pct(focus[con]))
  if horizon in (1,5,20,60):
   h=sectors[(sectors.sector_id==sid)&(sectors.date<=asof)].sort_values('date')
   fig=go.Figure()
   fig.add_trace(go.Scatter(x=h.date,y=h[ex],name=T('赛道超额收益'),line=dict(color=COLORS['blue'],width=3)))
   fig.add_hline(y=0,line_color='#c5ced8')
   fig.update_yaxes(tickformat='.1%',title=T('相对HSCI超额'))
  else:
   h=sector_horizon_history(prices,master,bench,sid,asof,horizon)
   fig=go.Figure()
   fig.add_trace(go.Scatter(x=h.date,y=h.excess,mode='lines',name=T('赛道超额收益'),line=dict(color=COLORS['blue'],width=3)))
   fig.add_hline(y=0,line_color='#c5ced8')
   fig.update_yaxes(tickformat='.1%',title=T('相对HSCI超额'))
  st.plotly_chart(figstyle(fig),use_container_width=True)
  focusstocks=master[master.sector_id==sid].merge(prices[prices.date==asof][['code','close','amount','cap','ret_1','ret_5','ret_20','ret_60']],on='code',how='left')
  focusstocks=focusstocks.merge(stock_custom,on='code',how='left').sort_values('cap',ascending=False)
  for h1 in [1,5,20,60]:focusstocks[f'{h1}D收益%']=(focusstocks[f'ret_{h1}']*100).round(2)
  focusstocks['市值代理_亿']=(focusstocks.cap/1e8).round(1)
  focusstocks[f'{horizon}D收益%']=(focusstocks.ret_custom*100).round(2)
  st.markdown(T('**赛道股票（按当日总市值代理排序）**'))
  linked_stock_table(focusstocks[list(dict.fromkeys(['code','name','close','市值代理_亿',f'{horizon}D收益%','1D收益%','5D收益%','20D收益%','60D收益%','mapping_source','mapping_review']))].rename(columns={'code':'股票','name':'名称','close':'收盘价','mapping_source':'分类来源','mapping_review':'核验状态'}),'股票')
  st.download_button(T('下载该赛道股票数据'),focusstocks.to_csv(index=False).encode('utf-8-sig'),file_name=f'HKERM_{sid}_{selected}.csv',mime='text/csv')
  st.warning(T('该页采用研究用固定成分股分类；个别公司分类仍未按年报全部核验。龙头高度集中时，赛道走势可能主要代表单只股票。'))

with tabs[3]:
 st.markdown(T('### 个股筛选 · 研究日股票查询'))
 st.caption(T('用途：按照股票、行业、指数成员资格过滤581股，然后选中单只股票查看具体价格、收益和历史走势。所有筛选和图表随左侧研究日期变化。'))
 daily=master.merge(prices[prices.date==asof],on='code',how='left').merge(stock_custom,on='code',how='left')
 c1,c2,c3=st.columns([2,1,1])
 with c1:q=st.text_input(T('输入股票代码、公司名称或赛道'),placeholder=T('例如：0700、腾讯、半导体'),key='stock_search')
 with c2:index_filter=st.selectbox(T('指数成员筛选'),[T('全部'),'HSI','HSCEI','HSTECH'],key='stock_index')
 with c3:stock_industry=st.selectbox(T('股票所属行业'),[T('全部行业')]+sorted(tax.industry.dropna().unique()),index=([T('全部行业')]+sorted(tax.industry.dropna().unique())).index(industry_choice),key='stock_industry')
 if index_filter!=T('全部'):daily=daily[daily[index_filter]==1]
 if stock_industry!=T('全部行业'):daily=daily[daily.sector_id.isin(tax[tax.industry==stock_industry].sector_id)]
 if q:
  query=q.strip().lower()
  daily=daily[daily[['code','name','sector']].fillna('').astype(str).apply(lambda a:a.str.lower().str.contains(query,regex=False)).any(axis=1)]
 daily=daily.sort_values('cap',ascending=False,na_position='last')
 st.markdown((f'**Filtered: {len(daily)} stocks**' if EN else f'**当前筛选：{len(daily)} 只股票**'))
 if daily.empty:
  st.warning(T('没有符合条件的股票。请清除搜索词，或将指数/行业筛选改为「全部」。'))
 else:
  daily['总市值代理(亿)']=(daily.cap/1e8).round(1)
  daily[f'{horizon}D收益(%)']=(daily.ret_custom*100).round(2)
  for h1 in [1,5,20,60]:daily[f'{h1}D收益(%)']=(daily[f'ret_{h1}']*100).round(2)
  allcodes=daily.code.tolist()
  # Selectbox binds the selected code to the stock chart below.
  chosen_code=st.selectbox(T('选择股票 · 显示下方详情及历史走势'),allcodes,
                           format_func=lambda c:f"{c}  {daily.loc[daily.code==c,'name'].iloc[0]}  ·  {daily.loc[daily.code==c,'sector'].iloc[0]}",key='stock_detail_choice')
  linked_stock_table(daily[list(dict.fromkeys(['code','name','sector','HSI','HSCEI','HSTECH','总市值代理(亿)',f'{horizon}D收益(%)','1D收益(%)','5D收益(%)','20D收益(%)','60D收益(%)','mapping_review']))].rename(columns={'code':'代码','name':'名称','sector':'细分赛道','mapping_review':'分类核验'}),'代码')
  st.download_button(T('下载当前筛选股票 CSV'),daily.to_csv(index=False).encode('utf-8-sig'),file_name=f'HKERM_stocks_{selected}.csv',mime='text/csv')
  st.divider()
  tv=tradingview_url(chosen_code)
  if tv:st.link_button(T('在 TradingView 打开该股票 ↗'),tv,help=T('使用浏览器现有 TradingView 会话；账号登录由 TradingView 管理。'))
  stock_chart(chosen_code,asof)

with tabs[4]:
 st.markdown(T('### 数据说明与质量控制'))
 st.markdown("""**Coverage:** 581 HSCI fixed constituents as of 2026-10-09, with HSI / HSCEI / HSTECH membership flags. Available history depends on the bundled data.

**Unadjusted prices:** No verified corporate-action adjustments. Extreme raw price changes may be filtered.

**Look-ahead limitation:** Today's sector classification is applied to historical dates; this is a research tool, not an OOS model-tuning dataset.""" if EN else """**研究范围**：固定2026年10月9日HSCI成分股581只，叠加HSI / HSCEI / HSTECH标签。可用历史由打包数据决定。

**复权限制**：尚无核验过的公司行动复权数据，极端原始价格变动可能已被过滤。

**历史前视**：以当前赛道分类回看历史；仅供研究，不用于OOS调参。""")
 st.markdown(T('#### 核心公式'))
 st.markdown(('**Research dates:** Pick any calendar date in the bundled range; non-trading days resolve to the preceding trading day. The first 36+5 sessions do not have sufficient history to show the RRG coordinates.' if EN else '**研究日历**：可选择打包行情起止区间内的任意日历日；非交易日取此前最近一个交易日。数据前36+5个交易日不足以形成有效RRG坐标，保持空值。'))
 st.latex(r'RS_t = I_{sector,t}/I_{HSCI,t}')
 st.latex(r'X_t = 100\exp(EMA_{14}(\ln RS)_t-EMA_{36}(\ln RS)_t)')
 st.latex(r'Y_t = 100\, X_t/X_{t-5}')
 st.markdown(('X and Y are USERM-compatible public EMA approximations of RRG-style positioning, **not** the proprietary JdK indicators. The sector proxy index chains the original daily cap-weighted sector returns. The selected 1–60-session performance window does not alter the RRG formula.' if EN else 'X、Y采用与USERM一致的对数EMA近似坐标，**不是**StockCharts专有JdK公式。赛道研究价格由原有日度市值加权收益逐日连乘得到。1–60日观察周期只影响收益表及排名，不改变RRG坐标。'))

 st.latex(r'R_{i,t}^{(X)}=P_{i,t}/P_{i,t-X}-1')
 st.latex(r'w_{i,t-X}=\\frac{P_{i,t-X}\\times Shares_{i,t-X}}{\\sum_j P_{j,t-X}\\times Shares_{j,t-X}}'.replace('\\\\','\\'))
 st.latex(r'R_{sector,t}^{(X)}=\\sum_i w_{i,t-X}R_{i,t}^{(X)}'.replace('\\\\','\\'))
 st.latex(r'Excess_{sector,t}^{(X)}=R_{sector,t}^{(X)}-R_{HSCI,t}^{(X)}')
 st.markdown("""**RRG momentum:** 100 times today's RRG X divided by its value five sessions earlier. The center line is 100.

**Positive breadth:** Share of valid stocks with positive X-day price return.

**Largest stock weight:** Highest starting-window market-cap-proxy weight in the sector.

**No inferred flows:** Volume is not equated with net capital inflow; Southbound flows and earnings catalysts are not independently verified.""" if EN else """**RRG相对动量**：当日RRG横轴X ÷ 五个交易日前的X ×100；100为中性线。

**上涨广度**：当前X日收益大于0的有效股票数 / 有效股票总数。

**最大市值权重**：当前赛道最大一只股票在窗口期初的总市值代理权重。

**研究页面不显示南向净流入或基本面催化**：当前材料不足以核实这些字段。不会将成交量解释为实际资金流入。""")
 st.markdown(('**Flexible lookback:** 1/5/20/60-session returns reuse the bundled original calculated columns. Other 1–60-session returns are recalculated using observed raw closes and start-of-window capitalization weights, with >35% raw single-session jump filtering. Early dates without enough bundled history show missing returns instead of made-up values.' if EN else '**自选观察周期**：1、5、20、60交易日沿用原始预计算字段；其他1–60日周期使用打包股票原始收盘价和期初市值代理重新加权计算，并过滤窗口内日涨跌绝对值超过35%的异常跳变。最早日期若缺少窗口数据，收益显示为空，不补造历史。'))
 st.markdown(T('#### 数据来源'))
 st.write(T('上传的港股原始日行情 data.zip；2026年10月9日四个恒生指数成分股CSV；HKERM统一研究工作簿20260902（赛道及分类）'))
 st.markdown(T('#### 数据质量摘要'))
 qa1,qa2,qa3=st.columns(3)
 qa1.metric(T('母池股票数'),len(master));qa2.metric(T('现有细分赛道'),len(tax));qa3.metric(T('网页可选日期'),len(calendar))
 st.info(T('若后续重新生成数据，只需保持 data/ 中CSV结构一致并更新仓库；当前版本不连接iFinD、不调用量化模型、不修改本地训练数据。'))
