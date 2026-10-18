"""Presentation-only Arabic/English localization; business values remain unchanged."""
from pathlib import Path
import ast
import copy
import functools
import inspect
import json
import re
import streamlit as _st
import streamlit.components.v1 as components
from streamlit.elements.lib.form_utils import current_form_id

TRANSLATIONS = json.loads(Path(__file__).with_name('translations.en.json').read_text(encoding='utf-8'))
_language_component = components.declare_component('wdi_language', path=str(Path(__file__).parent / 'static' / 'language'))

def language():
    return _st.session_state.get('_ui_language', 'ar')

class TranslatedText(str):
    """A rendered template whose inserted business values must not be translated."""

def translated(text):
    return TranslatedText(text)

def tr(text):
    """Translate application-owned text only. Never call on customer records."""
    if language() == 'ar' or not isinstance(text, str) or isinstance(text, TranslatedText):
        return text
    return TRANSLATIONS.get(text, text)

def refresh_translations():
    global TRANSLATIONS
    TRANSLATIONS = json.loads(Path(__file__).with_name('translations.en.json').read_text(encoding='utf-8'))

# Match message templates before translating so paths, keywords and inserted names
# are opaque. No translation ever runs over the captured user-supplied values.
_MESSAGE_TEMPLATES=[]
for _file in ('storage_manager.py','utils.py','insights.py'):
    _tree=ast.parse(Path(__file__).with_name(_file).read_text(encoding='utf-8-sig'))
    for _node in ast.walk(_tree):
        if isinstance(_node,ast.JoinedStr) and any(isinstance(v,ast.Constant) and re.search(r'[\u0600-\u06ff]',str(v.value)) for v in _node.values):
            _parts=[v.value if isinstance(v,ast.Constant) else None for v in _node.values]
            _regex=''.join(re.escape(v) if v is not None else '(.*?)' for v in _parts)
            _MESSAGE_TEMPLATES.append((re.compile('^'+_regex+'$',re.S),_parts))

def translate_message(text):
    if not isinstance(text,str) or language()=='ar' or isinstance(text,TranslatedText):
        return text
    for pattern,parts in _MESSAGE_TEMPLATES:
        match=pattern.fullmatch(text)
        if match:
            values=iter(match.groups())
            return translated(''.join(tr(part) if part is not None else next(values) for part in parts))
    return tr(text)

def language_switcher():
    refresh_translations()
    selected = _language_component(language=language(), default=None, key='wdi_language_preference')
    if selected in ('ar','en') and selected != language():
        _st.session_state['_ui_language'] = selected


def document_locale():
    lang = language()
    direction = 'rtl' if lang == 'ar' else 'ltr'
    # Streamlit retains the selected display label in buffered forms. Translate
    # only that text node, without committing or replacing any pending field value.
    enum_texts={key: TRANSLATIONS[key] for key in (
        'الكل','كل الشهور','عميل حالي','عميل محتمل','عميل مستهدف','عميل جديد','عميل سابق',
        'محتمل','مستهدف','جديد','سابق','غير مهتم','لم تتم المقابلة','غير مصنف',
        'يناير','فبراير','مارس','أبريل','مايو','يونيو','يوليو','أغسطس','سبتمبر','أكتوبر','نوفمبر','ديسمبر'
    )}
    enum_labels=['الحالة','تُصنَّف كـ','الشهر','حالة الوعد','فلتر الحالة']
    label_texts=enum_labels+[TRANSLATIONS.get(label,label) for label in enum_labels]
    # st.html is the framework-supported JavaScript surface (Streamlit >= 1.58).
    script_html=f'''<span id="wdi-document-locale" hidden></span><script>(()=>{{
    document.documentElement.lang={json.dumps(lang)};
    document.documentElement.dir={json.dumps(direction)};
    window.__wdiLocale=window.__wdiLocale||{{originals:new WeakMap()}};
    const localeState=window.__wdiLocale;
    localeState.lang={json.dumps(lang)};
    localeState.texts={json.dumps(enum_texts,ensure_ascii=False)};
    localeState.labels={json.dumps(label_texts,ensure_ascii=False)};
    if(!localeState.observer){{
        let queued=false;
        const update=()=>{{
            queued=false;
            document.querySelectorAll('[data-testid="stSelectbox"]').forEach(box=>{{
                const label=box.querySelector('[data-testid="stWidgetLabel"]');
                if(!label||!localeState.labels.includes(label.textContent.trim()))return;
                const select=box.querySelector('[data-baseweb="select"]');
                if(!select)return;
                const walker=document.createTreeWalker(select,NodeFilter.SHOW_TEXT);
                let node;
                while(node=walker.nextNode()){{
                    const value=node.textContent;
                    if(localeState.lang==='en'&&Object.hasOwn(localeState.texts,value)){{
                        localeState.originals.set(node,value);
                        node.textContent=localeState.texts[value];
                    }}else if(localeState.lang==='ar'){{
                        const original=localeState.originals.get(node);
                        if(original&&node.textContent===localeState.texts[original])node.textContent=original;
                        else{{
                            const pair=Object.entries(localeState.texts).find(pair=>pair[1]===node.textContent);
                            if(pair)node.textContent=pair[0];
                        }}
                    }}
                }}
            }});
        }};
        localeState.schedule=()=>{{if(!queued){{queued=true;requestAnimationFrame(update)}}}};
        localeState.observer=new MutationObserver(localeState.schedule);
        localeState.observer.observe(document.body,{{childList:true,subtree:true,characterData:true}});
    }}
    localeState.schedule();
    }})();</script>'''
    common_css='''<style>[data-testid="stElementContainer"]:has(#wdi-document-locale){display:none}
        .stApp,[data-testid=stAppViewContainer]{direction:ltr}
        iframe[title="localization.wdi_language"]{height:43px!important}
        [data-testid="stCustomComponentV1"]:has(iframe[title="localization.wdi_language"]){height:43px!important;min-height:43px!important}
        </style>'''
    english_css=''
    if lang == 'en':
        english_css='''<style>
        .stApp,[data-testid="stAppViewContainer"],.main .block-container,
        [data-testid="stMainBlockContainer"],[data-testid="stSidebar"],.wdi-table{direction:ltr!important}
        .wdi-table th{text-align:left!important}
        [style*="direction:rtl"]{direction:ltr!important}
        .wdi-table td{unicode-bidi:plaintext}
        input,textarea,[data-testid="stDataFrame"]{unicode-bidi:plaintext}
        @media(max-width:700px){.kpi-grid{grid-template-columns:repeat(auto-fit,minmax(min(100%,150px),1fr))!important}.page-head{flex-wrap:wrap}.wdi-tablewrap{max-width:100%}}
        </style>'''
    _st.html(script_html+common_css+english_css, unsafe_allow_javascript=True)


OWNED_VALUE_COLUMNS={'المؤشر','البند','نوع الوعد','حالة الوعد','سبب الأولوية','أولوية الزيارة',
                     'تصنيف المحرك','تصنيف الموظف','الحالة','الحالة الحالية','الحالة السابقة',
                     'النوع','اليوم','فئة العميل'}

def display_value(column,value):
    return translate_message(value) if column in OWNED_VALUE_COLUMNS and isinstance(value,str) else value

def display_frame(df):
    """Copy display headers and owned enums; preserve free-form records and the source schema."""
    if language() == 'ar' or not hasattr(df, 'rename'):
        return df
    result=df.copy()
    for col in result.columns:
        if col in OWNED_VALUE_COLUMNS:
            result[col]=result[col].map(lambda value: display_value(col,value))
    result=result.rename(columns=lambda c: tr(c) if isinstance(c,str) else c)
    if getattr(result.index,'name',None): result.index.name=tr(result.index.name)
    return result


def display_figure(figure):
    horizontal=any(getattr(trace,'orientation',None)=='h' for trace in figure.data)
    axes=any(trace.type in {'bar','scatter','heatmap'} for trace in figure.data)
    if language() == 'ar' and not axes:
        return figure
    fig = copy.deepcopy(figure)
    if axes:
        # Reserve space for readable labels in both writing directions; never alter data.
        fig.update_yaxes(automargin=True)
        fig.update_layout(margin=dict(l=max(170 if horizontal else 50,fig.layout.margin.l or 0),
                                      r=max(60,fig.layout.margin.r or 0)))
        fig.update_traces(cliponaxis=False,selector=dict(type="bar"))
    def layout_text(obj):
        if isinstance(obj, dict):
            return {k: (tr(v) if k in ('text','title','hovertemplate') and isinstance(v,str)
                        else layout_text(v)) for k,v in obj.items()}
        if isinstance(obj,list):
            return [layout_text(v) for v in obj]
        return obj
    spec=fig.to_plotly_json()
    spec['layout']=layout_text(spec.get('layout',{}))
    # Trace labels are UI only. Only known status/metric enums are translated;
    # free-form axes (customer names, governorates, notes) stay untouched.
    statuses={'السبت','الأحد','الاثنين','الثلاثاء','الأربعاء','الخميس','الجمعة','عميل حالي','محتمل','مستهدف','جديد','سابق','غير مهتم','لم تتم المقابلة','غير مصنف'}
    for trace in spec.get('data',[]):
        hover=trace.get('hovertemplate','') or ''
        owned_axis=any(marker in hover for marker in ('Status=','الحالة=','Day=','اليوم='))
        if isinstance(trace.get('name'),str) and trace['name'] in statuses and owned_axis:
            trace['name']=tr(trace['name'])
        if isinstance(trace.get('hovertemplate'),str):
            trace['hovertemplate']=re.sub(r'([^<>]+?)(?==%\{)',lambda m:tr(m.group()),trace['hovertemplate'])
        for field in ('labels','x','y'):
            values=trace.get(field)
            owned_labels=(field=='labels' and trace.get('type')=='pie') or owned_axis
            if owned_labels and values is not None and all(isinstance(v,str) and v in statuses for v in values):
                trace[field]=[tr(v) for v in values]
    import plotly.graph_objects as go
    return go.Figure(spec)


def option_label(key, value):
    """Translate compound option captions without changing their canonical values."""
    if language()=='ar' or not isinstance(value,str): return str(value)
    if key=='merge_grp':
        match=re.fullmatch(r'(.*) — (.*) \((\d+) اسم\)',value)
        if match:
            name,gov,count=match.groups()
            return f"{name} — {tr(gov) if gov=='بدون محافظة' else gov} ({count} names)"
    if key=='del_rules':
        name,arrow,tail=value.rpartition(' → ')
        status,paren,score=tail.rpartition(' (')
        if arrow and paren:return name+arrow+tr(status)+paren+score
    return value

class LocalizedStreamlit:
    """A local facade, never a process-wide monkeypatch (sessions can use different languages)."""
    _widgets={'button','download_button','checkbox','toggle','radio','selectbox','multiselect',
              'text_input','text_area','number_input','date_input','time_input','slider',
              'select_slider','file_uploader','data_editor','color_picker'}
    _text={'markdown','write','info','warning','error','success','caption','header','subheader',
           'title','text','spinner','expander','form_submit_button','metric'}
    def __init__(self, target=_st):
        self._target=target
    def __enter__(self):
        self._target.__enter__()
        return self
    def __exit__(self,*args):
        return self._target.__exit__(*args)
    def __getattr__(self,name):
        original=getattr(self._target,name)
        if name=='sidebar': return LocalizedStreamlit(original)
        if name=='columns':
            return lambda *a,**kw: [LocalizedStreamlit(col) for col in original(*a,**kw)]
        if name in ('container','empty','form'):
            return lambda *a,**kw: LocalizedStreamlit(original(*a,**kw))
        if name=='plotly_chart':
            return lambda fig,*a,**kw: original(display_figure(fig),*a,**kw)
        if name=='dataframe':
            return lambda df,*a,**kw: original(display_frame(df),*a,**kw)
        if name=='tabs':
            def tabs(labels,**kw):
                frame=inspect.currentframe().f_back
                kw.setdefault('key',f'wdi:tabs:{Path(frame.f_code.co_filename).name}:{frame.f_lineno}')
                return [LocalizedStreamlit(tab) for tab in original([tr(x) for x in labels],**kw)]
            return tabs
        if name not in self._widgets | self._text:
            return original
        @functools.wraps(original)
        def render(*args,**kwargs):
            args=list(args)
            if name=='expander' and 'key' not in kwargs:
                frame=inspect.currentframe().f_back
                kwargs['key']=f'wdi:expander:{Path(frame.f_code.co_filename).name}:{frame.f_lineno}'
            if name in self._widgets:
                # Explicit language-independent keys make widget identity stable.
                # Streamlit 1.58 retains keyed widget values when labels change.
                if 'key' not in kwargs:
                    frame=inspect.currentframe().f_back
                    kwargs['key']=f'wdi:{Path(frame.f_code.co_filename).name}:{frame.f_lineno}'
                if name in ('radio','selectbox','multiselect') and not current_form_id(_st._main if self._target is _st else self._target):
                    widget_key=kwargs['key']
                    locale_key='_wdi_widget_language:'+str(widget_key)
                    previous=_st.session_state.get(locale_key)
                    if previous is not None and previous!=language() and widget_key in _st.session_state:
                        value=_st.session_state[widget_key]
                        if value is None:
                            value=_st.session_state.get('_wdi_option_value:'+str(widget_key))
                        if value is not None: _st.session_state[widget_key]=value
                    _st.session_state[locale_key]=language()
                if name in ('radio','selectbox','multiselect','select_slider'):
                    formatter=kwargs.get('format_func',str)
                    if kwargs.get('key') in {'merge_grp','del_rules'}:
                        formatter=lambda value: option_label(kwargs['key'],value)
                    kwargs['format_func']=lambda v: (tr(formatter(v)) if formatter is not str or kwargs.get('key')=='ac_pstate' or v in {'الكل','كل الشهور','👤 موقف نهائي لكل عميل','📋 كل الزيارات','30 يوم','60 يوم','90 يوم','180 يوم'} or (name=='radio' and args and args[0]=='Navigation') else formatter(v))
            if args and isinstance(args[0],str):
                args[0]=translate_message(args[0]) if name in {'info','warning','error','success'} else tr(args[0])
            for key in ('label','help','placeholder','text','body'):
                if isinstance(kwargs.get(key),str): kwargs[key]=tr(kwargs[key])
            if name=='data_editor':
                # column_config labels do not rename the returned editing schema.
                data=args[0] if args else kwargs.get('data')
                config=dict(kwargs.get('column_config') or {})
                if hasattr(data,'columns'):
                    for col in data.columns:
                        if col not in config: config[col]=tr(str(col))
                        elif isinstance(config[col],dict):
                            config[col]=dict(config[col],label=tr(config[col].get('label',str(col))))
                kwargs['column_config']=config
            result=original(*args,**kwargs)
            if name in ('radio','selectbox','multiselect') and result is not None:
                _st.session_state['_wdi_option_value:'+str(kwargs['key'])]=result
            return LocalizedStreamlit(result) if name=="expander" else result
        return render

st=LocalizedStreamlit()

