"""Offline execution of every Streamlit page with a UI double. Not a browser test."""
import sys,types,runpy,os
from pathlib import Path
base=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(base))

class FakeWidget:
    def __init__(self,name='fake'):
        self.name=name
        self.column_config=self
        self.sidebar=self
    def __enter__(self):return self
    def __exit__(self,*args):return False
    def __getattr__(self,name):return FakeWidget(name)
    def __call__(self,*args,**kwargs):
        n=self.name
        if n=='set_page_config':return None
        if n=='cache_data':return lambda f:f
        if n=='selectbox':
            opts=kwargs.get('options',args[1] if len(args)>1 else [])
            if opts and args and args[0]=='Language / 语言' and os.environ.get('FAKE_LANG')=='中文':
                return '中文'
            return opts[kwargs.get('index',0)] if len(opts) else None
        if n=='date_input':
            return __import__('datetime').date.fromisoformat(os.environ['FAKE_DATE']) if os.environ.get('FAKE_DATE') else kwargs['value']
        if n=='slider':
            if args and ('Lookback period' in args[0] or args[0]=='观察周期') and os.environ.get('FAKE_HORIZON'):
                return int(os.environ['FAKE_HORIZON'])
            return kwargs.get('value',args[3] if len(args)>3 else 1)
        if n=='columns':
            length=args[0] if args else kwargs.get('spec',1)
            if isinstance(length,int): return [FakeWidget('col') for _ in range(length)]
            return [FakeWidget('col') for _ in length]
        if n=='tabs': return [FakeWidget('tab') for _ in args[0]]
        if n=='multiselect':return kwargs.get('default',[])
        if n=='text_input':return ''
        if n=='stop':raise RuntimeError('Application called st.stop()')
        return None

fake=FakeWidget()
mod=types.ModuleType('streamlit')
for key in ['set_page_config','markdown','selectbox','caption','divider','cache_data','slider','date_input','columns','metric','info','warning','error','plotly_chart','tabs','multiselect','download_button','dataframe','link_button','text_input','title','latex','write','stop']:
 setattr(mod,key,FakeWidget(key))
mod.sidebar=fake
mod.column_config=fake
sys.modules['streamlit']=mod
runpy.run_path(str(base/'app.py'),run_name='__main__')
print('All five HKERM page branches executed with mocked Streamlit widgets.')
