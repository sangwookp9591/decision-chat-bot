# 디자인 시스템 — 토스(TDS) 기반, 브랜드 컬러 유지

앱 전체의 회색 체계·배경·글꼴·타이포 위계·모서리·간격·버튼/입력/카드/리스트/토스트/스켈레톤·모션을 토스 디자인 시스템(TDS) 방식으로 맞춘 기반이다. **브랜드 컬러(주황 `#F15921`, 틸 `#0E7C86`)와 주황 위 글자색 `#1B1712` 규칙은 그대로**다. 화면(`pages/**`)은 수정하지 않았고, **토큰 이름은 유지한 채 값과 공용 스타일만** 바꿔 화면들이 자동으로 따라오게 했다.

| 파일 | 역할 |
|---|---|
| `frontend/src/styles/tokens.css` | 색·글꼴·타이포·반경·간격·그림자·모션 토큰, 다크 값 |
| `frontend/src/styles/motion.css` | 키프레임, 진입·stagger·누름·스켈레톤 클래스, reduced-motion |
| `frontend/src/style.css` | 전역(글꼴 번들 import)·앱 셸·로그인·오버플로 규칙 |
| `frontend/src/components/{index.tsx,ui.css,fields.css}` | 공용 구성요소(Button·Tabs·Modal·Drawer·Toast·표·배지·필드) 스타일과 모션 |
| `frontend/src/lib/motion.ts` | 모션 유틸·훅(`useStaggerIn`, `useCountUp`, `CountUp`, `PressScale`, `useReducedMotion`, `armRouteMotion`) |
| `frontend/src/styles/tokens.test.ts` | 토큰 대비(AA)·브랜드 고정값을 시험으로 고정 |

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

- 반경: `--radius-xs` 6, `--radius-md`·`--radius-control` 12, `--radius-card` 16, `--radius-xl` 20(큰 카드·시트), `--radius-pill`. 간격은 4px 격자 `--space-1…10`, 섹션 `--section-gap` 28px.
- 카드는 **테두리 대신 면 대비**(회색 바탕 위 흰 카드) + `--shadow-card`(거의 없는 옅은 그림자). 팝업은 `--shadow-pop`, 토스트는 `--shadow-toast`.

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

TDS dark 값을 `tokens.css`에 정의했다(역할 토큰 전체: 회색·바탕·카드·상태색·브랜드 글자색). **지금은 선택 적용**이다.

- `<html data-theme="dark">`: 강제 다크. `<html data-theme="auto">`: OS 설정(`prefers-color-scheme`)을 따른다.
- 기본(속성 없음)은 라이트다. **OS 설정을 자동으로 따르지 않게 한 이유**: 화면 CSS에 `#fff` 같은 라이트 고정 색이 아래 목록만큼 남아 있어, 지금 자동으로 켜면 흰 카드 위에 흰 글자가 놓이는 화면이 생긴다. 화면별 하드코딩이 토큰으로 바뀐 뒤 `index.html`의 `<html>`에 `data-theme="auto"`만 추가하면 켜진다.
- 판단 맵의 고정 다크 무대는 예외(UX-MAP 담당).
- 다크 값의 대비도 `tokens.test.ts`가 AA로 검사한다. 브랜드 틸은 바꾸지 않았으므로 다크 면 위 틸 글자는 약 3:1 — 틸을 글자로 쓰는 곳이 생기면 별도 밝은 틸 토큰이 필요하다.

## 접근성 대비 (시험으로 고정)

`tokens.test.ts`가 라이트·다크의 글자 쌍을 AA 4.5:1로 검사한다: 제목·본문·보조 글자 × 카드·바탕·조용한 면·채움, 주황 글자 × 카드·바탕·tint, 상태 글자 × 배경, **`#1B1712` × `#F15921`**. 브랜드 색 고정값(`#F15921`, `#0E7C86`, `#1B1712`)과 TDS 회색(ground·line·ink)도 고정한다. 알려진 한계: 입력 채움(grey100)과 흰 카드의 경계는 WCAG 1.4.11(비텍스트 3:1)에 못 미친다 — TDS 방식을 따르되 포커스 링(2px)·오류 테두리로 상태를 드러낸다. 틸 `#0E7C86`는 회색 바탕 위 글자 4.49:1(틸을 글자로 쓰지 않는다, 배경 채움+흰 글자 4.95:1로만).

## 번들 크기 (전후)

`vite build`, 같은 화면 코드 기준(전: 이 단계 파일을 HEAD 값으로 되돌린 사본).

| | 전 | 후 |
|---|---|---|
| 초기 JS `index-*.js` | 229,739 B (gzip 75,150) | 230,254 B (gzip 75,317) |
| 초기 CSS `index-*.css` | 25,368 B (gzip 6,080) | 82,414 B (gzip 23,080) |
| 글꼴 | IBM Plex를 Google Fonts CDN에서 | Pretendard Variable dynamic-subset 92조각(woff2, 합 3.0MB)을 번들. 화면에 쓰인 글자의 조각만 내려받음 |

CSS 증가분(+~17KB gzip)은 거의 전부 Pretendard의 `@font-face` 92개(unicode-range)다. 가장 자주 쓰는 3조각(91·90·89, 약 38+21+22KB)은 `index.html`에서 `preload`(빌드 때 해시 경로로 치환)해 첫 글자 그리기를 앞당긴다. 줄이고 싶으면 드문 한글 조각(번호가 낮은 쪽)의 `@font-face`를 빼면 되지만, 그 글자는 시스템 한글 글꼴로 대체된다.

## 화면 하드코딩 목록 (다음 단계에서 화면별 정리)

화면 파일에 남은 직접 색·글꼴·반경. 따뜻한 회색 계열(`#E6E1DA` `#D3CCC2` `#F1ECE6` `#4A433B` `#625B52` `#6B6259` `#FBFAF8` `#EFECE7` …)은 새 차가운 회색과 어울리지 않으니 우선 바꾼다.

| 파일 | 하드코딩 색(건) | 고유 색 | 글꼴 직접 지정 | 상위 색 | 고정 반경 |
|---|---:|---:|---:|---|---|
| `pages/learning/learning.css` | 58 | 20 | 0 | #0E7C86×8, #FFF×7, #4A433B×7, #E6E1DA×6, #0B5E66×4, #6B6259×4 | 4px, 7px, 8px, 10px, 12px, 14px, 999px |
| `pages/main/main.css` | 52 | 27 | 0 | #FFF×8, #0E7C86×4, #F7F3FC×3, #4A2A9A×3, #0A5A62×3, #FFF7E6×3 | 4px, 6px, 7px, 8px, 10px, 12px, 14px, 999px |
| `pages/judgment-map/judgment-map.css` | 51 | 24 | 0 | #FFF×13, #F1ECE6×5, #E7F3F4×3, #0B5E66×3, #14161C×2, #FF7A7A×2 | 4px, 6px, 7px, 8px, 10px, 12px, 14px, 999px |
| `pages/observatory/observatory.css` | 27 | 15 | 0 | #FFF×6, #625950×4, #D3CCC2×3, #0E7C86×2, #DDD5CB×2, #28231F×1 | 8px, 12px, 14px |
| `pages/monitoring/monitoring.css` | 26 | 17 | 0 | #625B52×5, #E6E1DA×4, #FFF×2, #EFECE7×2, #1B1712×1, #D3CCC2×1 | 6px, 7px, 8px, 9px, 10px, 12px, 99px |
| `pages/policy/policy.css` | 20 | 12 | 0 | #625B52×3, #D3CCC2×2, #FBFAF8×2, #E6E1DA×2, #F0D9A8×2, #FFF7E6×2 | 7px, 8px, 10px, 12px |
| `pages/review/review.css` | 6 | 6 | 0 | #FFF×1, #F8F6F3×1, #0E7C86×1, #F4F0FD×1, #B42318×1, #FDF0EE×1 | 8px, 10px, 12px |
| `pages/tasks/tasks.css` | 3 | 3 | 0 | #FFF×1, #F0D9A8×1, #FFF7E6×1 | 10px, 12px, 14px |
| `components/EvidenceViewer.css` | 1 | 1 | 0 | #F1ECE6×1 | 8px, 10px |
| `pages/evaluation/evaluation.css` | 1 | 1 | 0 | #FFF×1 | 5px, 6px, 8px, 10px, 12px, 999px |

전체 상위 색: `#FFF`×39, `#0E7C86`×15, `#E6E1DA`×13, `#D3CCC2`×9, `#F1ECE6`×8, `#4A433B`×8, `#B42318`×8, `#625B52`×8, `#0B5E66`×7, `#FFF7E6`×7, `#4A2A9A`×5, `#6B6259`×5, `#F0D9A8`×5, `#F4F0FD`×4
합계 245 건 / 75 종

### 변환 안내 (화면 정리 시)

| 하드코딩 | 토큰 |
|---|---|
| `#fff` | `var(--color-surface)` |
| `#E6E1DA` `#DDD5CB` | `var(--color-line)` |
| `#D3CCC2` `#B5ACA1` | `var(--color-line-strong)` |
| `#F1ECE6` `#EFECE7` `#F8F6F3` | `var(--color-fill)` |
| `#FBFAF8` | `var(--color-surface-2)` |
| `#1B1712` `#14161C`(고정 다크 무대 제외) | `var(--color-ink)` |
| `#4A433B` `#625B52` `#625950` | `var(--color-ink-2)` 또는 `var(--color-caption)` |
| `#6B6259` | `var(--color-caption)` |
| `#B42318` `#FDF0EE` | `var(--status-fail)` `var(--status-fail-bg)` |
| `#FFF7E6` `#F0D9A8` | `var(--status-warn-bg)` · 경계는 `var(--color-line)` |
| `#F4F0FD` `#4A2A9A` | `var(--status-review-bg)` `var(--status-review-text)` |
| `#0E7C86` `#0B5E66` | `var(--color-secondary)` (진한 틸은 hover 전용 토큰 추가 검토) |
| `border-radius: 7/8/10/14px` | `var(--radius-xs|md|card|xl)` |

## 검증

- `npm run typecheck`, `npm run test`(3회 연속), `npm run build`: 보고서 참조.
- 접근성: `npx playwright test --config=playwright.a11y.config.ts --workers=1`(`A11Y_SHOT_DIR`로 t23 PNG 보호), Chromium·WebKit 모두 통과.
- 전후 화면: `artifacts/review/toss-design/{before,after}/<화면>-{1440,375}.png`(로그인·요청 접수·검토·업무·실행 관찰·판단 맵·규칙 학습·모니터링·정책). 전은 이 단계 파일만 HEAD 값으로 되돌린 사본(화면 코드는 동일)이다.
