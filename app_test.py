import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import re
import FinanceDataReader as fdr
import json
import threading
import concurrent.futures

# ==========================================
# 🔒 보안 설정
# ==========================================
SECRET_PASSCODE = "SM2026"

# ==========================================
# 1. 앱 기본 설정
# ==========================================
st.set_page_config(page_title="My Asset Hub (v1.44)", layout="wide", initial_sidebar_state="expanded")

# ==========================================
# 2. 입장 및 인증 시스템 (상태 관리)
# ==========================================
query_params = st.query_params
if 'api_url' not in st.session_state: st.session_state.api_url = query_params.get("api_url", "")
if 'passcode' not in st.session_state: st.session_state.passcode = query_params.get("passcode", "")
if 'authenticated' not in st.session_state: st.session_state.authenticated = False
if 'show_guide' not in st.session_state: st.session_state.show_guide = False

def login():
    if st.session_state.temp_passcode == SECRET_PASSCODE and st.session_state.temp_api_url.startswith("https://script.google.com/"):
        st.session_state.passcode = st.session_state.temp_passcode
        st.session_state.api_url = st.session_state.temp_api_url
        st.session_state.authenticated = True
        st.query_params["passcode"] = st.session_state.passcode
        st.query_params["api_url"] = st.session_state.api_url
    else:
        st.error("❌ Private password가 틀렸거나, URL ID 형식이 올바르지 않습니다.")

def toggle_guide(): st.session_state.show_guide = not st.session_state.show_guide

if st.session_state.passcode == SECRET_PASSCODE and st.session_state.api_url.startswith("https://script.google.com/"):
    st.session_state.authenticated = True

# ------------------------------------------
# 🛑 미인증 사용자 화면 (다크 테마 라운지)
# ------------------------------------------
if not st.session_state.authenticated:
    st.markdown("""
    <style>
    [data-testid="stSidebar"] { display: none !important; }
    [data-testid="stHeader"] { display: none !important; }
    .stApp { background-color: #0B0E14; background-image: radial-gradient(circle at 50% 0%, #1a1c2e 0%, #0B0E14 70%); color: #FFFFFF; }
    .block-container { padding-top: 10vh !important; max-width: 500px !important; }
    .stTextInput>div>div>input { background-color: #1A1C23 !important; color: white !important; border: 1px solid #2D3748 !important; border-radius: 8px !important; padding: 12px !important; }
    .stButton>button[kind="primary"] { background: linear-gradient(90deg, #7c3aed 0%, #4f46e5 100%) !important; color: white !important; border: none !important; border-radius: 8px !important; padding: 10px !important; font-weight: bold !important; }
    .stButton>button[kind="secondary"] { background-color: #1A1C23 !important; color: #A0AEC0 !important; border: 1px solid #2D3748 !important; border-radius: 8px !important; }
    .stButton>button[kind="secondary"]:hover { color: #FFFFFF !important; border-color: #4f46e5 !important; }
    .guide-card { background-color: #161b22; border: 1px solid #30363d; border-radius: 10px; padding: 20px; margin-bottom: 20px; color: #c9d1d9; font-size: 0.95em; line-height: 1.6; }
    .terminal-box { background-color: #010409; border: 1px solid #30363d; border-radius: 10px; padding: 15px; margin-bottom: 20px; box-shadow: 0 8px 16px rgba(0,0,0,0.5); overflow-x: auto; }
    .terminal-header { display: flex; gap: 8px; margin-bottom: 12px; }
    .dot { width: 12px; height: 12px; border-radius: 50%; } .dot.red { background-color: #ff5f56; } .dot.yellow { background-color: #ffbd2e; } .dot.green { background-color: #27c93f; }
    </style>
    """, unsafe_allow_html=True)

    if not st.session_state.show_guide:
        st.markdown("<h1 style='text-align:center; font-size:2.5rem; margin-bottom:5px; font-weight:800; letter-spacing: -1px;'>Sign in</h1>", unsafe_allow_html=True)
        st.markdown("<p style='text-align:center; color:#8b949e; margin-bottom:40px; font-size:1rem;'>My Asset Hub Private Lounge</p>", unsafe_allow_html=True)
        st.text_input("URL ID", key="temp_api_url", value=st.session_state.api_url, placeholder="https://script.google.com/...")
        st.text_input("Private password", type="password", key="temp_passcode", value=st.session_state.passcode, placeholder="초대 코드를 입력하세요")
        st.markdown("<br>", unsafe_allow_html=True)
        st.button("Sign in", on_click=login, type="primary", use_container_width=True)
        st.markdown("<div style='text-align:center; margin-top:50px;'>", unsafe_allow_html=True)
        st.button("URL ID 생성방법 ✨", on_click=toggle_guide, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        st.markdown("<h2 style='text-align:center; font-size:1.8rem; margin-bottom:30px; font-weight: 700;'>✨ URL ID 생성방법</h2>", unsafe_allow_html=True)
        st.markdown("<div class='guide-card'><h4 style='color:#58a6ff; margin-top:0;'>STEP 1: 구글 시트 준비</h4>1. 구글 드라이브에서 <b>새 스프레드시트</b>를 생성합니다.<br>2. 상단 메뉴 <b>[확장 프로그램] ➡️ [Apps Script]</b>를 클릭합니다.</div>", unsafe_allow_html=True)
        st.markdown("<div class='guide-card'><h4 style='color:#58a6ff; margin-top:0;'>STEP 2: 엔진 코드 붙여넣기</h4>3. 열린 창의 내용을 지우고, 아래 코드를 복사하여 덮어씌웁니다.</div>", unsafe_allow_html=True)
        st.markdown("""
        <div class='terminal-box'>
            <div class='terminal-header'><div class='dot red'></div><div class='dot yellow'></div><div class='dot green'></div></div>
            <pre style="margin:0; font-family:'Consolas', monospace; font-size:0.85em; color:#3fb950; white-space:pre;"><code>function doPost(e) {
  var ss = SpreadsheetApp.getActiveSpreadsheet();
  var params = JSON.parse(e.postData.contents);
  for (var sheetName in params) {
    var data = params[sheetName];
    var sheet = ss.getSheetByName(sheetName) || ss.insertSheet(sheetName);
    sheet.clear();
    if (data && data.length > 0) {
      var headers = Object.keys(data[0]);
      var values = [headers];
      data.forEach(function(item) { values.push(headers.map(function(h) { return item[h]; })); });
      sheet.getRange(1, 1, values.length, headers.length).setValues(values);
    }
  }
  return ContentService.createTextOutput("Success");
}
function doGet(e) { ... (생략) ... }</code></pre>
        </div>
        """, unsafe_allow_html=True)
        st.markdown("<div class='guide-card'><h4 style='color:#58a6ff; margin-top:0;'>STEP 3: 배포 및 권한 승인</h4>4. 우측 상단 <b>[배포] ➡️ [새 배포]</b> 클릭<br>5. 설정 후 배포!<br><br><span style='color:#ff7b72;'>⚠️ <b>\"Google hasn’t verified this app\"</b> 해결:</span><br>&nbsp;&nbsp;↳ <b>[Advanced (고급)]</b> ➡️ <b>[Go to 프로젝트]</b> ➡️ <b>[Allow (허용)]</b><br>6. 발급된 <b>웹 앱 URL</b>을 복사하여 로그인 화면에 붙여넣으세요!</div>", unsafe_allow_html=True)
        st.button("⬅️ 로그인 화면으로 돌아가기", on_click=toggle_guide, use_container_width=True)
    st.stop()

# ==========================================
# 🟢 메인 자산 관리 앱 로직 (v1.44)
# ==========================================
st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem !important; max-width: 100% !important; }
    p, .stMarkdown, div[data-testid="stText"] { font-size: 1.1rem !important; }
    .goal-red { color: #E74C3C; font-weight: 900; font-size: 1.4rem; }
    .goal-green { color: #2ECC71; font-weight: 900; font-size: 1.4rem; }
    .green-text { color: #2ECC71; font-size: 0.95em; margin-bottom: 10px; font-weight: 500; }
    </style>
    """, unsafe_allow_html=True)

API_URL = st.session_state.api_url

def load_cloud_data(sheet_name):
    try:
        res = requests.get(f"{API_URL}?sheetName={sheet_name}", timeout=8)
        if res.status_code == 200:
            data = res.json()
            if isinstance(data, list): return data
        return []
    except: return []

def save_all_to_cloud():
    try:
        payload = {"stocks": st.session_state['stocks'], "savings": st.session_state['savings'], "config": [st.session_state['config']]}
        res = requests.post(API_URL, data=json.dumps(payload), timeout=15)
        return res.status_code == 200
    except: return False

if 'stocks' not in st.session_state: 
    with st.spinner("구글 금고에서 자산 정보 동기화 중..."): st.session_state['stocks'] = load_cloud_data('stocks')
if 'savings' not in st.session_state: st.session_state['savings'] = load_cloud_data('savings')
if 'config' not in st.session_state: 
    cfg = load_cloud_data('config')
    st.session_state['config'] = cfg[0] if cfg else {"target_asset
