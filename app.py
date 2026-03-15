import streamlit as st
import pandas as pd
import FinanceDataReader as fdr

st.title("🔍 국장 검색 엔진 생존 테스트 (수정본)")
st.write("클라우드 방화벽을 뚫고 한글 종목명을 찾아오는지 검증합니다.")

# 한국거래소(KRX) 전체 종목 리스트를 공식적으로 다운로드 (하루 1번만 캐싱)
@st.cache_data(ttl=86400)
def load_krx_data():
    try:
        # fdr.StockListing('KRX')는 한국 주식 전체 데이터를 빠르고 안전하게 가져옵니다.
        df = fdr.StockListing('KRX')
        return df[['Code', 'Name']]
    except Exception as e:
        return str(e)

# 테스트 입력창
query = st.text_input("검색할 한글 종목명 (예: 삼성전자, 카카오, SK하이닉스)", "삼성전자")

if st.button("🚀 테스트 시작"):
    with st.spinner("한국거래소 공식 데이터 뒤지는 중..."):
        df = load_krx_data()
        
        if isinstance(df, pd.DataFrame):
            # 입력한 이름과 정확히 일치하는 데이터 찾기
            result = df[df['Name'] == query]
            
            if not result.empty:
                code = result.iloc[0]['Code']
                st.success(f"✅ 검색 대성공! '{query}'의 티커는 '{code}' 입니다.")
                st.info(f"구글 파이낸스 변환: {code}:KRX")
                st.info(f"야후 파이낸스 변환: {code}.KS")
            else:
                st.warning(f"❌ '{query}' 종목을 한국거래소 공식 명단에서 찾을 수 없습니다. 띄어쓰기를 확인해 주세요.")
        else:
            st.error(f"❌ 라이브러리 로드 실패 (에러 내용: {df})")
