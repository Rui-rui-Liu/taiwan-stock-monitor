import streamlit as st
import finlab
from finlab import data
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 網頁寬螢幕設定
st.set_page_config(page_title="台股族群漲跌幅", layout="wide")

# ==========================================
# 【全域 UI 強制修正】：經典黑底風格 CSS 注入
# ==========================================
st.markdown("""
<style>
    /* 強制將整頁與主要容器改回黑底 */
    .stApp {
        background-color: #0E1117 !important;
        color: #FFFFFF !important;
    }
    h1, h2, h3, h4, h5, h6, p, span, label {
        color: #FFFFFF !important;
    }
    /* 極致緊縮大標題的上方間距 */
    h1 {
        padding-top: 0px !important;
        margin-top: -30px !important;
        padding-bottom: 0px !important;
        margin-bottom: 0px !important;
    }
    /* 讓 st.columns 渲染出的每一行區塊底部留白 */
    [data-testid="stHorizontalBlock"] {
        margin-bottom: 8px !important;
    }
    .element-container {
        margin-bottom: 0px !important;
    }
    /* 按鈕偽裝成純白大字 */
    div.stButton > button, 
    div.stButton > button p, 
    div.stButton > button span {
        background-color: transparent !important;
        color: #FFFFFF !important;
        border: none !important;
        padding: 0px !important;
        font-size: 24px !important;
        font-weight: bold !important;
        text-align: left !important;
        box-shadow: none !important;
        transition: color 0.1s ease;
    }
    /* 滑鼠移過去時變橘色 */
    div.stButton > button:hover,
    div.stButton > button:hover p,
    div.stButton > button:hover span {
        color: #FF8500 !important;
        background-color: transparent !important;
        border: none !important;
    }
    div.stButton > button:focus,
    div.stButton > button:focus p,
    div.stButton > button:focus span {
        background-color: transparent !important;
        color: #FFFFFF !important; 
        border: none !important;
        box-shadow: none !important;
    }
    /* 排序按鈕樣式 */
    [class*="st-key-sortbtn_"] div.stButton > button,
    [class*="st-key-sortbtn_"] div.stButton > button p,
    [class*="st-key-sortbtn_"] div.stButton > button span {
        font-size: 12px !important;
        line-height: 1.1 !important;
        font-weight: normal !important;
        text-align: left !important;
        white-space: pre-line !important;
        padding: 0px !important;
        margin: 0px !important;
        min-height: 0px !important;
        height: auto !important;
        color: #A0A5B5 !important;
    }
    [class*="st-key-sortbtn_"] div.stButton > button:hover,
    [class*="st-key-sortbtn_"] div.stButton > button:hover p,
    [class*="st-key-sortbtn_"] div.stButton > button:hover span {
        color: #FF8500 !important;
    }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 0. 記憶體快取 (支援本機與雲端 Secrets 部署)
# ==========================================
@st.cache_data
def load_data():
    api_token = st.secrets.get("finlab", {}).get("api_token", None)
    if api_token:
        finlab.login(api_token)
    else:
        finlab.login()
        
    close = data.get('etl:adj_close')
    volume = data.get('price:成交股數')  
    twii = data.get('benchmark_return:發行量加權股價報酬指數').iloc[:, 0]
    market_value = data.get('etl:market_value') 
    twii_amount = data.get('market_transaction_info:成交金額')['TAIEX'] 
    return close, volume, twii, market_value, twii_amount

close, volume, twii, market_value, twii_amount = load_data()

# ==========================================
# 1. 側邊欄設定
# ==========================================
st.sidebar.header("看盤與監控設定")
view_mode = st.sidebar.radio("版面模式", ["💻 桌機/平板橫向大表", "📱 手機極致卡片"], index=0)
st.sidebar.markdown("---")
sigma_5 = st.sidebar.slider("近週 σ 倍數", min_value=0.0, max_value=3.0, value=1.0, step=0.1)
sigma_20 = st.sidebar.slider("近月 σ 倍數", min_value=0.0, max_value=3.0, value=1.0, step=0.1)
sigma_60 = st.sidebar.slider("近季 σ 倍數", min_value=0.0, max_value=3.0, value=1.0, step=0.1)

# ==========================================
# 族群結構名單
# ==========================================
groups = {
    'FOPLP': {'3711': '日月光投控', '6239': '力成', '3481': '群創', '3663': '鑫科', '3580': '友威科'},
    '封裝': {'3711': '日月光投控', '6239': '力成', '2441': '超豐', '8150': '南茂'},
    '測試': {'2449': '京元電', '6257': '矽格', '3264': '欣銓', '3374': '精材'},
    '高階PCB板': {'2368': '金像電', '3044': '健鼎', '2313': '華通', '5439': '高技', '3715': '定穎投控', '6191': '精成科'},
    '晶圓代工': {'2330': '台積電', '2303': '聯電', '5347': '世界', '6770': '力積電'},
    'ASIC': {'2454': '聯發科', '3443': '創意', '3661': '世芯-KY', '3035': '智原'},
    '伺服器電力設備': {'2308': '台達電', '2301': '光寶科', '1504': '東元', '6282': '康舒', '6412': '群電'},
    '伺服器ODM/OEM': {'2317': '鴻海', '2382': '廣達', '6669': '緯穎', '3231': '緯創', '2356': '英業達', '2376': '技嘉', '2357': '華碩', '4938': '和碩', '2324': '仁寶'},
    'CCL/銅箔': {'2383': '台光電', '6274': '台燿', '6213': '聯茂', '1303': '南亞', '8358': '金居'},
    '被動元件': {'2327': '國巨', '2492': '華新科', '3026': '禾伸堂', '2472': '立隆電', '6173': '信昌電'},
    '被動元件-通路商': {'3090': '日電貿', '8043': '蜜望實'},
    '金控': {'2881': '富邦金', '2891': '中信金', '2882': '國泰金', '2885': '元大金', '2887': '台新新光金', '2886': '兆豐金', '2890': '永豐金', '2884': '玉山金', '2883': '凱基金', '2880': '華南金', '2892': '第一金', '5880': '合庫金'},
    '銀行': {'2801': '彰銀', '5876': '上海商銀', '2834': '臺企銀', '2812': '台中銀', '2838': '聯邦銀', '2845': '遠東銀'},
    '玻璃纖維布': {'1303': '南亞', '1802': '台玻', '1815': '富喬', '5475': '德宏', '5340': '建榮'},
    '塑化': {'1303': '南亞', '6505': '台塑化', '1326': '台化', '1301': '台塑', '1314': '中石化'},
    'ABF載板': {'3037': '欣興', '8046': '南電', '3189': '景碩', '4958': '臻鼎-KY'},
    '資料中心交換器': {'2345': '智邦', '6285': '啓碁', '3380': '明泰'},
    'DRAM/NOR flash': {'2408': '南亞科', '2344': '華邦電', '2337': '旺宏'},
    '電信': {'2412': '中華電', '3045': '台灣大', '4904': '遠傳'},
    '伺服器散熱': {'3017': '奇鋐', '3653': '健策', '6805': '富世達', '3324': '雙鴻', '8996': '高力'},
    '散熱-多元/傳統應用': {'2308': '台達電', '2354': '鴻準', '2486': '一詮', '6831': '邁科'},
    '伺服器滑軌': {'2059': '川湖', '6584': '南俊國際', '6805': '富世達'},
    '探針卡/植針機': {'6223': '旺矽', '6515': '穎崴', '6510': '精測', '6683': '雍智科技', '6217': '中探針', '7828': '創新服務'},
    '新藥研發': {'6446': '藥華藥', '6919': '康霈', '1795': '美時', '4743': '合一', '4147': '中裕', '6535': '順藥'},
    '面板': {'3481': '群創', '2409': '友達', '6116': '彩晶'},
    '記憶體IC/IP': {'8299': '群聯', '3006': '晶豪科', '6485': '點序', '5351': '鈺創', '6531': '愛普', '3529': '力旺'},
    '矽智財': {'6643': 'M31', '6533': '晶心科'},
    '傳統NB代工/品牌/週邊': {'3706': '神達', '2353': '宏碁', '2377': '微星', '2385': '群光'},
    '工業電腦': {'2395': '研華', '3005': '神基', '6414': '樺漢', '6166': '凌華'},
    '食品原物料/加工/品牌': {'1210': '大成', '1215': '卜蜂', '1229': '聯華', '1216': '統一', '1201': '味全'},
    '餐飲通路': {'2912': '統一超', '5903': '全家', '2727': '王品', '2729': '瓦城', '2753': '八方雲集', '2723': '美食-KY'},
    '貨櫃航運': {'2603': '長榮', '2615': '萬海', '2609': '陽明', '2636': '台驊投控'},
    'IC設計': {'2379': '瑞昱', '2454': '聯發科', '3034': '聯詠', '4966': '譜瑞-KY', '5269': '祥碩', '2458': '義隆'},
    '高速銅纜/連接器': {'3665': '貿聯-KY', '6715': '嘉基', '3023': '信邦', '6290': '良維', '3533': '嘉澤'},
    '鋼鐵': {'2002': '中鋼', '2015': '豐興', '2006': '東和鋼鐵', '2027': '大成鋼', '1605': '華新'},
    '傳動/控制元件': {'1590': '亞德客-KY', '2049': '上銀', '4540': '全球傳動', '1597': '直得', '4576': '大銀微系統'},
    'IC通路': {'3036': '文曄', '3702': '大聯大', '
