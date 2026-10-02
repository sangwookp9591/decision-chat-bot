# 일동이 챗봇 애니메이션·이모지

Higgsfield에서 첨부 마스코트를 참조해 이미지 2장과 영상 2개를 생성했습니다.
실제 계정 잔액 차이: 282.74 → 263.74, 총 19크레딧. 30크레딧 한도 이내입니다.

## 파일

- `wave.webm`, `wave.webp`: 작은 손인사, 고개 움직임, 눈깜빡임.
- `idle.webm`, `idle.webp`: 대기 중 미소와 눈깜빡임.
- `mascot.png`: 투명 배경 정지 마스코트, 512×512.
- `icons/`: hello(인사), love(하트), like(좋아요), thinking(생각 중), surprised(놀람), cheer(응원).
- 각 아이콘은 256×256 PNG·WebP와 64×64·128×128 PNG를 제공합니다.
- `icons-preview.png`는 확인용 배경이 있는 모음 이미지입니다. 실제 아이콘은 투명합니다.

## 애니메이션 사양

WebM: 512×512, VP9 알파 채널, 20fps, 무음.
Animated WebP: 384×384, 20fps, 무한 반복.
5초 생성 영상을 정방향·역방향으로 연결해 이음새가 튀지 않는 10초 반복으로 만들었습니다.
녹색 배경을 실제 알파 채널로 변환했고 가장자리의 녹색 번짐을 줄였습니다.

## 챗봇에 사용

가장 간단한 적용:

```html
<img src="/assets/ildong/idle.webp" width="160" height="160" alt="일동이" />
<img src="/assets/ildong/icons/love.png" width="64" height="64" alt="하트" />
```

WebM 사용:

```html
<video autoplay loop muted playsinline width="160" height="160" aria-label="일동이">
  <source src="/assets/ildong/idle.webm" type="video/webm" />
</video>
```

실제 서비스의 대상 브라우저에서 WebM 투명 재생을 확인하고, 필요하면 Animated WebP를 사용하세요.
움직임 줄이기 설정을 적용한 사용자는 `mascot.png`로 대체하세요.

## 확인한 내용

- 두 WebM을 VP9 디코더로 다시 읽어 배경 알파 0·캐릭터 알파 255 확인.
- 두 WebP의 200프레임·무한 반복·투명 배경·프레임 간 실제 변화 확인.
- 모든 아이콘 PNG의 투명 픽셀·불투명 픽셀 확인.
- 영상 시작·중간·끝 프레임을 어두운 배경에 합성해 육안 확인.
- 실제 챗봇 서비스 연결 및 대상 브라우저 검증은 포함하지 않습니다.

생성 마스코트는 첨부 이미지와 유사하게 재현한 결과물로, 원본 3D 모델의 정확한 리깅 파일은 아닙니다.
