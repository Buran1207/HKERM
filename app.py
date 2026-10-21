"""HKERM | Hong Kong Equity Rotation Monitor — read-only research dashboard."""
from pathlib import Path
import io
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

BASE=Path(__file__).resolve().parent
st.set_page_config(page_title='HKERM | Hong Kong Equity Rotation Monitor',page_icon='📈',layout='wide',initial_sidebar_state='expanded')
CSS='''<style>
.block-container{padding-top:1.3rem;padding-bottom:2rem;max-width:1540px}
[data-testid="stSidebar"]{background:#111e32}
[data-testid="stSidebar"] label,[data-testid="stSidebar"] .stCaption,[data-testid="stSidebar"] p{color:#eaf2ff!important}
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
dates=sorted(set(sectors.date.dt.strftime('%Y-%m-%d')) & set(bench.date.dt.strftime('%Y-%m-%d')))

with st.sidebar:
 st.markdown('### HKERM')
 st.caption('HONG KONG EQUITY ROTATION MONITOR')
 st.divider()
 selected=st.selectbox('研究日期 / As of',list(reversed(dates)),index=0)
 horizon=st.selectbox('观察周期',options=[5,1,20,60],format_func=lambda x:f'{x}个交易日',index=0)
 industry_choice=st.selectbox('研究行业',['全部行业']+sorted(tax.industry.dropna().unique().tolist()))
 min_n=st.slider('赛道最低有效股票数',1,10,3)
 st.divider()
 st.caption('数据止于 2026-09-02')
 st.caption('固定2026-10-09成分名单回看；非历史真实指数成分。')
 st.caption('研究试算 · 未复权价格 · 非交易信号')

asof=pd.Timestamp(selected)
frame=sectors[sectors.date==asof].copy()
if industry_choice!='全部行业':frame=frame[frame.industry==industry_choice]
ret=f'ret_{horizon}';ex=f'excess_{horizon}';num=f'n_{horizon}';breadth=f'breadth_{horizon}';con=f'concentration_{horizon}'
frame=frame[(frame[num]>=min_n)&frame[ex].notna()].copy().sort_values(ex,ascending=False)
bench_row=bench[bench.date==asof]
bm=bench_row[f'hsciret_{horizon}'].iloc[0] if not bench_row.empty else np.nan
prior_date=max([x for x in dates if x<selected],default=None)
prev=sectors[sectors.date==pd.Timestamp(prior_date)][['sector_id',ex]].rename(columns={ex:'ex_prev'}) if prior_date else pd.DataFrame(columns=['sector_id','ex_prev'])
frame=frame.merge(prev,on='sector_id',how='left')
frame['momentum']=frame[ex]-frame['ex_prev']
frame['rank']=np.arange(1,len(frame)+1)
frame['state']=np.select([(frame[ex]>=0)&(frame.momentum>=0),(frame[ex]>=0)&(frame.momentum<0),(frame[ex]<0)&(frame.momentum>=0)],['领先强化','领先减弱','落后改善'],default='落后持续')

def pct(x):return f'{x:+.2%}' if pd.notna(x) else '—'
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
    members['总市值代理(亿)']=(members.cap/1e8).round(1)
    members['成交额(百万)']=(members.amount/1e6).round(1)
    for h in (1,5,20,60):members[f'{h}D收益(%)']=(members[f'ret_{h}']*100).round(2)
    visible=members[['code','name','总市值代理(亿)','成交额(百万)','1D收益(%)','5D收益(%)','20D收益(%)','60D收益(%)','mapping_review']].rename(columns={'code':'股票代码','name':'公司名称','mapping_review':'分类核验'})
    return visible if limit is None else visible.head(limit)

def stock_chart(stock_code, asof):
    h=prices[(prices.code==stock_code)&(prices.date<=asof)].sort_values('date').copy()
    if h.empty:
        st.warning('所选日期无该股票行情。可以尝试选择另一只股票或其他研究日期。')
        return
    obj=master[master.code==stock_code].iloc[0]
    last=h.iloc[-1]
    a,b,c=st.columns(3)
    a.metric('当前可用收盘价',f"{last['close']:.3f}" if pd.notna(last['close']) else '—')
    b.metric('5日价格收益',pct(last['ret_5']))
    c.metric('总市值代理（亿）',f"{last['cap']/1e8:,.1f}" if pd.notna(last['cap']) else '—')
    fig=go.Figure(go.Scatter(x=h.date,y=h.close,mode='lines+markers',line=dict(color=COLORS['blue'],width=2.7),name='收盘价'))
    fig.update_layout(xaxis_title='交易日期',yaxis_title='未复权收盘价',title=f"{obj['name']} · {stock_code}｜历史价格（截至所选日）")
    st.plotly_chart(figstyle(fig,340),use_container_width=True)
    st.caption(f"细分赛道：{obj['sector']} ｜ 分类状态：{obj['mapping_review']}。走势图只覆盖网页内置的46个交易日，未复权；不代表完整历史。")

def description():
 st.caption('口径：赛道X日收益＝窗口期初总市值代理（收盘价×总股本）加权个股X日原始价格收益；赛道X日超额＝赛道X日收益－恒生综指同期收益。未复权，极端原始价格跳变窗口已过滤。')

st.markdown('<div class="kicker">HKERM  /  INSTITUTIONAL MARKET MONITOR</div>',unsafe_allow_html=True)
st.title('Hong Kong Equity Rotation Monitor')
st.caption(f'研究日期 {selected}　·　HSCI固定成分研究池 581只　·　当前有效赛道 {len(frame)} / {len(tax)}　·　数据频率：日度')
tabs=st.tabs(['市场总览','轮动地图','赛道深度','个股筛选','方法与数据质量'])

with tabs[0]:
 a,b,c,d=st.columns(4)
 a.metric(f'HSCI {horizon}D 原始价格收益',pct(bm))
 b.metric('跑赢HSCI的赛道',f'{int((frame[ex]>0).sum())} / {len(frame)}')
 c.metric('领先强化',int((frame.state=='领先强化').sum()))
 d.metric('有效股票数中位数',f'{frame[num].median():.0f}' if len(frame) else '—')
 st.markdown('### 相对强弱排行榜')
 left,right=st.columns([1.35,1])
 with left:
  top=pd.concat([frame.head(12),frame.tail(8)]).drop_duplicates('sector_id').sort_values(ex)
  fig=px.bar(top,x=ex,y='sector',orientation='h',color=ex,color_continuous_scale=['#d56667','#eff2f5','#178b7a'],color_continuous_midpoint=0,hover_data=['industry',num,'rank'])
  fig.update_coloraxes(showscale=False);fig.update_xaxes(tickformat='.0%');fig.update_layout(xaxis_title='相对HSCI超额收益',yaxis_title=None)
  st.plotly_chart(figstyle(fig,580),use_container_width=True)
 with right:
  st.markdown('**状态分布**')
  states=frame.state.value_counts().reset_index();states.columns=['state','count']
  fig=px.pie(states,names='state',values='count',hole=.69,color='state',color_discrete_map={'领先强化':'#168c78','领先减弱':'#d4aa56','落后改善':'#497cae','落后持续':'#d65c61'})
  fig.update_traces(textposition='outside',textinfo='label+percent');st.plotly_chart(figstyle(fig,280),use_container_width=True)
  st.markdown('**研究提醒**')
  st.info('强势≠资金净流入。成交量、价格及南向持仓属于不同证据；当前数据尚未纳入南向资金或业绩催化。')
  if len(frame):
   top3='、'.join(frame.head(3).sector.tolist());weak='、'.join(frame.tail(3).sector.tolist())
   st.markdown(f'**领先赛道：**{top3}。\n\n**相对落后：**{weak}。')
 description()
 st.markdown('### 赛道成分股速览')
 st.caption('无需跳转页面：选择任意赛道，立即查看其中所有股票及市值排序。行业筛选与研究日期同步生效。')
 if len(frame):
  quick_ids=frame.sector_id.tolist()
  quick=st.selectbox('选择赛道 · 查看成分股',quick_ids,format_func=lambda x:next((r['sector'] for _,r in frame[frame.sector_id==x].iterrows()),x),key='overview_quick_sector')
  subset=sector_constituents(quick,asof)
  st.caption(f'赛道股票共 {len(subset)} 只；按所选日期的总市值代理降序排列，缺失市值置后。')
  view_table(subset)
 else:
  st.warning('当前日期与最低股票数条件下没有有效赛道，请调低左侧最低有效股票数。')
 st.markdown('### 全部赛道排名')
 listing=frame[['rank','industry','sector','state',num,ret,ex,breadth,con,'momentum']].copy()
 listing.columns=['排名','一级行业','细分赛道','状态','有效股数',f'{horizon}D赛道收益',f'{horizon}D超额vs HSCI','上涨广度','最大市值权重','超额日变化']
 st.dataframe(listing,use_container_width=True,hide_index=True,column_config={f'{horizon}D赛道收益':st.column_config.NumberColumn(format='%.2f%%'),f'{horizon}D超额vs HSCI':st.column_config.NumberColumn(format='%.2f%%')}) if False else view_table(listing.assign(**{f'{horizon}D赛道收益':(listing[f'{horizon}D赛道收益']*100).round(2),f'{horizon}D超额vs HSCI':(listing[f'{horizon}D超额vs HSCI']*100).round(2),'上涨广度':(listing['上涨广度']*100).round(1),'最大市值权重':(listing['最大市值权重']*100).round(1),'超额日变化':(listing['超额日变化']*100).round(2)}))
 st.download_button('下载当前日期赛道排名 CSV',frame.to_csv(index=False).encode('utf-8-sig'),file_name=f'HKERM_sector_{selected}_{horizon}D.csv',mime='text/csv')

with tabs[1]:
 st.markdown('### 相对强度 × 边际动量')
 st.caption('四象限借鉴RRG展示方式，但不是StockCharts专有的JdK RS-Ratio / RS-Momentum计算：横轴为X日相对HSCI超额收益，纵轴为该超额收益相较上一交易日的变化。')
 if len(frame):
  f=frame[frame.momentum.notna()].copy()
  fig=px.scatter(f,x=ex,y='momentum',size=num,color='state',hover_name='sector',hover_data=['industry',num,con],size_max=29,color_discrete_map={'领先强化':'#168c78','领先减弱':'#d5a453','落后改善':'#3e79ae','落后持续':'#d65c61'})
  fig.add_hline(y=0,line_color='#b8c8d5',line_width=1);fig.add_vline(x=0,line_color='#b8c8d5',line_width=1)
  fig.update_xaxes(title=f'{horizon}D相对收益',tickformat='.1%');fig.update_yaxes(title='超额收益日变化',tickformat='.1%')
  st.plotly_chart(figstyle(fig,590),use_container_width=True)
  st.markdown('### 历史轮动轨迹')
  ids=frame.sector_id.tolist();labels=dict(zip(frame.sector_id,frame.sector))
  chosen=st.multiselect('选择赛道查看轨迹',options=ids,default=ids[:4],format_func=lambda x:labels.get(x,x),max_selections=8)
  days=st.slider('轨迹长度（交易日）',3,25,10)
  for sid in chosen:
   hist=sectors[(sectors.sector_id==sid)&(sectors.date<=asof)].sort_values('date').tail(days).copy()
   hist['mom']=hist[ex].diff()
   hist=hist[hist.mom.notna()]
   if len(hist)<2:continue
   fig.add_trace(go.Scatter(x=hist[ex],y=hist.mom,mode='lines+markers',line=dict(width=2),marker=dict(size=6),name=labels.get(sid,sid),hovertext=hist.date.dt.strftime('%Y-%m-%d')))
  st.plotly_chart(figstyle(fig,580),use_container_width=True,key='trails')
  st.markdown('#### 地图上赛道包含哪些股票？')
  quick_sid=st.selectbox('查看地图赛道成分股',ids,format_func=lambda x:labels.get(x,x),key='rotation_quick_sector')
  view_table(sector_constituents(quick_sid,asof,limit=25))
  st.caption('最多显示按市值排序前25只；完整名单可在「市场总览」的赛道速览查看。')
 description()

with tabs[2]:
 options=frame.sector_id.tolist()
 if not options:st.warning('当前筛选条件下没有可分析的赛道。')
 else:
  sid=st.selectbox('选择细分赛道',options,format_func=lambda v:next((x for x in frame.loc[frame.sector_id==v,'sector']),v))
  focus=frame[frame.sector_id==sid].iloc[0]
  c1,c2,c3,c4=st.columns(4)
  c1.metric(f'{horizon}D加权收益',pct(focus[ret]));c2.metric('相对HSCI超额',pct(focus[ex]));c3.metric('上涨广度',pct(focus[breadth]));c4.metric('最大股票市值权重',pct(focus[con]))
  h=sectors[(sectors.sector_id==sid)&(sectors.date<=asof)].sort_values('date')
  fig=go.Figure()
  fig.add_trace(go.Scatter(x=h.date,y=h[ex],name='赛道超额收益',line=dict(color=COLORS['blue'],width=3)))
  fig.add_hline(y=0,line_color='#c5ced8');fig.update_yaxes(tickformat='.1%',title='相对HSCI超额')
  st.plotly_chart(figstyle(fig),use_container_width=True)
  focusstocks=master[master.sector_id==sid].merge(prices[prices.date==asof][['code','close','amount','cap','ret_1','ret_5','ret_20','ret_60']],on='code',how='left')
  focusstocks=focusstocks.sort_values('cap',ascending=False)
  for h1 in [1,5,20,60]:focusstocks[f'{h1}D收益%']=(focusstocks[f'ret_{h1}']*100).round(2)
  focusstocks['市值代理_亿']=(focusstocks.cap/1e8).round(1)
  st.markdown('**赛道股票（按当日总市值代理排序）**')
  view_table(focusstocks[['code','name','close','市值代理_亿','1D收益%','5D收益%','20D收益%','60D收益%','mapping_source','mapping_review']].rename(columns={'code':'股票','name':'名称','close':'收盘价','mapping_source':'分类来源','mapping_review':'核验状态'}))
  st.download_button('下载该赛道股票数据',focusstocks.to_csv(index=False).encode('utf-8-sig'),file_name=f'HKERM_{sid}_{selected}.csv',mime='text/csv')
  st.warning('该页采用研究用固定成分股分类；个别公司分类仍未按年报全部核验。龙头高度集中时，赛道走势可能主要代表单只股票。')

with tabs[3]:
 st.markdown('### 个股筛选 · 研究日股票查询')
 st.caption('用途：按照股票、行业、指数成员资格过滤581股，然后选中单只股票查看具体价格、收益和历史走势。所有筛选和图表随左侧研究日期变化。')
 daily=master.merge(prices[prices.date==asof],on='code',how='left')
 c1,c2,c3=st.columns([2,1,1])
 with c1:q=st.text_input('输入股票代码、公司名称或赛道',placeholder='例如：0700、腾讯、半导体',key='stock_search')
 with c2:index_filter=st.selectbox('指数成员筛选',['全部','HSI','HSCEI','HSTECH'],key='stock_index')
 with c3:stock_industry=st.selectbox('股票所属行业',['全部行业']+sorted(tax.industry.dropna().unique()),index=(['全部行业']+sorted(tax.industry.dropna().unique())).index(industry_choice),key='stock_industry')
 if index_filter!='全部':daily=daily[daily[index_filter]==1]
 if stock_industry!='全部行业':daily=daily[daily.sector_id.isin(tax[tax.industry==stock_industry].sector_id)]
 if q:
  query=q.strip().lower()
  daily=daily[daily[['code','name','sector']].fillna('').astype(str).apply(lambda a:a.str.lower().str.contains(query,regex=False)).any(axis=1)]
 daily=daily.sort_values('cap',ascending=False,na_position='last')
 st.markdown(f'**当前筛选：{len(daily)} 只股票**')
 if daily.empty:
  st.warning('没有符合条件的股票。请清除搜索词，或将指数/行业筛选改为「全部」。')
 else:
  daily['总市值代理(亿)']=(daily.cap/1e8).round(1)
  for h1 in [1,5,20,60]:daily[f'{h1}D收益(%)']=(daily[f'ret_{h1}']*100).round(2)
  allcodes=daily.code.tolist()
  # Selectbox binds the selected code to the stock chart below.
  chosen_code=st.selectbox('选择股票 · 显示下方详情及历史走势',allcodes,
                           format_func=lambda c:f"{c}  {daily.loc[daily.code==c,'name'].iloc[0]}  ·  {daily.loc[daily.code==c,'sector'].iloc[0]}",key='stock_detail_choice')
  view_table(daily[['code','name','sector','HSI','HSCEI','HSTECH','总市值代理(亿)','1D收益(%)','5D收益(%)','20D收益(%)','60D收益(%)','mapping_review']].rename(columns={'code':'代码','name':'名称','sector':'细分赛道','mapping_review':'分类核验'}))
  st.download_button('下载当前筛选股票 CSV',daily.to_csv(index=False).encode('utf-8-sig'),file_name=f'HKERM_stocks_{selected}.csv',mime='text/csv')
  st.divider()
  stock_chart(chosen_code,asof)

with tabs[4]:
 st.markdown('### 数据说明与质量控制')
 st.markdown('''**研究范围**：2026年10月9日HSCI固定成分股581只，叠加HSI / HSCEI / HSTECH标签；原始行情止于2026年9月2日。网站提供2026年6月30日至9月2日可用研究日切换（约46个交易日），但不同期限存在窗口不足的情况。\n\n**复权限制**：价格未经过可靠公司行动复权。模型过滤包含大于35%单日原始价格跳变的收益窗口，但这既可能过滤真实波动，也不能覆盖全部公司行动。\n\n**历史前视**：2026年10月的成分股与行业分类固定回看以前交易日，不构成时点真实股票池历史回测。此网站是研究查看工具，不用于独立样本外模型调参。''')
 st.markdown('#### 核心公式')
 st.latex(r'R_{i,t}^{(X)}=P_{i,t}/P_{i,t-X}-1')
 st.latex(r'w_{i,t-X}=\\frac{P_{i,t-X}\\times Shares_{i,t-X}}{\\sum_j P_{j,t-X}\\times Shares_{j,t-X}}'.replace('\\\\','\\'))
 st.latex(r'R_{sector,t}^{(X)}=\\sum_i w_{i,t-X}R_{i,t}^{(X)}'.replace('\\\\','\\'))
 st.latex(r'Excess_{sector,t}^{(X)}=R_{sector,t}^{(X)}-R_{HSCI,t}^{(X)}')
 st.markdown('''**日度轮动动量**：当日赛道X日超额收益减去前一交易日的赛道X日超额收益。\n\n**上涨广度**：当前X日收益大于0的有效股票数 / 有效股票总数。\n\n**最大市值权重**：当前赛道最大一只股票在窗口期初的总市值代理权重。\n\n**研究页面不显示南向净流入或基本面催化**：当前材料不足以核实这些字段。不会将成交量解释为实际资金流入。''')
 st.markdown('#### 数据来源')
 st.write('上传的港股原始日行情 data.zip；2026年10月9日四个恒生指数成分股CSV；HKERM统一研究工作簿20260902（赛道及分类）')
 st.markdown('#### 数据质量摘要')
 qa1,qa2,qa3=st.columns(3)
 qa1.metric('母池股票数',len(master));qa2.metric('现有细分赛道',len(tax));qa3.metric('网页可选日期',len(dates))
 st.info('若后续重新生成数据，只需保持 data/ 中CSV结构一致并更新仓库；当前版本不连接iFinD、不调用量化模型、不修改本地训练数据。')
