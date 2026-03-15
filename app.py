import streamlit as st
import pandas as pd
import FinanceDataReader as fdr

st.title("🔍 통합 검색 엔진 생존 테스트 (국장 + ETF + 미장)")
st.write("클라우드 방화벽을 뚫고 내장 DB에서 종목을 찾아옵니다.")

# 전 세계 시장 데이터를 한 번에 다운로드 (하루 1번 캐싱)
@st.cache_data(ttl=86400)
def load_market_data():
    dfs = []
    
    # 1. 한국 주식 (KRX)
    try:
        df_krx = fdr.StockListing('KRX')
        df_krx = df_krx.rename(columns={'Code': '티커', 'Name': '종목명'})
        df_krx['시장'] = '한국주식(KRX)'
        dfs.append(df_krx[['티커', '종목명', '시장']])
    except: pass
    
    # 2. 한국 ETF (ETF/KR)
    try:
        df_etf = fdr.StockListing('ETF/KR')
        df_etf = df_etf.rename(columns={'Symbol': '티커', 'Name': '종목명'})
        df_etf['시장'] = '한국ETF'
        dfs.append(df_etf[['티커', '종목명', '시장']])
    except: pass

    # 3. 미국 주식 (NASDAQ, NYSE, AMEX)
    for market in ['NASDAQ', 'NYSE', 'AMEX']:
        try:
            df_us = fdr.StockListing(market)
            df_us = df_us.rename(columns={'Symbol': '티커', 'Name': '종목명'})
            df_us['시장'] = f'미국주식({market})'
            dfs.append(df_us[['티커', '종목명', '시장']])
        except: pass
        
    if dfs:
        total_df = pd.concat(dfs, ignore_index=True)
        # 검색 에러 방지를 위해 문자로 변환
        total_df['종목명'] = total_df['종목명'].astype(str)
        total_df['티커'] = total_df['티커'].astype(str)
        return total_df
    else:
        return "데이터 로드 실패"

df = load_market_data()

if isinstance(df, pd.DataFrame):
    st.success(f"✅ 전체 시장 데이터 로드 완료! (총 {len(df):,}개 종목 탑재)")
    
    query = st.text_input("검색어 (종목명 일부 또는 티커 입력)", "TIGER 미국")
    
    if st.button("🚀 검색 시작"):
        with st.spinner("방대한 DB에서 검색 중..."):
            # 대소문자 구분 없이, 검색어가 종목명이나 티커에 포함된 결과 찾기 (부분 일치)
            mask = df['종목명'].str.contains(query, case=False, na=False) | df['티커'].str.contains(query, case=False, na=False)
            result = df[mask]
            
            if not result.empty:
                st.success(f"🎉 총 {len(result)}개의 결과를 찾았습니다! (상위 10개 표시)")
                st.dataframe(result.head(10))
            else:
                st.warning(f"❌ '{query}'에 대한 검색 결과가 없습니다.")
                st.info("💡 미국 주식은 영어 이름(예: Apple)이나 티커(예: AAPL)로 검색해 보세요.")
else:
    st.error(df)
