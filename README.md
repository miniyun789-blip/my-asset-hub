# My Asset Hub · TEST v0.8.0-beta.2

Build: `20260928-beta-02`
Branch: `feature/v0.8.0-asset-flow-rebalance`
Worker: **`my-asset-hub-v08-test`**

기존 v0.8 beta.1을 검증하고 발견된 오류만 수정한 테스트 버전입니다. 금융기관 연결, 실제 주문 전송, 사용자 자산의 서버 수집은 하지 않습니다.

## 실행과 검증

1. GitHub에서 위 feature 브랜치를 받습니다.
2. `npm ci`를 실행합니다.
3. `npm run check`, `npm test`를 실행합니다.
4. `npx playwright install chromium` 후 `npm run test:browser`를 실행합니다. 기존 브라우저를 사용할 때는 `CHROMIUM_EXECUTABLE`에 실행 파일 경로를 지정할 수 있습니다.
5. `npm run dev`로 앱을 엽니다. 하단의 TEST 버전/build와 `/api/health` 응답을 비교합니다.

`npm test`는 시장 API·계산·저장·migration·체결·undo·메타데이터 검사를 실행합니다. `npm run test:browser`는 390px Chromium에서 기존 흐름과 실제 터치 이벤트에 의한 투자자산/은행/현금 드래그, 월 투자, 전체 리밸런싱, 자동 반영, 파일 백업·복원을 실행합니다. 테스트에는 가상 데이터만 사용합니다.

`npm run test:live`는 공개 시장 서버에 실제로 접속합니다. 시세 및 환율은 제공처 기준 시각과 통화를 확인하며, 실패하면 앱은 기존 저장 가격을 유지합니다.

## 유동자산 투자 재원 정책

- 유동 현금성 잔액 = `cash.amount` + `liquidityType='liquid'` 은행자산의 `balance` 합계.
- `fixed`는 투자 재원에서 제외하며 자산가치와 리스크 비중에는 포함합니다.
- 두 투자 화면 모두 같은 최소 현금 설정과 체결 엔진을 사용합니다. 월 투자는 입력 예산과 최소 현금을 지키며 기존 종목을 매도하지 않습니다.
- 실제 차감은 현금부터, 이후 유동 은행자산의 `displayOrder` 오름차순입니다. 순서가 같으면 stable asset ID 오름차순입니다. 매도 순유입은 현금에 반영합니다.
- 수수료는 실제 체결 비용에 포함합니다. 자산별 순변동은 거래 이력의 `funding`에 기록하고 `liquidAfter`에 전체 유동 잔액을 남깁니다. 되돌리기는 은행 잔액도 복구합니다.
- 월 투자 화면의 투자금은 이미 등록된 유동 잔액을 사용합니다. 월급 자동 반영 후 투자하더라도 총자산에 다시 더하지 않습니다. 기존 데이터와 테스트의 외부 신규자금 모드는 공통 엔진 내부 호환성으로 유지합니다.

## 저장과 백업

기본 저장 키는 `my-asset-hub-beta-v4`, schema는 4입니다. v0.7의 `my-asset-hub-beta-v3`와 초기 `my-asset-hub-html-v1`에서 읽어 이전하며 기존 키는 삭제하지 않습니다. 최초 이행 전 원본은 새 키의 `-before-migration`에 보존합니다. 이행 실패 시 원본을 덮어쓰지 않습니다.

구버전 적금/청약은 이전 평가액 `amount × current`를 `balance`로 변환합니다. 이후에는 현재 잔액을 직접 입력합니다. 월 납입액은 별도 자금흐름 정보입니다.

JSON은 전체 상태, Excel은 자산 표와 복원 메타데이터를 포함합니다. `v08백업` 또는 기존 `v07백업` 시트는 수정하지 마세요. 다른 기기에 Excel을 가져올 때도 백업에 기록된 stable risk ID와 사용자 이름, 순서를 기준으로 복원합니다. 개인 JSON/Excel은 public GitHub에 올리지 마세요.

## 테스트 배포와 휴대폰 설치

이번 검증에서는 **어떤 Worker에도 배포하지 않았습니다**. 추후 테스트 배포를 승인한 경우 Cloudflare 인증 후 `npm run deploy`를 실행하면 현재 설정의 `my-asset-hub-v08-test`에 배포됩니다. UI와 Market API는 같은 Worker 주소를 사용합니다.

- Android: 테스트 HTTPS 주소를 Chrome에서 열고 메뉴 → 앱 설치 또는 홈 화면에 추가.
- iPhone: 테스트 HTTPS 주소를 Safari에서 열고 공유 → 홈 화면에 추가 → 웹 앱으로 열기.
- 테스트와 운영 주소의 로컬 저장소는 다릅니다. 필요하면 JSON/Excel로 백업·복원합니다.
- 배포 후 `/api/health`와 하단 버전/build가 같은지 확인합니다. 물리 기기 설치는 별도 검증이 필요합니다.

## 향후 main 승격 절차

1. 사용자의 main 병합 및 운영 배포 승인을 받습니다.
2. 테스트 결과와 최종 feature SHA를 확인합니다.
3. **운영 승격 변경에서만** `wrangler.jsonc`의 Worker 이름을 `my-asset-hub`로 변경합니다. 운영 버전/build와 메타데이터도 함께 맞춥니다.
4. 검사를 다시 통과한 후 승인된 변경을 main에 반영합니다. 운영 배포는 별도 승인된 단계로 수행합니다.

feature 브랜치에서 `--name my-asset-hub`로 이름을 덮어써 배포하지 마세요.

## 버전 업데이트

`python scripts/version.py 0.8.0-beta.3 YYYYMMDD-beta-03`을 실행하면 app, Worker, package/lock, manifest, footer 및 service-worker cache를 함께 갱신합니다. `npm test`가 `/api/health` 응답과 메타데이터 일치를 검사합니다.
