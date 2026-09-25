# My Asset Hub · v0.6.0

기존 HTML 화면을 유지한 개인 자산관리 PWA입니다. Streamlit 서버가 필요하지 않습니다. `public/`이 앱이고 `worker.js`는 공개 시세·검색 API입니다. 먼저 TEST_REPORT.md의 미검증 항목을 확인하세요. 이번 결과는 배포 후보이며 실제 휴대폰 설치까지 검증한 v1.0 안정판은 아닙니다.

## 1. 기존 자료와 데이터 보호

- 기존 앱에서 JSON 또는 Excel을 먼저 내려받아 개인 폴더에 보관하세요.
- 실제 보유종목·수량·매수단가·은행잔액·백업 파일을 GitHub에 올리지 마세요.
- `public/data/catalog.json`은 공개 종목 목록이며 보유자산 파일이 아닙니다.
- 자산은 해당 기기·브라우저·주소의 localStorage에 저장됩니다. 새 도메인이나 새 설치 앱으로 자동 이동하지 않습니다. 새 앱에서 백업을 가져오세요.
- 브라우저 데이터 삭제, 휴대폰 교체·분실 시 복원이 안 될 수 있습니다. 주기적으로 JSON과 Excel을 내려받으세요.
- 기존 `stocks / savings / config / history` JSON 및 v0.5 Excel을 읽습니다. 가져오기 전 변경 건수를 보여주고 직전 데이터 복구 사본을 보관합니다. 실제 개인 파일은 이번 테스트에 사용하지 않았습니다.
- 깨진 저장 데이터는 자동 초기화하지 않습니다. ‘원본 백업’으로 내려받고 수정 후 다시 가져오세요.

## 2. 폴더 구성

- `public/index.html`: 기존 화면·스타일
- `public/js/app.js`: 자산 계산·저장·화면·Excel
- `public/config.js`: 별도 API 주소(기본은 빈 문자열, 동일 주소)
- `public/manifest.webmanifest`, `public/service-worker.js`, `public/icons/`: PWA
- `public/vendor/`: 오프라인 Excel 모듈
- `public/data/catalog.json`: 국내·미국·ETF·Upbit 공개 검색 목록
- `worker.js`, `wrangler.jsonc`: Cloudflare API 및 정적 파일 배포
- `tests/`: 자동 검증, `scripts/`: 버전·패키징·시장목록 갱신

이 ZIP에는 개인 데이터나 API 키가 없습니다. 아이콘은 기존 초안 것을 유지했습니다.

## 3. GitHub에 올리기

1. ZIP을 풀고 내부 `my-asset-hub` 폴더를 작업 폴더로 사용합니다.
2. 기존 저장소를 GitHub Desktop에서 Clone합니다. 실제 저장소가 제공되지 않아 이번 작업에서 원격 저장소를 변경하지 않았습니다.
3. Branch → New branch에서 `feature/pwa`를 만듭니다. 검증 전 `main`을 덮어쓰지 마세요.
4. 프로젝트 파일을 복사합니다. 예전 Streamlit 파일은 별도로 보존하되 개인 정보나 비밀번호가 들어 있는 원본을 공개 저장소에 복사하지 마세요.
5. 변경 파일에 개인 JSON·Excel·환경변수가 없는지 확인한 다음 Commit → Publish branch 합니다.
6. 미리보기 주소에서 TEST_REPORT의 남은 항목을 확인한 후 PR을 통해 `main`에 반영합니다.

추천 분기: `feature/pwa`, `feature/market-api`, `feature/excel`, `fix/문제명`. ZIP을 매번 올리는 것보다 코드 변경을 Commit하면 수정 이력을 쉽게 되돌릴 수 있습니다.

## 4. 가장 간단한 배포: Cloudflare Worker + Static Assets

UI와 API를 같은 HTTPS 주소에 배포하면 CORS 주소 설정이 필요 없습니다. GitHub는 소스 보관과 업데이트에 사용합니다.

1. Node.js LTS와 GitHub Desktop을 설치하고 Cloudflare 계정을 준비합니다.
2. 터미널에서 `package.json`이 있는 폴더로 이동합니다.
3. 다음 명령으로 의존성과 로컬 앱을 실행합니다.

```sh
npm ci
npm run dev
```

4. 표시된 localhost 주소를 열어 확인합니다. HTML을 파일로 더블클릭하는 방식은 API/PWA 실행 방식이 아닙니다.
5. 배포 전 검사를 실행합니다.

```sh
npm run check
npm test
npx wrangler deploy --dry-run
```

6. `wrangler.jsonc`의 `name`을 본인의 사용 가능한 프로젝트 이름으로 정합니다. 앱에 표시되는 이름과는 별개입니다. `ASSETS`, `run_worker_first: ["/api/*"]` 설정은 유지합니다.
7. 로그인하고 배포합니다.

```sh
npx wrangler login
npm run deploy
```

8. 출력된 `https://...workers.dev` 주소에서 앱을 엽니다. `/api/health`가 JSON으로 응답하는지, 검색·새로고침이 동작하는지 확인합니다.
9. `/api/fx`, `/api/quote?ticker=AAPL&currency=USD`, `/api/search?q=삼성전자`를 확인합니다. API 오류가 나면 앱은 기존 가격을 유지하고 실패를 표시합니다.

**GitHub 자동 배포:** Cloudflare Workers & Pages에서 Git 저장소 연결을 선택하고 이 프로젝트를 연결합니다. 프로젝트 루트를 `package.json` 위치로 지정하고 배포 명령을 `npm run deploy`로 설정합니다. 먼저 테스트 브랜치를 사용하고, 검증 후 운영 브랜치를 `main`으로 지정하세요. 계정 권한·요금제·대시보드 구성에 따라 화면이 다를 수 있습니다. 이번 작업에서는 실제 계정 배포를 수행하지 않았습니다.

참고: [Cloudflare Static Assets](https://developers.cloudflare.com/workers/static-assets/), [GitHub 연동](https://developers.cloudflare.com/workers/ci-cd/builds/git-integration/github-integration/).

## 5. GitHub Pages를 UI 주소로 유지하는 경우

Worker는 위 방법으로 먼저 배포합니다.

1. `public/config.js`의 빈 API 주소를 본인 Worker HTTPS 주소로 바꿉니다. 끝에 `/api`를 붙이지 않습니다.
2. Worker의 `ALLOWED_ORIGIN`에 GitHub Pages의 origin을 입력합니다. 예: `https://사용자명.github.io`이며 `/저장소명` 경로는 제외합니다. 여러 origin은 쉼표로 구분합니다.
3. Worker를 다시 배포합니다.
4. GitHub Pages에서 `public/` 내부 파일을 사이트 루트로 발행합니다. 간단히 별도 `gh-pages` 브랜치 루트에 `public/`의 내용만 복사한 뒤 Settings → Pages에서 그 브랜치를 선택할 수 있습니다. 앱 원본은 작업 브랜치에 유지합니다.
5. HTTPS 적용 후 프로젝트 경로에서도 manifest·아이콘·API가 정상인지 확인합니다. 모든 앱 파일 경로는 상대 경로를 사용합니다.

Pages UI와 Worker의 주소가 다르면 CORS 설정이 필수입니다. API 키가 필요한 소스로 변경할 때에는 `wrangler secret put 이름`으로 Worker에 저장하고 public JS에 넣지 마세요.

## 6. Android / iPhone 설치

배포된 HTTPS 주소를 사용합니다. 이 과정은 실제 기기에서 추가 확인이 필요합니다.

- Android: Chrome으로 앱 열기 → 메뉴 → ‘앱 설치’ 또는 ‘홈 화면에 추가’. 앱의 설치 버튼이 보이면 사용해도 됩니다.
- iPhone: Safari로 앱 열기 → 공유 → ‘홈 화면에 추가’ → 표시되는 경우 ‘웹 앱으로 열기’를 켭니다 → 추가.
- 홈 화면 아이콘을 눌러 My Asset Hub 이름과 아이콘, 주소창 없는 실행을 확인합니다.
- 설치 전후 데이터가 다르면 기존 브라우저에서 JSON 백업 후 설치 앱으로 가져옵니다.
- 최초 온라인 실행 뒤 오프라인에서도 저장 자산과 Excel을 사용할 수 있습니다. 검색·최신 시세는 인터넷이 필요합니다.

[Apple 설치 안내](https://support.apple.com/guide/iphone/iphea86e5236/ios), [Google PWA 안내](https://support.google.com/chromebook/answer/9658361?co=GENIE.Platform%3DAndroid&hl=en).

## 7. 일상 사용 및 Excel 관리

1. 투자자산 추가 → 종목/티커 검색 → 국내·미국·ETF·가상화폐 시장 선택. 미국 종목은 영문명 또는 티커를 입력합니다.
2. 평단·수량·리스크를 입력합니다. 미국 주식은 USD입니다. 매수 당시 환율을 입력하면 원화 원금이 보존됩니다. 생략하면 기존 Streamlit처럼 현재 환율을 원금에도 적용합니다.
3. 동일 티커와 통화로 추가하면 확인 후 수량과 가중평단을 합산합니다. 추가매수의 매수환율도 원금 기준으로 반영합니다.
4. 예금·파킹통장은 금액을 잔액으로, 적금·청약은 금액 × 현재회차로 평가합니다. 이율은 보관하지만 이자·세금은 평가액에 포함하지 않습니다.
5. 리밸런싱은 고정 은행자산을 제외한 목표를 입력하고 종목별 비중을 배분합니다. 합계·그룹 목표가 맞지 않으면 매매 안내를 차단합니다. 실제 주문 기능은 없습니다.
6. ‘엑셀·백업’에서 Excel 내보내기 → Excel 또는 LibreOffice에서 수정 → 가져오기 → 미리보기 확인 → 적용.

Excel은 투자자산·은행자산·설정·자산기록·리스크목표·종목목표 6개 시트입니다. 투자자산에 종목명, 티커, 시장, 매수평단가, 보유수량, 해외여부, 매수환율, 리스크를 포함합니다. 통화(USD/KRW)와 해외여부(TRUE/FALSE)는 일치해야 합니다.

머리글과 기존 ID를 유지하세요. 새 행의 ID는 비워둡니다. 티커는 텍스트 형식으로 저장해 앞자리 0을 유지하세요. 수식은 값으로 붙여넣습니다. 행을 지우면 가져오기 적용 시 해당 자산이 빠지므로 미리보기의 삭제 건수를 확인하세요. 자산 전체 복원에는 JSON이 가장 완전합니다.

시세는 시작 시와 기본 5분마다 자동 조회합니다. 설정에서 15분·30분으로 변경하거나 주기만 끌 수 있습니다. 휴대폰 백그라운드에서는 주기 실행을 보장하지 않습니다. ‘시세 새로고침’과 가격 기준시각을 확인하세요. 조회 실패 시 이전 가격을 유지하며, 현재가가 전혀 없으면 평단을 추정값으로 표시합니다.

## 8. 앱 업데이트

1. JSON 백업 → 테스트 브랜치에서 수정 → `npm run check`, `npm test`.
2. Python이 있는 개발 환경에서 버전을 올립니다. Python은 앱 실행에 필요하지 않습니다.

```sh
python scripts/version.py 0.6.1
```

버그 수정은 patch, 기능 추가는 minor를 올립니다. 화면·manifest·Service Worker 캐시·패키지 버전을 함께 변경합니다. CHANGELOG와 TEST_REPORT도 갱신합니다.
3. 테스트 주소에 배포 → 종목 검색·실제 시세·백업·모바일 확인 → 운영 배포.
4. 기존 앱에서 업데이트 버튼이 나타나면 저장 후 적용합니다. 보이지 않으면 앱을 다시 열어 확인합니다. 데이터 초기화·브라우저 저장소 삭제로 업데이트하지 마세요.
5. 이름·아이콘을 바꾸려면 manifest와 index 표시명, 192/512 PNG를 수정합니다. 기기별 아이콘 갱신에는 재설치가 필요할 수 있으므로 먼저 백업합니다.

## 9. 공개 종목목록 갱신

기본 목록은 2026-09-25에 생성한 17,575개 항목입니다. 모든 상장 상품의 시세 제공을 보장하지 않습니다. 신규 상장·폐지·명칭 변경을 반영하려면 개발 환경에서 갱신합니다.

```sh
python -m pip install finance-datareader requests beautifulsoup4
python scripts/refresh_catalog.py
```

실패한 시장만 재시도: `python scripts/refresh_catalog.py --retry-failed`. 국내 분류만 갱신: `--krx`. 필수 시장이 비면 기존 공개 목록을 보존합니다. 결과의 coverage 오류를 확인하고 `public/data/catalog.json`만 Commit한 뒤 재배포하세요. 원본 소스의 일시 장애로 이전 시장 데이터가 유지될 수 있습니다. 앱에는 Python·FinanceDataReader 서버가 필요하지 않습니다.

## 10. 검증 및 다음 추천 작업

`npm test`는 Worker와 DOM/데이터 계산 테스트입니다. 실제 브라우저 테스트는 다음처럼 별도로 실행합니다.

```sh
npx playwright install chromium
npm run test:browser
npm run test:live
```

`test:live`는 외부 호출이므로 네트워크·제공처 상태에 따라 실패할 수 있습니다. 결과는 `live-results.json`에 저장되며 개인 자산을 전송하지 않습니다.

우선순위: (1) 실제 Cloudflare 배포와 Android/iPhone 확인, (2) 본인 백업으로 이전 확인, (3) 별도 시세 제공처와 장 마감/휴장일 표시, (4) 거래 내역·수수료·배당·이자, (5) 선택적 암호화 동기화. 현재 거래내역 원장·자동 클라우드 동기화·앱 잠금·실제 주문은 구현하지 않았습니다.

업데이트는 GitHub Desktop + Cloudflare Git 자동 배포 조합, 데이터 편집은 Excel/LibreOffice + 앱 가져오기를 권합니다. APK/iOS 패키징은 PWA 실기기 검증 이후 Capacitor로 진행할 수 있지만 이번 버전 범위에는 포함하지 않았습니다.
