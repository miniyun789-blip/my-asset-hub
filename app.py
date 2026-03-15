import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from datetime import datetime, timedelta
import os
import requests
from bs4 import BeautifulSoup
import re
import FinanceDataReader as fdr
import json

# ==========================================
# [중요] 성민 대표님 전용 구글 앱스 스크립트 URL
# ==========================================
API_URL = "https://script.google.com/macros/s/AKfycbx6-L0Rl4GlpZloBZ79M9mqHYSnSTOCaaHjVnhF5mYKcPF42QaShH0A54vD6WUz4O45/exec"

# ==========================================
# 1. 앱 기본 설정 & UI 스타일링
# ==========================================
st.set_page_config(page_title="My Asset Hub V38", layout="wide")

st.markdown("""
    <style>
    .block-container { padding-top: 1.5rem; padding-left: 1rem; padding-right: 1rem; }
    p, .stMarkdown, div[data-testid="stText"] { font-size: 1.1rem !important; }
    .stMetric label { font-size: 1rem !important; }
    .stMetric value { font-size: 1.8rem !important; }
    .stDataFrame { font-size: 1rem !important; }
    .goal-red { color: #E74C3C; font-weight: 900; font-size: 1.4rem; }
    .goal-green { color: #2ECC71; font-weight: 900; font-size: 1.4rem; }
    .green-text { color: #2ECC71; font-size: 0.95em; font-weight: 500; margin-bottom: 5px; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# 2. 클라우드 데이터 동기화 엔진 (화이트스크린 방어형)
# ==========================================
def load_cloud_data(sheet_name):
    try:
        res = requests.get(f"{API_URL}?sheetName={sheet_name}", timeout=8)
        if res.status_code == 200:
            data = res.json()
            return data if isinstance(data, list) else []
        return []
    except:
        return []

def save_cloud_data(data, sheet_name):
    try:
        payload = {"sheetName": sheet_name, "data": data}
        requests.post(API_URL, data=json.dumps(payload), timeout=10)
        return True
    except:
        return False

# 세션 데이터 초기화 (구글 시트 연동)
if 'stocks' not in st.session_state: 
    with st.spinner("구글 금고에서 자산 정보 가져오는 중..."):
        st.session_state['stocks'] = load_cloud_data('stocks')
if 'savings' not in st.session_state: st.session_state['savings'] = load_cloud_data('savings')
if 'config' not in st.session_state: 
    cfg = load_cloud_data('config')
    st.session_state['config'] = cfg[0] if cfg else {"target_asset": 1000000000, "risk_levels": "초고위험,위험,중립,안전"}

active_risks = [r.strip() for r in st.session_state['config'].get('risk_levels', "초고위험,위험,중립,안전").split(',') if r.strip()]

def sort_and_save():
    def get_risk_weight(r):
        try: return active_risks.index(r)
        except: return 99
    # 리스크 순서 정렬 -> 같은 리스크 내 평가액 큰 순 정렬
    st.session_state['stocks'].sort(key=lambda x: (get_risk_weight(x.get('리스크')), -(float(x.get('매수평단가', 0)) * float(x.get('보유수량', 0)))))
    s1 = save_cloud_data(st.session_state['stocks'], 'stocks')
    s2 = save_cloud_data(st.session_state['savings'], 'savings')
    s3 = save_cloud_data([st.session_state['config']], 'config')
    return s1 and s2 and s3

# ==========================================
# 3. 데이터 수집 엔진
# ==========================================
kst_now = datetime.utcnow() + timedelta(hours=9)
logic_date_str = (kst_now - timedelta(days=1)).strftime('%Y-%m-%d') if kst_now.hour < 3 else kst_now.strftime('%Y-%m-%d')

@st.cache_data(ttl=86400)
def load_market_data():
    dfs = []
    try:
        df_krx = fdr.StockListing('KRX'); df_krx['시장'] = 'KRX'; dfs.append(df_krx[['Code', 'Name', '시장']])
        df_etf = fdr.StockListing('ETF/KR'); df_etf['시장'] = 'ETF/KR'; dfs.append(df_etf[['Symbol', 'Name', '시장']].rename(columns={'Symbol':'Code'}))
        for mkt in ['NASDAQ', 'NYSE', 'AMEX']:
            try:
                df_us = fdr.StockListing(mkt); df_us['시장'] = mkt; dfs.append(df_us[['Symbol', 'Name', '시장']].rename(columns={'Symbol':'Code'}))
            except: pass
    except: pass
    return pd.concat(dfs, ignore_index=True) if dfs else None

@st.cache_data(ttl=600)
def get_exchange_rate():
    try:
        res = requests.get("https://www.google.com/finance/quote/USD-KRW", headers={'User-Agent': 'Mozilla/5.0'})
        soup = BeautifulSoup(res.text, 'html.parser')
        return float(soup.select_one('.YMlKec.fxKbKc').text.replace(',', ''))
    except: return 1350.0

@st.cache_data(ttl=300)
def get_price(ticker):
    if ticker.startswith("KRW-"):
        try: return requests.get(f"https://api.upbit.com/v1/ticker?markets={ticker}").json()[0]['trade_price']
        except: return 0.0
    clean_ticker = ticker.replace('.KS', '').replace('.KQ', '')
    markets = [f"{clean_ticker}:KRX", f"{clean_ticker}:KOSDAQ", f"{clean_ticker}:NASDAQ", f"{clean_ticker}:NYSE", f"{clean_ticker}:NYSEARCA"]
    for gf_ticker in markets:
        try:
            res = requests.get(f"https://www.google.com/finance/quote/{gf_ticker}", headers={'User-Agent': 'Mozilla/5.0'}, timeout=3)
            if 'YMlKec fxKbKc' in res.text:
                soup = BeautifulSoup(res.text, 'html.parser')
                return float(soup.select_one('.YMlKec.fxKbKc').text.replace('₩', '').replace('$', '').replace(',', ''))
        except: pass
    return 0.0

exchange_rate = get_exchange_rate()

# ==========================================
# 4. 사이드바 컨트롤러
# ==========================================
with st.sidebar:
    st.title("🛠️ 컨트롤러")
    st.metric("💵 실시간 환율", f"{exchange_rate:,.2f} 원")
    
    st.divider()
    with st.expander("⚙️ 시스템 설정"):
        curr_tgt = int(st.session_state['config'].get('target_asset', 1000000000))
        new_tgt = st.text_input("목표 자산 (원)", value=f"{curr_tgt:,}")
        if st.button("목표 저장"):
            st.session_state['config']['target_asset'] = int(new_tgt.replace(",", ""))
            sort_and_save(); st.rerun()

    st.markdown("### ➕ 투자 자산 추가")
    asset_input = st.text_input("🔍 종목/티커 검색", placeholder="예: 삼성전자, SCHD")
    
    if asset_input:
        options = []
        coin_map = {"비트코인": "KRW-BTC", "이더리움": "KRW-ETH", "리플": "KRW-XRP", "솔라나": "KRW-SOL"}
        for k, v in coin_map.items():
            if k in asset_input: options.append(f"[가상화폐] {k} ({v})")
        df_m = load_market_data()
        if df_m is not None:
            mask = df_m['Name'].str.contains(asset_input, case=False, na=False) | df_m['Code'].str.contains(asset_input, case=False, na=False)
            for _, r in df_m[mask].head(20).iterrows(): options.append(f"[{r['시장']}] {r['Name']} ({r['Code']})")
        if re.match(r"^[A-Za-z0-9]+$", asset_input.strip()): options.append(f"[해외 직접입력] {asset_input.upper()} ({asset_input.upper()})")
        
        if options:
            selected = st.selectbox("💡 종목 선택", list(dict.fromkeys(options)))
            m = re.match(r"\[(.*?)\] (.*) \((.*?)\)", selected)
            if m:
                sel_mkt, sel_name, sel_code = m.group(1), m.group(2), m.group(3)
                is_f = (sel_mkt in ['NASDAQ', 'NYSE', 'AMEX', '해외 직접입력'])
                curr_l = "달러 $" if is_f else "원 ₩"
                raw_p = st.text_input(f"매수 단가 ({curr_l})", value="0")
                new_p = float(raw_p.replace(',', '')) if raw_p.replace(',', '').replace('.','').isdigit() else 0.0
                new_q = st.number_input("보유 수량", min_value=0.0, step=0.01)
                risk_lv = st.selectbox("리스크 분류", active_risks)
                
                if st.button("내 자산으로 저장", use_container_width=True):
                    existing = next((i for i, s in enumerate(st.session_state['stocks']) if s.get('티커') == sel_code), None)
                    if existing is not None:
                        old = st.session_state['stocks'][existing]
                        final_q = float(old.get('보유수량', 0)) + new_q
                        final_p = ((float(old.get('매수평단가', 0)) * float(old.get('보유수량', 0))) + (new_p * new_q)) / final_q if final_q > 0 else 0
                        st.session_state['stocks'][existing].update({'매수평단가': final_p, '보유수량': final_q})
                    else:
                        st.session_state['stocks'].append({"종목명": sel_name, "티커": sel_code, "매수평단가": new_p, "보유수량": new_q, "해외여부": is_f, "리스크": risk_lv})
                    if sort_and_save(): st.toast("✅ 구글 시트 동기화 완료!"); st.rerun()

    with st.expander("⚙️ 리스크 분류 관리"):
        risk_df = pd.DataFrame({"리스크 명칭": active_risks})
        edited_risk = st.data_editor(risk_df, num_rows="dynamic", use_container_width=True, hide_index=True)
        if st.button("✔️ 분류 저장"):
            st.session_state['config']['risk_levels'] = ",".join(edited_risk['리스크 명칭'].dropna().tolist())
            sort_and_save(); st.rerun()

    with st.expander("🏦 은행 자산 추가"):
        b_type = st.selectbox("종류", ["적금", "주택청약", "예금", "파킹통장"])
        b_name = st.text_input("통장이름")
        raw_m = st.text_input("월 납입액 (원)", value="1,000,000")
        b_curr = st.number_input("현재 회차", min_value=1)
        b_total = st.number_input("총 만기 회차", min_value=1)
        b_rate = st.number_input("연 이율 (%)", min_value=0.0, step=0.1, value=3.0)
        if st.button("은행 자산 저장"):
            st.session_state['savings'].append({"종류": b_type, "상품명": b_name, "월납입액": int(raw_m.replace(',','')), "현재회차": b_curr, "총회차": b_total, "이율": b_rate})
            sort_and_save(); st.rerun()

    st.divider()
    st.markdown("### ☁️ 클라우드 연결 진단")
    if st.button("🚀 지금 즉시 엑셀로 저장하기", use_container_width=True):
        if sort_and_save(): st.toast("✅ 엑셀 동기화 성공!")

# ==========================================
# 5. 메인 화면 (대시보드)
# ==========================================
st.title("💰 My Asset Hub V38")

# 연산 로직
risk_group = {r: 0 for r in active_risks}; risk_group["고정(은행)"] = 0
port_group = {"가상화폐": 0, "해외 주식": 0, "국내 주식": 0} 
stock_disp = []; total_buy = 0 

for idx, s in enumerate(st.session_state['stocks']):
    tk, is_f, bp, qt = s.get('티커'), s.get('해외여부'), float(s.get('매수평단가', 0)), float(s.get('보유수량', 0))
    curr = get_price(tk)
    curr_krw = curr * exchange_rate if is_f else curr
    b_amt = bp * qt * (exchange_rate if is_f else 1)
    e_amt = curr_krw * qt
    total_buy += b_amt
    
    if tk.startswith("KRW-"): port_group["가상화폐"] += e_amt
    elif is_f: port_group["해외 주식"] += e_amt
    else: port_group["국내 주식"] += e_amt
    
    r_cat = s.get('리스크', active_risks[0])
    risk_group[r_cat] = risk_group.get(r_cat, 0) + e_amt
    
    profit = (e_amt - b_amt) / b_amt * 100 if b_amt > 0 else 0
    stock_disp.append({"ID": idx, "종목명": s.get('종목명'), "티커": tk, "매수": b_amt, "평가": e_amt, "수익률": profit, "리스크": r_cat, "현재가": curr, "해외": is_f, "매수평단가": bp, "보유수량": qt})

total_sav_val = 0; total_bank_principal = 0; fixed_sav_val = 0
for sav in st.session_state['savings']:
    m, c, t = int(sav.get('월납입액', 0)), int(sav.get('현재회차', 0)), int(sav.get('총회차', 1))
    amt = m * c
    total_sav_val += amt; total_buy += amt
    total_bank_principal += (m * t)
    if sav.get('종류') in ["적금", "주택청약"]: fixed_sav_val += amt
risk_group["고정(은행)"] += total_sav_val

grand_total = sum(port_group.values()) + total_sav_val

# 히스토리 동기화
history_data = load_cloud_data('history')
history_df = pd.DataFrame(history_data) if history_data else pd.DataFrame(columns=["날짜", "총자산"])
if grand_total > 0:
    if not history_df.empty and logic_date_str in history_df['날짜'].values:
        history_df.loc[history_df['날짜'] == logic_date_str, '총자산'] = grand_total
    else:
        history_df = pd.concat([history_df, pd.DataFrame([{"날짜": logic_date_str, "총자산": grand_total}])], ignore_index=True)
    save_cloud_data(history_df.to_dict('records'), 'history')

# 목표 현황 메트릭
target = st.session_state['config'].get('target_asset', 1000000000)
achieved = (grand_total / target * 100) if target > 0 else 0
if achieved < 100: st.markdown(f"### 🏆 목표 ({target:,.0f}원) | <span class='goal-red'>{100-achieved:.1f}% 남음 🔥</span>", unsafe_allow_html=True)
else: st.markdown(f"### 🏆 목표 ({target:,.0f}원) | <span class='goal-green'>🎉 {achieved-100:.1f}% 초과 달성 🎉</span>", unsafe_allow_html=True)
st.progress(min(achieved / 100, 1.0))

c1, c2, c3 = st.columns(3)
c1.metric("총 자산", f"{grand_total:,.0f}원")
c2.metric("매수 원금", f"{total_buy:,.0f}원")
c3.metric("수익금", f"{grand_total-total_buy:,.0f}원", f"{(grand_total-total_buy)/total_buy*100:.1f}%" if total_buy>0 else "0%")

st.markdown("---")
tab1, tab2, tab3 = st.tabs(["📊 대시보드", "📋 자산 관리", "⚖️ 리밸런싱 (3-Step)"])

with tab1:
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        fig1 = go.Figure(data=[go.Pie(labels=["가상화폐", "해외 주식", "국내 주식", "은행(안전)"], values=[port_group["가상화폐"], port_group["해외 주식"], port_group["국내 주식"], total_sav_val], hole=.4, sort=False, marker_colors=['#F39C12', '#9B59B6', '#3498DB', '#1ABC9C'])])
        fig1.update_layout(title="포트폴리오 비중", height=320, margin=dict(t=40, b=10))
        st.plotly_chart(fig1, use_container_width=True)
    with col_p2:
        colors = ['#E74C3C', '#F39C12', '#3498DB', '#2ECC71', '#9B59B6', '#1ABC9C', '#34495E']
        fig2 = go.Figure(data=[go.Pie(labels=list(risk_group.keys()), values=list(risk_group.values()), hole=.4, marker_colors=colors)])
        fig2.update_layout(title="리스크 다각화", height=320, margin=dict(t=40, b=10))
        st.plotly_chart(fig2, use_container_width=True)
    
    if not history_df.empty:
        st.subheader("🚀 자산 성장 타임라인 (03:00 KST)")
        fig_line = px.area(history_df, x="날짜", y="총자산", markers=True, color_discrete_sequence=['#2E86C1'])
        fig_line.update_layout(height=300, margin=dict(t=10, b=10))
        st.plotly_chart(fig_line, use_container_width=True, config={'staticPlot': True})

with tab2:
    st.subheader(f"📈 투자 자산 내역 (총 평가: {sum(x['평가'] for x in stock_disp):,.0f}원)")
    # 리스크 순 정렬 재확인
    def get_rp(r): 
        try: return active_risks.index(r)
        except: return 99
    stock_disp.sort(key=lambda x: (get_rp(x['리스크']), -x['평가']))
    
    for s in stock_disp:
        c_i, c_e, c_d = st.columns([6, 0.7, 0.7])
        with c_i:
            cur_s = "$" if s['해외'] else "₩"
            st.markdown(f"**{s['종목명']} ({s['티커']})** | **[{s['리스크']}]** | {'🔥' if s['수익률']>0 else '❄️'} **{s['수익률']:.2f}%**")
            # [핵심 수정] 초록색 폰트 테마 적용
            st.markdown(f"<div class='green-text'>↳ 평단가(수수료제외): <b>{s['매수평단가']:,.2f}{cur_s}</b> | 수량: <b>{s['보유수량']:.2f}</b> | 평가: <b>{s['평가']:,.0f}원</b></div>", unsafe_allow_html=True)
        with c_e:
            if st.button("✏️", key=f"e_{s['ID']}"): st.session_state[f"em_{s['ID']}"] = not st.session_state.get(f"em_{s['ID']}", False)
        with c_d:
            if st.button("🗑️", key=f"d_{s['ID']}"): st.session_state['stocks'].pop(s['ID']); sort_and_save(); st.rerun()
        if st.session_state.get(f"em_{s['ID']}", False):
            new_p = st.number_input("평단가 수정", value=float(s['매수평단가']), key=f"np_{s['ID']}")
            new_q = st.number_input("수량 수정", value=float(s['보유수량']), key=f"nq_{s['ID']}")
            if st.button("저장", key=f"sv_{s['ID']}"):
                st.session_state['stocks'][s['ID']].update({'매수평단가': new_p, '보유수량': new_q}); sort_and_save(); st.rerun()
    
    st.divider()
    st.subheader(f"🏦 은행 자산 내역 (총 원금: {total_bank_principal:,.0f}원)")
    for i, sav in enumerate(st.session_state['savings']):
        c_i, c_e, c_d = st.columns([6, 0.7, 0.7])
        with c_i:
            s_type, s_name, s_rate = sav.get('종류', '정보없음'), sav.get('상품명', '이름없음'), sav.get('이율', 0)
            m_v, c_v, t_v = int(sav.get('월납입액', 0)), int(sav.get('현재회차', 0)), int(sav.get('총회차', 1))
            st.markdown(f"**[{s_type}] {s_name}** (연 {s_rate}%) | 원금: {m_v * t_v:,.0f}원")
            # [핵심 수정] 초록색 폰트 테마 적용
            st.markdown(f"<div class='green-text'>↳ {c_v}/{t_v}개월 진행 중</div>", unsafe_allow_html=True)
            st.progress(min(1.0, c_v / t_v) if t_v > 0 else 0)
        with c_e:
            if st.button("✏️", key=f"eb_{i}"): st.session_state[f"ebm_{i}"] = not st.session_state.get(f"ebm_{i}", False)
        with c_d:
            if st.button("🗑️", key=f"db_{i}"): st.session_state['savings'].pop(i); sort_and_save(); st.rerun()

with tab3:
    st.subheader("⚖️ 1단계: 비중 설정")
    fixed_p = round(fixed_sav_val/grand_total*100, 1) if grand_total>0 else 0
    cols = st.columns(len(active_risks) + 1)
    tgt_w = {}
    for i, r in enumerate(active_risks): tgt_w[r] = cols[i].number_input(f"{r}", value=0.0, step=1.0)
    cols[-1].number_input("고정(은행)", value=float(fixed_p), disabled=True)
    
    total_input = round(sum(tgt_w.values()) + fixed_p, 1)
    if abs(total_input - 100.0) < 0.2:
        st.success(f"✅ 100% 일치 (현재 {total_input}%)")
        st.divider(); st.subheader("🔬 2단계: 세부 조율")
        re_items = []
        for s in stock_disp: re_items.append({"자산군": s['리스크'], "종목명": s['종목명'], "현재금액": int(s['평가']), "현재가": s['현재가']})
        for sv in st.session_state['savings']:
            grp = "고정(은행)" if sv.get('종류') in ["적금", "주택청약"] else active_risks[-1]
            re_items.append({"자산군": grp, "종목명": sv.get('상품명'), "현재금액": int(sv.get('월납입액',0))*int(sv.get('현재회차',0)), "현재가": 0})
        
        # 없는 자산군 표시
        eg = set(x['자산군'] for x in re_items)
        for g in active_risks:
            if g not in eg: re_items.append({"자산군": g, "종목명": "💡 신규 자산 필요", "현재금액": 0, "현재가": 0})

        rdf = pd.DataFrame(re_items)
        def style_rebal(df):
            cp = ['#FFCDD2','#FFE0B2','#BBDEFB','#C8E6C9','#E1BEE7','#D7CCC8']
            sdf = pd.DataFrame('', index=df.index, columns=df.columns)
            for i, row in df.iterrows():
                try: ix = active_risks.index(row['자산군'])
                except: ix = -1
                color = cp[ix % len(cp)] if ix != -1 else '#F5F5F5'
                sdf.iloc[i] = f'background-color: {color}'
            return sdf

        if not rdf.empty:
            rdf['💡 목표(%)'] = rdf.apply(lambda x: round((x['현재금액']/grand_total*100),1), axis=1)
            rdf['sort_key'] = rdf['자산군'].apply(get_rp)
            rdf.sort_values(['sort_key', '현재금액'], ascending=[True, False], inplace=True)
            styled_rdf = rdf[['자산군', '종목명', '현재금액', '💡 목표(%)']].style.apply(style_rebal, axis=None)
            edited = st.data_editor(styled_rdf, use_container_width=True, hide_index=True)
            
            if st.button("🚀 3단계: 액션 플랜 생성"):
                st.session_state['rebal_df'] = rdf.copy()
                st.session_state['rebal_df']['💡 목표(%)'] = edited['💡 목표(%)'].values
                st.session_state['rebal_go'] = True
            
            if st.session_state.get('rebal_go'):
                st.divider(); st.subheader("🎯 3단계: 액션 플랜")
                rf = st.session_state['rebal_df']
                rf['목표금액'] = (grand_total * (rf['💡 목표(%)'] / 100)).astype(int)
                rf['차액'] = rf['목표금액'] - rf['현재금액']
                def get_act(row):
                    if row['자산군'] == "고정(은행)": return "🔒 유지", "-"
                    d = row['차액']
                    if d > 10000: return f"🟢 매수 (+{d:,.0f}원)", f"약 {d/row['현재가']:.2f}주" if row['현재가']>0 else "-"
                    if d < -10000: return f"🔴 매도 ({abs(d):,.0f}원)", f"약 {abs(d)/row['현재가']:.2f}주" if row['현재가']>0 else "-"
                    return "유지", "-"
                rf[['액션', '가이드']] = rf.apply(get_act, axis=1, result_type='expand')
                st.dataframe(rf[['자산군', '종목명', '현재금액', '목표금액', '액션', '가이드']], hide_index=True)
    else:
        st.warning(f"합계 {total_input}%입니다. 100%를 맞춰주세요!")
