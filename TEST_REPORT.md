# My Asset Hub v0.8.0-beta.2 독립 검증

Build: `20260928-beta-02`

대상 브랜치: `feature/v0.8.0-asset-flow-rebalance`. 검증 시작 및 push 전 원격 HEAD는 `1a8b6e3d8ad3f7b08eb275aa7fa585f12cba477f`. main 기준은 `985c32104e24325ac99851ec562286e3dba48bcd`이며 병합·운영 배포는 수행하지 않았다.

## 최종 결과

| 검사 | PASS | FAIL | 범위 |
|---|---:|---:|---|
| Worker/API/metadata | 17 | 0 | 실제 제공된 종목 카탈로그 검색, 모의 시세 검증, health/version/build, CORS |
| 기존 v0.7 회귀 | 29 | 0 | 평단, 목표, 실행, 부분체결, 수수료, migration, 위험군 이름, Excel, undo |
| 기존 v0.8 회귀 | 12 | 0 | 현재 잔액, 유동/고정, 월급/정기납입, 중복 방지, popup, undo, 수량 유지 |
| 추가 beta.2 단위/DOM | 13 | 0 | 유동 재원, 실제 차감 순서, 수수료·최소현금, Excel 복원, KRW 평단, Worker 분리 |
| 기존 Chromium 모바일 시나리오 | 2 | 0 | 검색·시세 fixture, Excel 왕복, 체결·undo·저장, 은행 편집 |
| 독립 Chromium 모바일 시나리오 | 13 | 0 | 아래 실제 터치·자금흐름·파일 복원 검사 |
| 외부 시세/환율 실제 호출 | 7 | 0 | USD/KRW, 삼성전자, KOSDAQ, AAPL, 국내/미국 ETF, KRW-BTC |
| **합계** | **93** | **0** | 테스트 케이스/시나리오 수; 개별 assertion 수와 다름 |

- `npm run check`: PASS.
- `npm test`: 71 PASS / 0 FAIL.
- `npm run test:browser`: 15 PASS / 0 FAIL.
- `npm run test:live`: 7 PASS / 0 FAIL. 2026-09-27 UTC 외부 응답 원본은 `test-evidence/beta2/live-results.json`. 현재가라는 명칭은 제공처의 최근 시세이며 응답의 `asOf` 기준 시각을 보존한다.
- 로그: `test-evidence/beta2/unit.txt`, `browser.txt`, `check.txt`.

## 모바일 390 × 844 검증

새 `browser-beta2.cjs`는 CDP의 **실제 touchStart/touchMove/touchEnd 이벤트**를 사용한다. `moveAsset()`을 직접 호출하거나 `elementFromPoint()`를 바꾸지 않는다. 이동 시 화면 스크롤로 목적지를 노출하고 실제 브라우저 hit test와 pointer capture를 거친다.

- 삼성전자·AAPL·QQQ·KRW-BTC·은행·cash: 교차 위험군 이동 popup, 취소 시 전체 state 동일, 승인 시 stable risk 변경, dashboard 비중·계산 입력 갱신, reload 유지 PASS.
- 투자자산 같은 그룹 정렬: displayOrder 변경 및 reload 유지, allocations 불변 PASS.
- 현금/은행 같은 그룹 정렬 및 목표비중 불변 PASS.
- 전체 리밸런싱: legacy 월 투자 선택지 없음, 수량 유지 checkbox, 목표비중 입력 너비 80px 이상, QQQ 5주 유지, 부분체결·수수료·undo PASS.
- 월 투자: 기존 투자자산 매도 없음, 현금부터 은행 잔액 사용, 고정은행 유지, undo PASS.
- 설정의 월급 및 적금 편집, 자동 반영 popup, undo, 다시 실행 후 월별 중복 반영 없음 PASS.
- JSON 실제 다운로드·가져오기·reload, cash 수정 실시간 콤마 및 숫자 저장 PASS.
- JavaScript page error 없음, 문서 가로 overflow 없음 PASS.

## 재현한 오류와 최소 수정

1. `moveAsset()`이 stocks를 찾지 못함 → 통합 자산 ID 조회로 변경.
2. 같은 그룹 정렬이 목표비중을 덮어씀 → 정렬에서는 순서만 변경. 교차 이동은 이전·이후 그룹에만 목표 재분배.
3. 전체 리밸런싱에 legacy 월 투자 옵션 노출 → 제거하고 `mode='rebalance'`로 고정. 엔진은 공통 사용.
4. 유동 은행이 재원에서 제외됨 → 공통 유동 잔액/차감 함수를 계획·체결에 사용. 실제 사용은 `funding`에 기록.
5. 테스트 설정의 Worker 이름이 운영과 같음 → `my-asset-hub-v08-test`로 분리.
6. 새 기기 Excel의 custom risk ID 오류, 구버전 적금 평가액 축소, Excel 목표금액 수정 무시 → 가져오는 백업의 context/legacy 잔액을 사용.
7. 소수점 원화 평단을 숫자 문자열에서 지우며 자릿수가 늘어남 → 원화 표시 반올림, 수정하지 않은 내부 평단 보존.
8. 현금 prompt가 실시간 콤마를 지원하지 않음 → 기존 편집 dialog 재사용.
9. 모바일 수량 유지 행의 목표 입력칸이 24px로 좁아짐 → 해당 grid 위치만 명시.

## 최종 투자 재원 정책

`cash.amount + liquid 은행 balance`에서 최소 현금을 남긴다. 월 투자는 입력 예산과 이 가용 잔액 중 작은 금액만 사용한다. 차감은 cash → liquid 자산 displayOrder → 같은 순서이면 stable ID 순이다. fixed 자산은 차감하지 않는다. 매도 순유입은 cash로 들어간다. 실제 체결 가격과 수수료를 다시 검증하며 실패하면 원본을 변경하지 않는다. 외부 가격이 동일하고 수수료가 0이면 투자 전후 총자산은 보존된다.

## NOT TESTED

- 실제 Android/iPhone 기기의 홈 화면 설치, 손가락 조작 및 OS별 standalone 동작.
- 배포된 테스트/production Worker의 `/api/health`와 설치된 PWA의 동시 일치. 이번 작업에서는 배포하지 않았다. 로컬 Worker 핸들러의 health 응답과 app/manifest/package/footer/SW cache 일치는 테스트했다.
- 이번 범위의 서비스 워커 오프라인 설치·업데이트 전환. 이번 변경은 cache 버전 갱신이며 네트워크/캐시 동작 로직은 그대로 유지했다.
