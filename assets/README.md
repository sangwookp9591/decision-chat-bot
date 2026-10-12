# 일동이 마스코트 애니메이션·아이콘

사진 기반으로 캐릭터화한 일동이를 Higgsfield로 제작했습니다(`generation-info.json` 참고).

## 파일

- `wave.webp`: 손인사와 밝은 웃음.
- `nod.webp`: 고개 끄덕임과 미소.
- `shy.webp`: 양손을 볼 가까이 올리는 수줍은 웃음.
- `mascot.png`: 투명 정지 이미지. 움직임 줄이기 설정에서 사용.
- `preview.jpg`: 확인용 동작 모음(배경 있음). 실제 WebP는 투명합니다.
- `icons/`: hello·like·thinking·surprised·love·cheer — 위 애니메이션에서 뽑은 256px 투명 정지 프레임.

## 애니메이션 사양

512×512 투명 애니메이션 WebP, 약 5.4~6.0초 무한 반복, 무음.
3초 생성 영상을 정방향·역방향으로 이어 반복 경계의 튐을 줄였습니다.

## 챗봇에 사용

```html
<img src="/assets/mascot/wave.webp" width="160" height="160" alt="" />
```

움직임 줄이기 설정을 적용한 사용자는 `mascot.png`로 대체하세요.
