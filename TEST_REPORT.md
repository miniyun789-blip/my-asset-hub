# My Asset Hub v0.8.0-beta.1 · TEST

## 자동 테스트

| 영역 | PASS | FAIL | 비고 |
|---|---:|---:|---|
| Market Worker API | 15 | 0 | 국내/미국/ETF/코인 검색·시세 응답 모의 입력 |
| v0.7 회귀 | 29 | 0 | JSON/localStorage/Excel/체결/undo/평단/리스크 |
| v0.8 계산·migration | 12 | 0 | 기존 적금 평가액 유지, 월급·이체 멱등성, 최소 현금, 수량 유지 등 |
| Chromium 390px 기존 모바일 흐름 | 1 | 0 | 실제 브라우저: 삼성전자 검색, 자동 시세, risk, 투자, 부분체결·수수료, reload, Excel 왕복, undo, 스크롤 |
| Chromium 390px 신규 모바일 흐름 | 1 | 0 | 신규 은행 입력, 원화 콤마, pointer 위험군 취소/승인과 재시작 저장, 가로 넘침 없음 |

`npm run check`, `npm test`, `npm run test:browser` 및 `node tests/browser-v08.cjs`를 실행했다. API 시험 응답은 테스트 fixture이며 실제 시장 서버 연결을 의미하지 않는다.

## 미검증·제약

- NOT TESTED: 물리 Android/iPhone 홈 화면 설치 및 오프라인에서 실제 금융 시세 조회.
- NOT TESTED: 배포된 `/api/health`와 브라우저 빌드 일치; 로컬 Worker 상수와 앱 상수는 같은 `20260927-beta-01`.
- NOT TESTED: 현금/은행 자산 외 투자 종목의 터치 위험군 이동을 실제 손가락으로 조작하는 기기 시험. 코드 경로는 공통이며 테스트 자동화는 은행 자산에 적용했다.
- LIMITATION: 일반 유동 은행 잔액은 현금으로 자동 이체되지 않는다. 투자 재원은 앱 내부 `cash`로 관리한다.
- LIMITATION: 서비스 워커 설치 자격은 HTTPS 테스트 배포 후 브라우저 개발자 도구로 최종 확인해야 한다.
