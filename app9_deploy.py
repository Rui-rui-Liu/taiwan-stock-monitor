import streamlit as st
import finlab
from finlab import data
import pandas as pd
import numpy as np
import plotly.graph_objects as go

# 網頁寬螢幕設定
st.set_page_config(page_title="台股族群漲跌幅", layout="wide")

# ==========================================
# 【全域 UI 與 CSS 注入】：乾淨黑底與狀態標籤增強
# ==========================================
st.markdown("""
<style>
    /* 強制整頁與主要容器為經典黑底 */
    .stApp {
        background-color: #0E1117 !important;
        color: #FFFFFF !important;
    }
    h1, h2, h3, h4, h5, h6, p, span, label {
        color: #FFFFFF !important;
    }
    h1 {
        padding-top: 0px !important;
        margin-top: -30px !important;
        padding-bottom: 0px !important;
        margin-bottom: 0px !important;
    }
    [data-testid="stHorizontalBlock"] {
        margin-bottom: 4px !important;
    }
    .element-container {
        margin-bottom: 0px !important;
    }
    /* 按鈕偽裝成純白大字 (桌機版使用) */
    div.stButton > button, 
    div.stButton > button p, 
    div.stButton > button span {
        background-color: transparent !important;
        color: #FFFFFF !important;
        border: none !important;
        padding: 0px !important;
        font-size: 20px !important;
        font-weight: bold !important;
        text-align: left !important;
        box-shadow: none !important;
        transition: color 0.1s ease;
    }
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

    /* 手機版族群標題按鈕專用樣式 */
    [class*="st-key-mob_btn_"] div.stButton > button,
    [class*="st-key-mob_btn_"] div.stButton > button p,
    [class*="st-key-mob_btn_"] div.stButton > button span {
        font-size: 18px !important;
        font-weight: bold !important;
        color: #FFFFFF !important;
        padding: 0px !important;
        margin: 0px !important;
        height: auto !important;
        min-height: 0px !important;
        border: none !important;
        background: transparent !important;
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
# 1. 側邊欄設定 (精簡選項名稱)
# ==========================================
st.sidebar.header("看盤設定")
view_mode = st.sidebar.radio("", ["📱 手機版", "💻 電腦版"], index=0)
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
    'IC通路': {'3036': '文曄', '3702': '大聯大', '2347': '聯強', '8112': '至上', '3028': '增你強'},
    '低軌衛星': {'2313': '華通', '3491': '昇達科', '6271': '同欣電', '3105': '穩懋', '6285': '啟碁', '2314': '台揚', '2367': '燿華'},
    '汽車銷售': {'2207': '和泰車', '2227': '裕日車', '2247': '汎德永業'},
    '半導體廠務': {'2404': '漢唐', '6139': '亞翔', '6691': '洋基工程', '5536': '聖暉', '6944': '兆聯實業', '6196': '帆宣', '7703': '銳澤', '3402': '漢科'},
    '電子紙': {'8069': '元大', '4961': '天鈺', '3141': '晶宏', '6143': '振曜'},
    '重電': {'1519': '華城', '1513': '中興電', '1503': '士電', '1514': '亞力', '2371': '大同'},
    '交通運輸': {'2618': '長榮航', '2610': '華航', '2646': '星宇航空', '6757': '台灣虎航', '2633': '台灣高鐵'},
    'PMIC': {'6415': '矽力-KY', '8081': '致新', '6719': '力智', '6138': '茂達'},
    '遊戲': {'3293': '鈊象', '3546': '宇峻', '3687': '歐買尬', '4946': '辣椒', '6180': '橘子'},
    '融資租賃': {'5871': '中租-KY', '9941': '裕融', '8393': '格上'},
    '水泥': {'1101': '台泥', '1102': '亞泥', '1103': '嘉泥', '1104': '環泥', '1108': '幸福', '1109': '信大'},
    '化合物半導體': {'3105': '穩懋', '8086': '宏捷科', '3707': '漢磊', '6488': '環球晶', '3016': '嘉晶', '2455': '全新'},
    '影像感測器': {'6789': '采鈺', '3227': '原相', '3530': '晶相光', '2478': '神盾', '6271': '同欣電', '3374': '精材'},
    '伺服器機殼': {'8210': '勤誠', '2474': '可成', '3013': '晟銘電', '5284': 'jpp-KY'},
    '矽電容': {'6531': '愛普', '2303': '聯電', '2344': '華邦電', '6770': '力積電'},
    '能源': {'8926': '台汽電', '3708': '上緯投控', '6869': '雲豹能源', '6873': '泓德能源'},
    '機器人概念股': {'2049': '上銀', '2359': '所羅門', '4583': '台灣精銳', '4585': '達明', '6215': '和椿', '7750': '新代'},
    '記憶體模組': {'5289': '宜鼎', '3260': '威剛', '2451': '創見', '4967': '十銓'},
    '紡織': {'1402': '遠東新', '1476': '儒鴻', '1477': '聚陽', '1409': '新纖', '1434': '福懋'},
    '製鞋': {'9904': '寶成', '9910': '豐泰', '6890': '來億-KY'},
    '燃料電池': {'8996': '高力', '6282': '康舒', '1513': '中興電', '2308': '台達電'},
    '貴金屬回收': {'7610': '聯友金屬', '1785': '光洋科', '3663': '鑫科', '8390': '金益鼎'},
    '輪胎': {'2105': '正新', '2101': '南港', '2102': '泰豐', '2106': '建大', '2109': '華豐'},
    '特化': {'4772': '台特化', '1717': '長興', '4749': '新應材', '1773': '勝一', '5234': '達興材料', '4722': '國精化', '1727': '中華化', '4768': '晶呈科技'},
    '房地產': {'2542': '興富發', '2597': '潤弘', '5522': '遠雄', '2540': '愛山林', '2923': '鼎固-KY', '2539': '櫻花建'},
    '導線架': {'6548': '長科', '2351': '順德', '5285': '界霖'},
    '石英晶體元件': {'3042': '晶技', '6174': '安碁', '2484': '希華', '8182': '加高', '8289': '泰藝', '3221': '台嘉碩'},
    '證券': {'2855': '統一證', '6005': '群益證', '6016': '康和證', '6015': '宏遠證', '6021': '美好證', '5864': '致和證', '6026': '福邦證', '6020': '大展證', '2889': '國票金'},
    'UPS/BBU': {'6409': '旭隼', '6781': 'AES-KY', '4931': '新盛力', '3211': '順達', '6121': '新普'},
    '功率元件-MOSFET': {'6435': '大中', '8261': '富鼎', '5299': '杰力', '3317': '尼克森', '2342': '茂矽'},
    '功率元件-整流/保護': {'8255': '朋程', '2481': '強茂', '3675': '德微', '5425': '台半', '6573': '虹揚-KY'},
    '電商/零售': {'8454': '富邦媒', '5904': '寶雅', '2915': '潤泰全'},
    '醫療科技/CDMO': {'7799': '禾榮科', '6949': '沛爾生醫', '6472': '保瑞'},
    'MCU': {'4919': '新唐', '6202': '盛群', '5471': '松翰', '4952': '凌通', '6907': '雅特力-KY'},
    '散裝航運': {'2637': '慧洋-KY', '2605': '新興', '2612': '中航', '5608': '四維航', '2606': '裕民'},
    '汽車': {'2258': '鴻華先進', '2206': '三陽工業', '2066': '世德', '6279': '胡連', '2250': 'IKKA-KY', '2402': '毅嘉'},
    '無人機': {'2645': '長榮航太', '2634': '漢翔', '8033': '雷虎', '5371': '中光電', '2630': '亞航'},
    '保險': {'2867': '三商壽', '2850': '新產', '2851': '中再保', '2852': '第一保', '2832': '台產'},
    'BMC': {'5274': '信驊', '4919': '新唐', '6231': '系微'},
    '矽晶圓': {'6488': '環球晶', '3532': '台勝科', '5483': '中美晶', '6182': '合晶', '3016': '嘉晶'},
    '光學鏡頭': {'3008': '大立光', '3406': '玉晶光', '3362': '先進光', '3441': '聯一光', '3019': '亞光'},
    '先進封裝核心設備': {'3131': '弘塑', '3583': '辛耘', '6187': '萬潤', '2467': '志盛', '6640': '均華', '7734': '印能科技', '5443': '均豪'},
    'PCB/IC載板設備與耗材': {'6664': '群翊', '7795': '長廣', '3167': '大量', '8021': '尖點'},
    '再生晶圓/晶圓薄化': {'3583': '辛耘', '8028': '昇陽半導體', '1560': '中砂'},
    '台積電先進製程耗材': {'1785': '光洋科', '5434': '崇越', '7556': '意德士', '3680': '家登'},
    '自動測試設備(ATE)': {'7769': '鴻勁', '2360': '致茂'},
    'AOI光學檢測設備': {'3535': '晶彩科', '3563': '牧德', '3455': '由田', '3030': '德律', '7822': '倍利科', '7853': '政美應用'},
    '光通訊-上游磊晶與雷射光源': {'3081': '聯亞', '2455': '全新', '4991': '環宇-KY', '3105': '穩懋', '6789': '采鈺', '4971': '英特磊-KY'},
    '光通訊-中下游模組、封裝與IC': {'6442': '光聖', '3450': '聯鈞', '3163': '波若威', '4979': '華星光', '6451': '訊芯-KY', '4977': '眾達-KY', '6526': '達發'},
    '光通訊-下游FA/FAU': {'3008': '大立光', '3406': '玉晶光', '3362': '先進光', '3363': '上詮'},
}

if 'expanded_group' not in st.session_state:
    st.session_state['expanded_group'] = None

st.session_state.setdefault('sort_period', None)
st.session_state.setdefault('sort_dir', None)

# ==========================================
# 2. 核心運算
# ==========================================
periods = [1, 5, 20, 60]
sigmas = {5: sigma_5, 20: sigma_20, 60: sigma_60}
returns_t = {p: (twii / twii.shift(p)) - 1 for p in periods}

twii_daily_returns = twii.pct_change(1, fill_method=None)
twii_daily_std = twii_daily_returns.rolling(60).std()

thresholds = {}
for p in [5, 20, 60]:
    market_period_std = twii_daily_std * np.sqrt(p)
    thresholds[p] = returns_t[p] + (sigmas[p] * market_period_std)

computed_rows = []
for g_name, ticker_dict in groups.items():
    row_entry = {"族群名稱": g_name}
    tickers = list(ticker_dict.keys())
    valid_tickers = [t for t in tickers if t in close.columns]
    
    if valid_tickers:
        raw_ret_1 = close[valid_tickers].pct_change(1, fill_method=None).mean(axis=1).iloc[-1]
        row_entry["報酬_1"] = f"{raw_ret_1*100:.2f}%"
        row_entry["raw_報酬_1"] = raw_ret_1
    else:
        row_entry["報酬_1"] = "0.00%"
        row_entry["raw_報酬_1"] = 0.0
        
    for p in [5, 20, 60]:
        if not valid_tickers: continue
        sub_c = close[valid_tickers].tail(p).ffill()
        g_ret = (sub_c.div(sub_c.iloc[0]) - 1).mean(axis=1).iloc[-1]
        row_entry[f"報酬_{p}"] = f"{g_ret*100:.2f}%"
        row_entry[f"raw_報酬_{p}"] = g_ret  
        
        aligned_thresh_up = thresholds[p].reindex(close.index).iloc[-1]
        aligned_twii_ret = returns_t[p].reindex(close.index).iloc[-1]
        aligned_thresh_down = aligned_twii_ret - (aligned_thresh_up - aligned_twii_ret)
        
        if g_ret > aligned_thresh_up: row_entry[f"狀態_{p}"] = "🔥 超額報酬"
        elif g_ret < aligned_thresh_down: row_entry[f"狀態_{p}"] = "❄️ 報酬落後"
        else: row_entry[f"狀態_{p}"] = "🟢 近似大盤"
            
    has_any_excess = (row_entry.get("狀態_5", "") == "🔥 超額報酬" or row_entry.get("狀態_20", "") == "🔥 超額報酬" or row_entry.get("狀態_60", "") == "🔥 超額報酬")
    row_entry["分類標記"] = 0 if has_any_excess else 1
    computed_rows.append(row_entry)

df_computed_raw = pd.DataFrame(computed_rows)

SORT_COL_MAP = {"1": "raw_報酬_1", "5": "raw_報酬_5", "20": "raw_報酬_20", "60": "raw_報酬_60"}

def get_sorted_df(df_raw):
    col = st.session_state.get("sort_period")
    direction = st.session_state.get("sort_dir")
    if col and direction:
        return df_raw.sort_values(by=SORT_COL_MAP[col], ascending=(direction == "asc")).reset_index(drop=True)
    return df_raw.sort_values(by=["分類標記", "raw_報酬_5"], ascending=[True, False]).reset_index(drop=True)

def cycle_sort(period):
    cur_col = st.session_state.get("sort_period")
    cur_dir = st.session_state.get("sort_dir")
    if cur_col != period:
        st.session_state["sort_period"] = period
        st.session_state["sort_dir"] = "desc"
    elif cur_dir == "desc":
        st.session_state["sort_dir"] = "asc"
    else:
        st.session_state["sort_period"] = None
        st.session_state["sort_dir"] = None

# ==========================================
# 3. UI 繪圖與標籤函數 (精準鮮豔色彩對比)
# ==========================================
def get_status_badge_mobile(status):
    if "🔥 超額報酬" in status:
        return '<span style="background-color:#3A1414; color:#FF3B30; border:1px solid #FF3B30; padding:2px 6px; border-radius:10px; font-weight:bold; font-size:11px; display:inline-block;">🔥 超額</span>'
    elif "❄️ 報酬落後" in status:
        return '<span style="background-color:#102A43; color:#007AFF; border:1px solid #007AFF; padding:2px 6px; border-radius:10px; font-weight:bold; font-size:11px; display:inline-block;">❄️ 落後</span>'
    elif "🟢 近似大盤" in status:
        return '<span style="background-color:#16331E; color:#34C759; border:1px solid #34C759; padding:2px 6px; border-radius:10px; font-weight:bold; font-size:11px; display:inline-block;">🟢 近似</span>'
    return ''

def get_status_html(status):
    if "🔥 超額報酬" in status:
        return '<div style="background-color:#FFD2D2; color:#D60000; padding:2px 8px; border-radius:12px; font-weight:bold; font-size:12px; display:inline-block; margin-top:-22px; margin-bottom:10px;">🔥 超額報酬</div>'
    elif "❄️ 報酬落後" in status:
        return '<div style="background-color:#E2F3FF; color:#0066CC; padding:2px 8px; border-radius:12px; font-weight:bold; font-size:12px; display:inline-block; margin-top:-22px; margin-bottom:10px;">❄️ 報酬落後</div>'
    elif "🟢 近似大盤" in status:
        return '<div style="background-color:#E8E8E8; color:#666666; padding:2px 8px; border-radius:12px; font-size:12px; display:inline-block; margin-top:-22px; margin-bottom:10px;">🟢 近似大盤</div>'
    return ''

def draw_spark_volume(g_name, tickers_list, key_suffix=""):
    valid_v = [t for t in tickers_list if t in volume.columns]
    if not valid_v: return
    
    g_vol_series = (volume[valid_v] / 1000).tail(20).ffill().sum(axis=1)
    date_labels = g_vol_series.index.strftime('%m-%d')
    hover_text = [f"{v:.0f}張" for v in g_vol_series]
    category_x = [f"D{i}" for i in range(1, 21)]
    
    fig = go.Figure(data=[go.Bar(
        x=category_x, 
        y=g_vol_series, 
        marker_color='#4A90E2', 
        opacity=0.85,
        customdata=np.stack((date_labels, hover_text), axis=-1), 
        hovertemplate="(%{customdata[0]}, %{customdata[1]})<extra></extra>", 
        textposition='none' 
    )])
    fig.update_layout(
        height=32, margin=dict(l=0, r=0, t=0, b=0),
        xaxis=dict(visible=False, type='category'), 
        yaxis=dict(visible=False),
        showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig, width='stretch', config={'displayModeBar': False}, key=f"vol_bar_{g_name}{key_suffix}")

def draw_market_volume_amt(key_suffix=""):
    m_amt_series = twii_amount.tail(20).ffill() / 10**8
    date_labels = m_amt_series.index.strftime('%m-%d')
    hover_text = [f"{v:.1f}億" for v in m_amt_series]
    category_x = [f"D{i}" for i in range(1, 21)]
    
    fig = go.Figure(data=[go.Bar(
        x=category_x, 
        y=m_amt_series, 
        marker_color='#FF8500', 
        opacity=0.85,
        customdata=np.stack((date_labels, hover_text), axis=-1),
        hovertemplate="(%{customdata[0]}, %{customdata[1]})<extra></extra>", 
        textposition='none' 
    )])
    fig.update_layout(
        height=38, margin=dict(l=0, r=0, t=2, b=2),
        xaxis=dict(visible=False, type='category'), 
        yaxis=dict(visible=False),
        showlegend=False, paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)'
    )
    st.plotly_chart(fig, width='stretch', config={'displayModeBar': False}, key=f"vol_bar_TAIEX_market{key_suffix}")

def draw_spark_stock_trends_svg(ticker_dict):
    tickers = list(ticker_dict.keys())
    valid_t = [t for t in tickers if t in close.columns]
    if not valid_t:
        st.info("暫無成分股資料")
        return
        
    latest_mv = market_value[valid_t].ffill().iloc[-1]
    valid_t = latest_mv.sort_values(ascending=False).index.tolist()
    
    stock_cols = st.columns(5)
    for idx, t in enumerate(valid_t):
        name = ticker_dict[t]
        col_target = stock_cols[idx % 5]
        with col_target:
            single_c = close[t].tail(20).ffill().values
            if len(single_c) < 2: continue
            single_cum = ((single_c / single_c[0]) - 1) * 100
            
            c_min, c_max = single_cum.min(), single_cum.max()
            c_range = (c_max - c_min) if (c_max - c_min) != 0 else 1
            
            points = []
            for i, val in enumerate(single_cum):
                x = (i / (len(single_cum) - 1)) * 160
                y = 35 - ((val - c_min) / c_range) * 30 
                points.append(f"{x},{y}")
            points_str = " ".join(points)
            
            line_color = '#FF4A4A' if single_cum[-1] >= 0 else '#2ECE5E'
            
            svg_html = f"""
            <div style="margin-bottom: 20px; padding: 5px;">
                <span style="font-size:13px; font-weight:bold; color:#A0A5B5;">📍 {t} {name}</span><br>
                <span style="font-size:12px; font-weight:bold; color:{line_color};">{single_cum[-1]:+.2f}%</span>
                <div style="margin-top: 4px;">
                    <svg width="100%" height="38" viewBox="0 0 160 40" style="background: transparent;">
                        <polyline fill="none" stroke="{line_color}" stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round" points="{points_str}" />
                    </svg>
                </div>
            </div>
            """
            st.markdown(svg_html, unsafe_allow_html=True)

# ==========================================
# 4. 主要主頁表格渲染
# ==========================================
st.title("台股族群漲跌幅")
st.markdown("<br>", unsafe_allow_html=True)

df_computed = get_sorted_df(df_computed_raw)

# ==========================================
# 📱 模式 1：手機版
# ==========================================
if "手機" in view_mode:
    taiex_ret_1 = returns_t[1].iloc[-1] * 100
    taiex_ret_5 = returns_t[5].iloc[-1] * 100
    taiex_ret_20 = returns_t[20].iloc[-1] * 100
    taiex_ret_60 = returns_t[60].iloc[-1] * 100

    # 加權指數卡片：採用 4 欄 CSS Grid 勻稱鋪開
    taiex_html = (
        '<div style="background:#161B22; border:1px solid #30363D; border-radius:12px; padding:14px; margin-bottom:15px;">'
        '<div style="font-size:18px; font-weight:bold; color:#FFFFFF; margin-bottom:12px;">加權指數報酬</div>'
        '<div style="display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:4px; text-align:center;">'
        f'<div><div style="font-size:11px; color:#8B949E; margin-bottom:2px;">近日</div><b style="color:#FFF; font-size:13px;">{taiex_ret_1:+.2f}%</b></div>'
        f'<div><div style="font-size:11px; color:#8B949E; margin-bottom:2px;">近週</div><b style="color:#FFF; font-size:13px;">{taiex_ret_5:+.2f}%</b></div>'
        f'<div><div style="font-size:11px; color:#8B949E; margin-bottom:2px;">近月</div><b style="color:#FFF; font-size:13px;">{taiex_ret_20:+.2f}%</b></div>'
        f'<div><div style="font-size:11px; color:#8B949E; margin-bottom:2px;">近季</div><b style="color:#FFF; font-size:13px;">{taiex_ret_60:+.2f}%</b></div>'
        '</div></div>'
    )
    st.markdown(taiex_html, unsafe_allow_html=True)

    if not df_computed.empty:
        for _, row in df_computed.iterrows():
            g_name = row['族群名稱']
            ret_1 = row['報酬_1']
            ret_5 = row['報酬_5']
            ret_20 = row['報酬_20']
            ret_60 = row['報酬_60']
            
            badge_5 = get_status_badge_mobile(row['狀態_5'])
            badge_20 = get_status_badge_mobile(row['狀態_20'])
            badge_60 = get_status_badge_mobile(row['狀態_60'])
            
            # 使用精準卡片包裹，確保族群標題按鈕、量能圖與報酬數據均穩定顯現
            st.markdown('<div style="background:#161B22; border:1px solid #30363D; border-radius:12px; padding:12px; margin-bottom:14px;">', unsafe_allow_html=True)
            
            c_title, c_vol = st.columns([1.5, 2.5])
            with c_title:
                st.markdown(f"<div class='st-key-mob_btn_{g_name}'>", unsafe_allow_html=True)
                if st.button(f"✦ {g_name}", key=f"mob_btn_{g_name}"):
                    if st.session_state['expanded_group'] == g_name:
                        st.session_state['expanded_group'] = None
                    else:
                        st.session_state['expanded_group'] = g_name
                st.markdown("</div>", unsafe_allow_html=True)
            with c_vol:
                draw_spark_volume(g_name, list(groups[g_name].keys()), key_suffix="_mob")
                
            card_grid_html = (
                '<div style="display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:4px; text-align:center; margin-top:8px;">'
                '<div style="background:#0D1117; padding:6px 2px; border-radius:8px;">'
                '<div style="font-size:11px; color:#8B949E;">近日</div>'
                f'<div style="font-size:13px; font-weight:bold; color:#FFF; margin:4px 0;">{ret_1}</div>'
                '</div>'
                '<div style="background:#0D1117; padding:6px 2px; border-radius:8px;">'
                '<div style="font-size:11px; color:#8B949E;">近週</div>'
                f'<div style="font-size:13px; font-weight:bold; color:#FFF; margin:4px 0;">{ret_5}</div>'
                f'{badge_5}'
                '</div>'
                '<div style="background:#0D1117; padding:6px 2px; border-radius:8px;">'
                '<div style="font-size:11px; color:#8B949E;">近月</div>'
                f'<div style="font-size:13px; font-weight:bold; color:#FFF; margin:4px 0;">{ret_20}</div>'
                f'{badge_20}'
                '</div>'
                '<div style="background:#0D1117; padding:6px 2px; border-radius:8px;">'
                '<div style="font-size:11px; color:#8B949E;">近季</div>'
                f'<div style="font-size:13px; font-weight:bold; color:#FFF; margin:4px 0;">{ret_60}</div>'
                f'{badge_60}'
                '</div>'
                '</div>'
            )
            st.markdown(card_grid_html, unsafe_allow_html=True)
            
            # 點擊族群標題後，僅展開成分股走勢圖
            if st.session_state['expanded_group'] == g_name:
                st.markdown("<hr style='margin:10px 0; border-top:1px dashed #30363D;'>", unsafe_allow_html=True)
                draw_spark_stock_trends_svg(groups[g_name])
                
            st.markdown('</div>', unsafe_allow_html=True)

# ==========================================
# 💻 模式 2：電腦版
# ==========================================
else:
    def render_sort_header(col, label, period):
        with col:
            c_label, c_btn = st.columns([3, 1], gap="small")
            with c_label:
                st.markdown(f"<span style='font-size: 1.5rem; white-space: nowrap;'>{label}</span>", unsafe_allow_html=True)
            with c_btn:
                active = st.session_state.get("sort_period") == period
                cur_dir = st.session_state.get("sort_dir")
                symbol = "△\n▼" if (active and cur_dir == "desc") else ("▲\n▽" if (active and cur_dir == "asc") else "△\n▽")
                if st.button(symbol, key=f"sortbtn_{period}"):
                    cycle_sort(period)
                    st.rerun()

    col_h_space, col_h_name, col_h_d, col_h_w, col_h_m, col_h_q, col_h_v = st.columns([0.01, 1.75, 1.2, 1.2, 1.2, 1.2, 1.4])
    with col_h_space: st.write("")
    with col_h_name: st.markdown("<span style='font-size: 1.5rem;'>族群名稱</span>", unsafe_allow_html=True)
    render_sort_header(col_h_d, "近日報酬", "1")
    render_sort_header(col_h_w, "近週報酬", "5")
    render_sort_header(col_h_m, "近月報酬", "20")
    render_sort_header(col_h_q, "近季報酬", "60")
    with col_h_v: st.markdown("<span style='font-size: 1.5rem;'>近月量能/走勢</span>", unsafe_allow_html=True)
    st.markdown("<hr style='margin: 5px 0 15px 0; border-top: 2px solid #ccc;'>", unsafe_allow_html=True)

    with st.container(height=550):
        col_n, col_d, col_w, col_m, col_q, col_v = st.columns([1.8, 1.2, 1.2, 1.2, 1.2, 1.4])
        with col_n: st.markdown("<h3 style='margin-left: 5px; font-weight: bold; font-size: 27px;'>加權指數</h3>", unsafe_allow_html=True)
        with col_d: st.metric(label="1D", label_visibility="collapsed", value=f"{returns_t[1].iloc[-1]*100:.2f}%")
        with col_w: st.metric(label="5D", label_visibility="collapsed", value=f"{returns_t[5].iloc[-1]*100:.2f}%")
        with col_m: st.metric(label="20D", label_visibility="collapsed", value=f"{returns_t[20].iloc[-1]*100:.2f}%")
        with col_q: st.metric(label="60D", label_visibility="collapsed", value=f"{returns_t[60].iloc[-1]*100:.2f}%")
        with col_v: 
            draw_market_volume_amt(key_suffix="_desk")
            
        st.markdown("<hr style='margin: 15px 0; border-top: 2px solid #555;'>", unsafe_allow_html=True)

        if not df_computed.empty:
            for _, row in df_computed.iterrows():
                g_name = row['族群名稱']
                col_n, col_d, col_w, col_m, col_q, col_v = st.columns([1.8, 1.2, 1.2, 1.2, 1.2, 1.4])
                
                with col_n:
                    if st.button(g_name, key=f"desk_btn_{g_name}"):
                        if st.session_state['expanded_group'] == g_name:
                            st.session_state['expanded_group'] = None
                        else:
                            st.session_state['expanded_group'] = g_name
                        
                with col_d: st.metric(label="1D", label_visibility="collapsed", value=row['報酬_1'])
                with col_w:
                    st.metric(label="5D", label_visibility="collapsed", value=row['報酬_5'])
                    st.markdown(get_status_html(row['狀態_5']), unsafe_allow_html=True)
                with col_m:
                    st.metric(label="20D", label_visibility="collapsed", value=row['報酬_20'])
                    st.markdown(get_status_html(row['狀態_20']), unsafe_allow_html=True)
                with col_q:
                    st.metric(label="60D", label_visibility="collapsed", value=row['報酬_60'])
                    st.markdown(get_status_html(row['狀態_60']), unsafe_allow_html=True)
                with col_v:
                    draw_spark_volume(g_name, list(groups[g_name].keys()), key_suffix="_desk")
                    
                if st.session_state['expanded_group'] == g_name:
                    st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
                    draw_spark_stock_trends_svg(groups[g_name])
                    
                st.markdown("<hr style='margin: 12px 0 15px 0; border-top: 1px solid #333;'>", unsafe_allow_html=True)

# ==========================================
# 5. 下半部網頁呈現：大盤歷史對照圖
# ==========================================
st.markdown("<br>", unsafe_allow_html=True)
st.subheader("族群報酬 vs. 加權報酬指數")

col_sel, col_time = st.columns([2, 1])
with col_sel:
    chosen_g_name = st.selectbox("選擇對照族群", list(groups.keys()), index=0)
with col_time:
    chart_window = st.selectbox("圖表歷史區間", ["週", "月", "季", "半年", "一年", "三年"], index=4)

window_map = {"週": 5, "月": 20, "季": 60, "半年": 120, "一年": 252, "三年": 756}
w_days = window_map[chart_window]

g_tickers = list(groups[chosen_g_name].keys())
valid_plot_tickers = [t for t in g_tickers if t in close.columns]

if valid_plot_tickers:
    sub_close = close[valid_plot_tickers].tail(w_days).ffill()
    sub_twii = twii.tail(w_days)
    
    group_each_cum = sub_close.div(sub_close.iloc[0]) - 1
    twii_cum_return = (sub_twii / sub_twii.iloc[0]) - 1
    group_cum_return = group_each_cum.mean(axis=1)

    fig = go.Figure()
    fig.add_trace(go.Scatter(x=twii_cum_return.index, y=twii_cum_return * 100, name='加權指數累積報酬 (%)', line=dict(color='#888888', width=2)))
    fig.add_trace(go.Scatter(x=group_cum_return.index, y=group_cum_return * 100, name=f'{chosen_g_name} 族群累積報酬 (%)', line=dict(color='#FF8500', width=3)))
    
    fig.update_layout(
        xaxis_title="日期", yaxis_title="累積報酬率 (%)", hovermode="x unified",
        paper_bgcolor='#0E1117', plot_bgcolor='#0E1117',
        margin=dict(l=20, r=20, t=20, b=20), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    fig.update_xaxes(showgrid=True, gridcolor='#22252D')
    fig.update_yaxes(showgrid=True, gridcolor='#22252D')
    st.plotly_chart(fig, width='stretch')
