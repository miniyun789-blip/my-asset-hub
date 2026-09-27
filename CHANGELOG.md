# CHANGELOG

## v0.7.0-beta.1 — 2026-09-26 (TEST)

Added
- 원화 매수원가, schema v3 migration, 운영 원본/테스트 저장 분리.
- stable risk ID, 이름·설명 편집, 삭제 시 자산 이동, 현금 연결 그룹.
- 별도 현금/예수금, 3단계 리밸런싱, 정수 주식·소수점 코인·예산 검증.
- 월 투자 2개 모드, 최소 현금, 매수 제외, 전후 Preview.
- 실제 체결·부분체결·수수료·최종 확인, 거래/납입 이력, 자동 백업·되돌리기.
- Excel 원화평단/현금/v3 백업, TEST 버전/build 표시.

Fixed
- 종목 시세 응답 순서 경합 및 async submit의 currentTarget 참조.
- 고정 은행자산을 매수 가용현금으로 잘못 사용하는 위험 방지.
- 다른 서비스워커를 일괄 해제하던 main 앱 코드 제거(네트워크 전용 유지).

Verified
- 기존 시장 테스트 15 + v0.7 계산/DOM 29 PASS.
- Chromium 모바일 사용자 흐름, 실제 xlsx 파일 왕복·거래 복구 PASS.
- 별도 임시 Cloudflare Worker 배포. 운영 main/URL 변경 없음.
- 실기기/개인 데이터/임시 주소 한계는 TEST_REPORT 참조.


## v0.6.0 — 2026-09-25

### Added
- 공개 종목목록 17,575개: 국내·미국·ETF·Upbit KRW 검색과 페이지 이동.
- 시작/주기 자동 환율·시세, 실패·가격 기준시각 표시, Cloudflare Worker Static Assets 배포 구성.
- 동일 종목 추가매수 가중평단·매수환율 합산.
- Excel 6개 시트 내보내기/가져오기, ID·시세·기록·목표 보존, 해외여부 필드.
- 가져오기 미리보기·직전 복구·손상 원본 백업.
- PWA 업데이트 적용 버튼, 설치 안내, 오프라인 Excel.
- 버전·패키징·공개 종목목록 갱신 스크립트와 재현 가능한 테스트.

### Fixed
- history 누락 가져오기 오류, 문자열 FALSE, 국내 코드 앞자리 0.
- KOSDAQ GLOBAL 오분류, NASDAQ/NYSEARCA 시장 코드 처리.
- 손상된 저장 원본 자동 덮어쓰기, 다른 앱 캐시 삭제.
- 해외 리밸런싱 수량의 원화 환산, 잘못된 목표 합계의 매매 안내.
- 예금·파킹통장 잔액의 회차 중복 곱셈.
- FX query1 시간 초과를 확인하고 query2 경로 적용.
- API 경로가 SPA HTML 응답으로 바뀌지 않도록 Worker 우선 라우팅.

### Verified
- Worker 15, SW 단위 테스트 4, DOM/데이터 17 = 36개 PASS.
- 실제 시세/환율 대표 7건 PASS, Wrangler dry-run PASS.
- Excel 바이너리 왕복·계산·이전 데이터 형식·손상 데이터 보호 PASS.
- 최종 실제 브라우저/모바일/Cloudflare 배포는 NOT TESTED. TEST_REPORT 참고.

## v0.5.1 — checkpoint

- 기존 v0.5.0에서 history 선택 처리, FALSE 변환, 손상 원본 보호, 앱 캐시 범위 최소 수정.
- 기본 앱·은행 저장·reload·손상 원본 보호 브라우저 확인.
- 검색/시세/Excel/전체 회귀는 이 체크포인트에서 완료되지 않음.

## v0.5.0 — 제공된 예약 작업 결과

- 작업 기준으로 보존. 완성본 또는 검증 완료판으로 간주하지 않음.
