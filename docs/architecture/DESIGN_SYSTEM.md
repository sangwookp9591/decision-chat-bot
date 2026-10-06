# 디자인 시스템 — 토스(TDS) 기반, 브랜드 컬러 유지

앱 전체의 회색 체계·배경·글꼴·타이포 위계·모서리·간격·버튼/입력/카드/리스트/토스트/스켈레톤·모션을 토스 디자인 시스템(TDS) 방식으로 맞춘 기반이다. **브랜드 컬러(주황 `#F15921`, 틸 `#0E7C86`)와 주황 위 글자색 `#1B1712` 규칙은 그대로**다. 기반 단계에서는 **토큰 이름은 유지한 채 값과 공용 스타일만** 바꿨고, 화면 단계(TOSS-SCREENS)에서 화면별 하드코딩을 토큰으로 바꿔 마감했다(아래 §화면 단계).

| 파일 | 역할 |
|---|---|
| `frontend/src/styles/tokens.css` | 색·글꼴·타이포·반경·간격·그림자·모션 토큰, 다크 값 |
| `frontend/src/styles/motion.css` | 키프레임, 진입·stagger·누름·스켈레톤 클래스, reduced-motion |
| `frontend/src/style.css` | 전역(글꼴 번들 import)·앱 셸·로그인·오버플로 규칙 |
| `frontend/src/components/{index.tsx,ui.css,fields.css}` | 공용 구성요소(Button·Tabs·Modal·Drawer·Toast·표·배지·필드) 스타일과 모션 |
| `frontend/src/lib/motion.ts` | 모션 유틸·훅(`useStaggerIn`, `useCountUp`, `CountUp`, `PressScale`, `useReducedMotion`, `armRouteMotion`) |
| `frontend/src/styles/tokens.test.ts` | 토큰 대비(AA)·브랜드 고정값을 시험으로 고정 |
| `frontend/src/styles/screens-tokens.test.ts` | 화면 CSS에 하드코딩(색·반경·글꼴)이 없음, eyebrow가 영문 대문자가 아님, 다크 자동 추종, stagger 게이트를 고정 |
| `frontend/src/styles/pretendard-subset.css` + `scripts/build-fonts-css.mjs` | 줄인 Pretendard `@font-face`(생성 파일)와 생성 스크립트. `fonts.test.ts`가 검증 |
| `frontend/src/components/ShortId.tsx` | 원시 ID를 짧은 칩으로 보이는 `ShortId`/`shortId()` |

## 근거 (공식, 2026-10-04 확인)

- **색**: TDS Colors `@toss/tds-colors` 0.1.0 — light grey50 `#f9fafb` … grey900 `#191f28`, greyBackground `#f2f4f6`, hairlineBorder `#e5e8eb`, red500 `#f04452`, green500 `#03b26c`, orange500 `#fe9800`; dark grey50 `#202027` … grey900 `#ffffff`, background `#17171c`, greyBackground `#101013`, layeredBackground `#202027`.
- **타이포**: TDS Typography. 공식 프리뷰가 비공개라 정확 값이 아니라 **근사치**(t1 30/40 · t2 26/35 · t3 22/31 · t4 20/29 · t5 17/25.5 · t6 15/22.5 · t7 13/19.5, px/line-height)를 토큰으로 정의했다. 굵기: 제목 700, 소제목 600, 본문 400~500.
- **글꼴**: Toss Product Sans는 공개 라이선스가 아니라 **사용하지 않는다**. 대체로 Pretendard Variable(OFL, npm `pretendard` 자체 호스팅). 시스템 폴백은 `-apple-system, BlinkMacSystemFont, 'Apple SD Gothic Neo', 'Malgun Gothic', sans-serif`. 숫자는 전역 `tabular-nums`, 모노 글꼴은 코드·ID(`code`, `.mono`, `.id-chip`)에만 쓰며 시스템 모노(웹폰트 제거)다.
- **Button**: TDS Button — size small/medium/large/xlarge, variant fill/weak, color primary/dark/danger/light. **Skeleton**: 최종 모양 자리표시 + 은은한 shimmer.

## 토큰

### 색

이름은 이전 팔레트와 같고 값만 TDS 회색으로 옮겼다.

| 토큰 | 값 | 용도 |
|---|---|---|
| `--grey-50…900`, `--grey-opacity-100/200` | TDS 원본 | 원시 회색(직접 쓰기보다 역할 토큰 사용) |
| `--color-ink` | grey900 `#191f28` | 제목 |
| `--color-ink-2` | grey700 `#4e5968` | 본문 |
| `--color-caption` | `#626d7b` | 보조 글자. TDS grey600 `#6b7684`는 greyBackground 위 4.19:1이라 AA 미달 → AA(4.77:1)가 되게 어둡게 조정 |
| `--color-disabled` | grey400 | 비활성·장식 전용(필수 글자 금지) |
| `--color-line` / `--color-line-strong` | grey200 / grey300 | hairline |
| `--color-ground` | greyBackground `#f2f4f6` | 페이지 바탕 |
| `--color-surface` / `--color-surface-2` | `#fff` / grey50 | 카드 / 카드 안 조용한 영역 |
| `--color-fill` / `--color-fill-strong` | grey100 / grey200 | 입력·칩·weak 버튼 채움 |
| `--color-primary` | `#F15921` (유지) | 주요 행동·강조 |
| `--color-on-primary` | `#1B1712` (유지, 5.26:1) | **주황 위 글자** — 흰색 금지 |
| `--color-primary-ink` | `#B33F0E` (유지) | 밝은 면 위 주황 글자·링크 |
| `--color-primary-tint` / `--color-primary-weak` | `#FDF3EE` / 주황 12% | 선택·hover / weak 버튼 |
| `--color-secondary` | `#0E7C86` (유지) | 보조(틸) |
| `--color-on-secondary` | `#fff` | 틸 위 글자(4.95:1), 스위치 손잡이 |
| `--color-secondary-ink` | `#0B5E66` (다크 `#5CC8D0`) | 틸을 **글자·hover**로 쓸 때(AA). 틸 원색을 글자로 쓰지 않는다 |
| `--color-secondary-tint` | `#E7F3F4` (다크 `#12363a`) | 약한 틸 채움(선택된 필터·AI/가설 면) |
| `--color-on-danger` | `#fff` (다크 `#1B1712`) | 위험 채움 위 글자 |

**상태색**은 TDS green·red·orange 계열이다. TDS 원색은 흰 바탕에서 글자 대비가 모자라(green500 2.8:1, red500 3.7:1) **글자·아이콘용은 AA(≥4.5:1)가 되게 어둡게, 채움용은 TDS 원색**으로 나눴다.

| 의미 | 글자·아이콘 | 채움(막대·스위치) | 배경 |
|---|---|---|---|
| 성공 | `--status-success` `#067A4B` | `--status-success-fill` `#03B26C` | `--status-success-bg` |
| 실패 | `--status-fail` `#D01F2C` | `--status-fail-fill` `#F04452` | `--status-fail-bg` |
| 경고 | `--status-warn` `#9A5200` | `--status-warn-fill` `#FE9800` | `--status-warn-bg` |
| 진행(브랜드) | `--color-primary-ink` | `--status-active` | `--status-active-bg` |
| 검토 | `--status-review-text` | `--status-review` | `--status-review-bg` |

경고(주황 계열)와 브랜드 주황이 헷갈리지 않도록 **상태 표시는 항상 아이콘+이름을 함께** 쓴다(`StatusBadge` 유지). 색만으로 의미를 전하지 않는다.

### 타이포

`--t1`~`--t7`은 `font` 단축 값(굵기 크기/행간 글꼴)이다. 이전 이름은 TDS 단계로 이어진다: `--text-title`=t4, `--text-section`=700 15/22.5, `--text-body`=t6, `--text-caption`=t7. 사용: `font: var(--t5);`. 값을 하드코딩하지 말고 토큰을 쓴다. `h1`은 t2(375px 이하 t3), 본문 기본 15px.

### 모서리·간격·그림자

- 반경: `--radius-xs` 6, `--radius-sm` 8, `--radius-md`·`--radius-control` 12, `--radius-card` 16, `--radius-xl` 20(큰 카드·시트), `--radius-pill`. 간격은 4px 격자 `--space-1…10`, 섹션 `--section-gap` 28px.
- 카드는 **테두리 대신 면 대비**(회색 바탕 위 흰 카드) + `--shadow-card`(거의 없는 옅은 그림자). 팝업은 `--shadow-pop`, 토스트는 `--shadow-toast`, 떠 있는 동작 막대·호버 카드는 `--shadow-lift`, 실행 중 단계의 후광은 `--shadow-glow`.

### 모션 토큰

| 토큰 | 값 | 용도 |
|---|---|---|
| `--dur-press` / `--dur-fast` / `--dur-base` / `--dur-slow` | 120 / 160 / 240 / 320ms | 누름 / 색 전환 / 진입 / 시트·서랍 |
| `--ease-spring` | `cubic-bezier(0.2,0.8,0.2,1)` | 탄성 있는 짧은 전환(기본) |
| `--ease-out`, `--ease-in-out` | | 색·불투명도 전환 |
| `--press-scale` 0.97, `--enter-distance` 10px, `--stagger-step` 36ms | | 누름·진입·목록 간격 |

JS 쪽 같은 값은 `MOTION`(`lib/motion.ts`). 두 곳을 같이 바꾼다.

## 구성요소

- **Button**: `size`(small/medium/large/xlarge), `tone`(fill 기본·weak), `color`(primary/dark/danger/light), `loading`, `block`. 기존 `variant`는 호환: primary=fill 주황, secondary=fill 틸(흰 글자), plain=weak light. 기본 크기는 터치 영역 44px 유지(small 36px은 촘촘한 도구 줄에만). 주황 위 글자는 `--color-on-primary`.
  ```tsx
  <Button size="large" block>요청 보내기</Button>
  <Button tone="weak" color="danger" size="small">삭제</Button>
  ```
- **Tabs**: 밑줄 하이라이트가 활성 탭으로 미끄러진다(`.ui-tabs-ind`, 측정이 안 되면 활성 탭 자체 밑줄로 폴백).
- **Modal / Drawer**: 모달은 pop(scale .96→1), 375px 이하는 아래 시트(slide-up), 서랍은 오른쪽에서 슬라이드. 배경 fade.
- **Toast**: 하단 중앙 어두운 pill, 아래에서 올라오며 등장.
- **입력(`fields.css`)**: 회색 채움(`--color-fill`), 포커스 시 흰 면+브랜드 테두리+2px 포커스 링, 오류는 `--status-fail` 테두리+배경. 칩·세그먼트는 pill, 스위치는 탄성 이동.
- **표·상태 패널·필터 막대**: 카드 면, 행 구분선만 hairline, 점선 테두리 제거.
- **StatusBadge**: 테두리 없는 weak 색 pill + 아이콘 + 이름.
- **SkeletonBlock**: `<SkeletonBlock width height circle />`, 공용 shimmer. 화면이 자체 `.skeleton`/`.sk`를 가진 곳은 임시 브리지 규칙(`main :is(.skeleton,.sk)`)으로 같은 모양·속도로 맞춘다 — 화면이 자기 사본을 지우면 브리지도 지운다.

## 모션 사용법 (`lib/motion.ts` + `motion.css`)

| 목적 | 방법 |
|---|---|
| 화면 진입 fade + 10px 위로(240ms) | `main > section`에 **앱 안에서 처음 이동한 뒤부터** 자동. 첫 로드·새로고침은 반투명 프레임 없이 즉시 그린다(첫 페인트·스크린샷·axe 대비 검사가 결정적). 임의 요소는 `className="m-enter"` |
| 목록 stagger(36ms 간격, 최대 10단계) | `const ref = useStaggerIn<HTMLUListElement>([rows])` → `<ul ref={ref}>` 또는 `className="m-stagger"` + `style={staggerStyle(i)}` |
| 누름 scale 0.97 / 카드 0.98 | `.ui-button`·`.fld-chip`·`.id-chip`·탭에 자동. 임의 요소는 `data-press` 또는 `<PressScale>`, 큰 카드는 `m-press-card` |
| 숫자 지표 count-up | `<CountUp value={n} format={...} />` 또는 `useCountUp(n)`. 보조기술에는 최종 값이 읽힌다. 기존 값 표시(`ConfidenceValue` 등)는 단위·e2e 시험이 즉시 값을 읽으므로 자동 적용하지 않았다 — 화면이 필요할 때 도입 |
| 신뢰도 막대 | 0에서 자라는 `m-grow` 자동 |
| 스켈레톤 | `<SkeletonBlock>` 또는 `.ui-skeleton` |

**reduced-motion**: `prefers-reduced-motion: reduce`에서 모든 animation·transition이 즉시 끝나고(`0.001ms`), 스켈레톤·스피너 반복은 멈추며, `useCountUp`은 목표 값을 바로 돌려준다.

**라이브러리**: 추가하지 않았다(CSS 전환·키프레임과 ~70줄 훅으로 충분, framer-motion은 번들 증가 대비 이득 없음).

## 다크 테마

TDS dark 값을 `tokens.css`에 정의했다(역할 토큰 전체: 회색·바탕·카드·상태색·브랜드·틸 글자색). **이제 OS 설정(`prefers-color-scheme: dark`)을 자동으로 따른다.**

- 속성이 없거나 `<html data-theme="auto">`: OS를 따른다. `data-theme="dark"`: 강제 다크. `data-theme="light"`: 강제 라이트(수동 선택 유지). 구현은 `@media (prefers-color-scheme: dark) { :root:not([data-theme='light']) {…} }`이고 값은 `[data-theme='dark']` 블록과 같다(두 블록을 같이 바꾼다).
- `index.html`의 `<meta name="color-scheme" content="light dark">`로 브라우저 기본 위젯(스크롤바·입력)도 따라간다.
- 자동 추종을 켤 수 있었던 이유: 화면 CSS의 하드코딩 색을 모두 토큰으로 바꿨기 때문이다(아래 §화면 단계). `screens-tokens.test.ts`가 화면 CSS에 리터럴 색이 다시 들어오면 실패시킨다.
- **예외: 판단 맵의 고정 다크 무대**(`pages/judgment-map/judgment-map-stage.css`)는 앱 테마와 무관하게 항상 어둡다. 리터럴 색은 이 파일에서만 허용한다.
- 다크 값의 대비도 `tokens.test.ts`가 AA로 검사한다. 브랜드 틸은 바꾸지 않았으므로 다크 면 위 틸 **글자**는 `--color-secondary-ink`(`#5CC8D0`)를 쓴다. 주황 위 글자는 두 테마 모두 `#1B1712`.
- 확인: `artifacts/review/toss-screens/<화면>-{1440,375}-{light,dark}.png`, axe `color-contrast`를 라이트·다크 × Chromium·WebKit × 전 화면으로 돌려 위반 0건.

## 접근성 대비 (시험으로 고정)

`tokens.test.ts`가 라이트·다크의 글자 쌍을 AA 4.5:1로 검사한다: 제목·본문·보조 글자 × 카드·바탕·조용한 면·채움, 주황 글자 × 카드·바탕·tint, 상태 글자 × 배경, **`#1B1712` × `#F15921`**. 브랜드 색 고정값(`#F15921`, `#0E7C86`, `#1B1712`)과 TDS 회색(ground·line·ink)도 고정한다. 알려진 한계: 입력 채움(grey100)과 흰 카드의 경계는 WCAG 1.4.11(비텍스트 3:1)에 못 미친다 — TDS 방식을 따르되 포커스 링(2px)·오류 테두리로 상태를 드러낸다. 틸 `#0E7C86`는 회색 바탕 위 글자 4.49:1(틸을 글자로 쓰지 않는다, 배경 채움+흰 글자 4.95:1로만).

## 번들 크기 (전후)

### 기반 단계(fdf275c)

`vite build`, 같은 화면 코드 기준(전: 이 단계 파일을 HEAD 값으로 되돌린 사본).

| | 전 | 후 |
|---|---|---|
| 초기 JS `index-*.js` | 229,739 B (gzip 75,150) | 230,254 B (gzip 75,317) |
| 초기 CSS `index-*.css` | 25,368 B (gzip 6,080) | 82,414 B (gzip 23,080) |
| 글꼴 | IBM Plex를 Google Fonts CDN에서 | Pretendard Variable dynamic-subset 92조각(woff2, 합 3.0MB)을 번들 |

### 글꼴 줄이기(TOSS-SCREENS)

원인: CSS 증가분(+~17KB gzip)은 거의 전부 Pretendard의 `@font-face` 92개(unicode-range 목록)였다. 92개는 **굵기가 아니라 글자 범위 조각**이다(가변 글꼴 하나가 굵기 45–920을 모두 담는다). 그래서 굵기 400·500·600·700만 쓴다는 사실은 `font-weight` 선언 범위를 `400 700`으로 좁히는 데만 쓰이고, 크기는 **조각 수**를 줄여 얻었다.

방법: `node scripts/build-fonts-css.mjs`가 업스트림 CSS에서 (1) 가장 자주 쓰는 한글·영문 단계 72–91번 20조각, (2) `src/` 안의 모든 비ASCII 글자(기호·화살표·드문 음절)가 들어 있는 조각을 골라 `src/styles/pretendard-subset.css`로 쓴다. **unicode-range 분할은 그대로**라 화면에 쓰인 글자의 조각만 내려받는다. 선택에서 빠진 드문 한글·한자는 시스템 한글 글꼴(Apple SD Gothic Neo 등)로 대체된다. `fonts.test.ts`가 (a) 면 수 ≤ 30, (b) 모든 면이 `font-weight:400 700`, (c) 앱이 줄인 파일을 import, (d) 소스에 나오는 모든 한글 음절이 선택된 조각에 들어 있음, (e) CSS가 400–700 밖 굵기를 쓰지 않음을 고정한다.

| | 전 | 후 |
|---|---|---|
| `@font-face` 개수 | 92 | 25 |
| 글꼴 CSS만 (주석 제외) | 54,561 B (gzip 12,858) | 23,341 B (gzip 6,456) |
| 초기 CSS `index-*.css` 전체 (같은 빌드의 화면 CSS 포함) | 82,467 B (gzip 23,017) | 61,687 B (gzip 16,136) |
| 빌드 산출 woff2 | 92개 (3.0MB) | 25개 (704KB) |

전체 CSS gzip의 남은 차이(6.1→16.1KB)는 글꼴 CSS 6.5KB와 기반 단계에서 추가된 공용 스타일·모션·다크 토큰이다. 가장 자주 쓰는 3조각(91·90·89)은 `index.html`에서 `preload`(빌드 때 해시 경로로 치환).

## 화면 단계 (TOSS-SCREENS)

### 하드코딩 제거 결과

기반 단계 목록(245건/75색)을 화면별로 모두 토큰으로 바꿨다. `main.css`(요청 접수)는 CHAT-POLISH가 같은 방식으로 정리했다.

| 파일 | 전(색 건수) | 후 | 비고 |
|---|---:|---:|---|
| `pages/learning/learning.css` | 58 | 0 | |
| `pages/judgment-map/judgment-map.css` | 51 | 0 | 고정 다크 무대와 계층 팔레트는 `judgment-map-stage.css`로 분리 |
| `pages/observatory/observatory.css` | 27 | 0 | |
| `pages/monitoring/monitoring.css` | 26 | 0 | |
| `pages/policy/policy.css` | 20 | 0 | |
| `pages/review/review.css` | 6 | 0 | |
| `pages/tasks/tasks.css` | 3 | 0 | |
| `components/EvidenceViewer.css` | 1 | 0 | |
| `pages/evaluation/evaluation.css` | 1 | 0 | `#ffffff59` 등 알파 리터럴 4건 추가 정리 |
| `components/ui.css`, `fields.css` | 5 (흰 글자·손잡이·그림자) | 0 | `--color-on-secondary`·`--color-on-danger`·`--shadow-card` (기반 단계 목록 밖 추가 정리) |
| **합계(요청 접수 제외, 무대 제외)** | 목록 193 + 5 | **0** | |

남은 리터럴 색: **`judgment-map-stage.css` 64건(47색)** — 판단 맵의 고정 다크 무대(앱 테마와 무관해야 함). 고정 반경도 화면·공용 CSS에서 0건(`border-radius:Npx` → `--radius-*`), 글꼴 직접 지정 0건(`font-family`는 토큰·`@font-face`만). 간격(`gap`·`padding` px)은 4px 격자 값이라 토큰(`--space-*`)으로 바꾼 곳과 px 그대로인 곳이 섞여 있다 — 값이 격자를 벗어난 곳이 없어 이번에는 강제하지 않았다.

변환 기준(이번 정리에서 쓴 것): 흰 면 → `--color-surface`, 카드 안 조용한 면 → `--color-surface-2`, 채움·칩 → `--color-fill`, 구분선 → `--color-line`, 진한 틸 글자·hover → `--color-secondary-ink`, 약한 틸 → `--color-secondary-tint`, 경고 배너 → `--status-warn-bg`(+ 왼쪽 막대는 `--status-warn-fill`), 검토(보라) → `--status-review-*`, 실패 → `--status-fail*`.

### 마감 규칙(앱 셸·페이지·카드·리스트)

- **앱 셸**: 사이드바는 페이지 바탕과 같은 회색 면(구분선 없음), 활성 항목은 흰 pill(`--color-surface` + `--shadow-card`, 글자 `--color-primary-ink`). 상단바는 48px로 얇게, 테두리·면 없음. 회색 바탕 위 `plain` 버튼은 `--btn-bg: surface` 면을 따로 준다(`style.css`).
- **페이지 머리**: `h1`은 t2(375px 이하 t3), 설명은 `--color-ink-2`. `main > section > header`가 간격·설명 색을 한곳에서 준다.
- **eyebrow**: 영문 대문자(`AI TRIAGE`, `TRACE / PLAYBACK` …)를 없애고 짧은 한국어 라벨(`사람 검토`, `배정 업무`, `운영 지표`, `실행 기록`, `정답 라벨`, `판단 관계`) 또는 제거. 스타일은 caption 색 t7 600(대비 AA). `screens-tokens.test.ts`가 영문 대문자 3자 이상을 막는다.
- **카드**: 큰 반경(`--radius-xl`)·테두리 없음, 회색 바탕 위 흰 면 + `--shadow-card`. 안쪽 조용한 영역은 `--color-surface-2`. 상태 강조는 외곽선 대신 면 색(`--status-*-bg`) + 필요하면 inset 링.
- **리스트 행**: 넉넉한 세로 간격(14px), 호버 시 `--color-fill` 면, 누르면 0.99 scale. 선택된 행은 `--color-primary-tint` + inset 링.
- **원시 ID**: 제목 자리에 `req_…`/`run_…`/`task_…` 전체 길이를 쓰지 않는다. `<ShortId id=… />`는 `req_…bc8acd`처럼 짧게 보이고, **전체 ID는 `title`(호버)과 시각적으로 숨긴 텍스트(`short-id-full`)로 남아** 복사·검색·보조기술·텍스트 비교(`toContainText`)에서 그대로 찾힌다. 검토 대기 목록 행은 `긴급도(제목) + 짧은 ID 칩 + 상태 + 사유`로 바뀌었다. (목록 API에 요청 첫 문장이 없어 제목은 긴급도로 했다 — 첫 문장 마스킹 값은 백엔드가 목록에 담아주면 같은 자리에 넣으면 된다.)

### 모션(화면)

| 목적 | 쓰는 곳 |
|---|---|
| 목록 stagger (`useStaggerIn`) | 검토 대기 목록, 업무 목록, 모니터링 핵심 지표. **앱 안에서 처음 이동한 뒤부터만** 돈다(`:root[data-motion='route'] .m-stagger > *`) — 첫 로드·스크린샷·axe는 반투명 프레임 없음 |
| 카드·행 누름 scale | 목록 행·지표 타일·실행 단계 카드·필터 칩에 `:active` scale(0.97~0.99, `--press-scale`) |
| 숫자 count-up (`CountNumber`) | 모니터링 핵심 지표 8개. 화면 진입 뒤(첫 앱 내 이동 후) 0에서 올라가고, 첫 로드·reduced-motion은 최종 값을 바로 그린다. `CountUp`과 달리 숨은 복제 없이 **텍스트 노드 하나**라 시험·보조기술에서 값이 한 번만 읽힌다 |
| 탭·세그먼트 슬라이드 (`useSlideIndicator` + `.m-seg`) | 실행 관찰 탭, 판단 맵 보기 전환, 평가 라벨 분할 전환. 선택된 자식의 위치·크기를 `--ind-x/y/w/h`로 컨테이너에 알려 하이라이트가 미끄러진다. 측정이 안 되면 각 버튼의 선택 스타일로 폴백 |
| 시트·서랍 | 업무 상세·실행 관찰 상세는 오른쪽 슬라이드(`m-slide-in-right`) |
| 토스트 | 공용 `Toast`(평가 라벨 확정 등). 검토·업무의 알림 문구는 화면 안 `role=status`로 그대로 둔다(시험·접근성 계약) |

### 시각 확인

`artifacts/review/toss-screens/<화면>-{1440,375}-{light,dark}.png` (로그인·검토 대기·검토 상세·업무·업무 상세·실행 관찰·판단 맵(입체·목록)·규칙 학습·모니터링·정책·평가 라벨). 요청 접수(Main)는 CHAT-POLISH 담당이라 제외.

## 검증

- `npm run typecheck`, `npm run test`(3회 연속), `npm run build`: 보고서 참조.
- 접근성: `npx playwright test --config=playwright.a11y.config.ts --workers=1`(`A11Y_SHOT_DIR`로 t23 PNG 보호), Chromium·WebKit 모두 통과.
- 전후 화면: `artifacts/review/toss-design/{before,after}/<화면>-{1440,375}.png`(로그인·요청 접수·검토·업무·실행 관찰·판단 맵·규칙 학습·모니터링·정책). 전은 이 단계 파일만 HEAD 값으로 되돌린 사본(화면 코드는 동일)이다.
- 화면 단계 검증: `npm run typecheck && npm run test && npm run build`, Chromium·WebKit e2e(검토·업무·정책·모니터링·실행 관찰·판단 맵·평가 라벨·screens-ui·responsive-overflow·a11y `--workers=1`), 라이트·다크 axe `color-contrast` 0건.
