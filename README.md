# My Asset Hub · v0.8.0 사용자 테스트

Build: `20260928-prod-01`  
Branch: `main` 승격 후보  
Worker: **`my-asset-hub`**

v0.8.0-beta.2 독립 검증판을 실제 휴대폰 사용자 테스트용으로 승격한 빌드입니다. 금융기관 연결, 실제 주문 전송, 사용자 자산의 서버 수집은 하지 않습니다. 자산 데이터는 브라우저 로컬 저장소와 사용자가 만든 JSON/Excel 백업에만 저장됩니다.

## 검증 상태

승격 전 feature 빌드에서 Worker/API/metadata, v0.7 회귀, v0.8 회귀, 유동자산 재원, 실제 터치 드래그, 월 투자, 전체 리밸런싱, JSON/Excel 복원 및 실제 공개 시세/환율 호출을 포함해 93개 시나리오가 PASS했습니다. 상세 근거는 `TEST_REPORT.md`와 `test-evidence/beta2/`에 보존되어 있습니다.

아직 별도로 확인해야 하는 항목은 실제 Android/iPhone 홈 화면 설치, OS별 standalone 동작, 그리고 배포 후 `/api/health`와 설치된 PWA의 build 일치입니다.

## v0.8 핵심 변경

- 모든 원화 입력의 실시간 천 단위 콤마
- 현금·은행 자산 통합 및 현재 잔액 직접 입력
- 유동/고정 자산 분류
- 월급 및 정기납입 자동 반영, 월별 중복 방지와 undo
- 투자자산/은행/현금의 모바일 drag & drop 및 위험군 이동 확인
- 리밸런싱을 `월 투자` / `전체 리밸런싱`으로 분리
- 전체 리밸런싱의 수량 유지와 간소화 Action Plan
- UI 비중 소수점 1자리
- 고정자산은 금액을 유지하되 전체 비중 계산에는 포함
- 유동 현금성 자산을 월 투자/리밸런싱 재원으로 사용

## 유동자산 투자 재원 정책

유동 현금성 잔액은 `cash.amount`와 `liquidityType='liquid'`인 은행자산 balance의 합계입니다. `fixed` 자산은 자산가치와 리스크 비중에는 포함하지만 투자 재원에서는 제외합니다.

실제 매수 금액은 현금부터 차감하고, 이후 유동 은행자산을 `displayOrder` 순으로 사용합니다. 최소 현금 설정은 전체 유동 현금성 자산 기준으로 유지합니다. 월 투자는 기존 투자자산을 매도하지 않습니다.

## 저장과 마이그레이션

schema는 4이고 저장 키는 `my-asset-hub-beta-v4`입니다. v0.7의 `my-asset-hub-beta-v3` 및 초기 `my-asset-hub-html-v1`을 읽어 v0.8 형식으로 이전합니다.

기존 키는 삭제하지 않으며 최초 이행 전 원본을 `-before-migration` 백업에 남깁니다. 이행 실패 시 기존 원본을 덮어쓰지 않습니다. v0.7 직전 main은 `backup/pre-v0.8-20260928` 브랜치에도 보존되어 있습니다.

## 개발 검증

```sh
npm ci
npm run check
npm test
npx playwright install chromium
npm run test:browser
npm run test:live
```

배포 후 화면의 `TEST · v0.8.0 · build 20260928-prod-01`과 `/api/health`의 version/build가 일치하는지 확인합니다.

개인 JSON·Excel·스크린샷은 public GitHub에 올리지 마세요.
