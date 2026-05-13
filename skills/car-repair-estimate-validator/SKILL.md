---
name: car-repair-estimate-validator
description: >
  자동차 정비 견적서 사진을 분석하여 공임비와 부품비의 적정성을 검증하는 스킬.
  견적서 이미지를 업로드하면 Upstage OCR로 항목을 추출하고, 공임나라 표준 공임비와
  현대모비스 순정 부품가를 기준으로 각 항목의 편차(%)를 계산하여 한국어 리포트를 생성한다.
  사용자가 "견적서 검증해줘", "정비 견적서 확인해줘", "이 견적서 바가지 아닌지 봐줘",
  "정비 비용이 적정한지 알고 싶어", "견적서 사진 분석해줘" 등의 요청을 하거나
  자동차 정비 견적서 이미지를 첨부할 때 이 스킬을 사용하라.
---

# 자동차 정비 견적서 검증 스킬

정비소에서 받은 견적서 사진을 분석하여, 각 항목의 공임비와 부품비가 시장 기준 대비 적정한지 검증하고 구체적인 한국어 리포트를 생성한다.

## 검증 기준
- **공임비**: 공임나라(gongim.com) 표준 공임비
- **부품비**: 현대모비스(mobis-as.com) 순정 부품 정가
- Solar Chat으로 매칭 불가 항목은 AI 가격 추정 (참고용)

## 사용자 인터랙션 플로우

### Step 1: 견적서 이미지 수집
사용자에게 견적서 사진을 요청하라. JPG/PNG만 지원한다.

```
견적서 사진을 첨부해주세요. (JPG/PNG)
여러 페이지면 모든 페이지를 첨부해주세요.
```

### Step 2: 파이프라인 실행
견적서 이미지를 `./scripts/run_pipeline.py`로 분석한다.

```bash
python ./scripts/run_pipeline.py /path/to/estimate.jpg --output /tmp/report.md
```

**다중 페이지인 경우:**
```bash
python ./scripts/run_pipeline.py page1.jpg page2.jpg page3.jpg --output /tmp/report.md
```

### Step 3: 차량 정보 보정 (필요 시)
OCR에서 차량명/연식을 제대로 읽지 못한 경우, 사용자에게 되물어라:

```
견적서에서 차량 정보를 정확히 읽지 못했습니다.
차량 모델과 연식을 알려주시겠어요? (예: "쏘나타 2020", "스포티지 2022")
```

사용자가 답하면 `--vehicle` 옵션으로 다시 실행:
```bash
python ./scripts/run_pipeline.py /path/to/estimate.jpg --vehicle "스포티지 2022" --output /tmp/report.md
```

### Step 4: 리포트 전달
생성된 마크다운 리포트를 사용자에게 보여줘라. 리포트에는 다음이 포함된다:
- 종합 판정 (적정 / 다소 높음 / 높음)
- 공임 비교 테이블 (공임나라 기준)
- 부품 비교 테이블 (모비스 정가 기준)
- Solar Chat 가격 추정 (참고용)
- 항목별 상세 제안
- 종합 제안

### Step 5: 비교불가 항목 웹 검색 (선택)
리포트에 Solar Chat 추정으로만 비교된 항목이 있으면, 에이전트가 웹 검색으로 실제 시장가를 확인하여 보충 설명을 제공하라.

**검색 쿼리 패턴:**
- 공임 항목: `[차량명] [정비항목] 공임비 공임나라 2024`
- 부품 항목: `[부품번호] 현대모비스 가격` 또는 `[부품명] 순정 가격`
- 부품번호 없는 부품: `[차량명] [부품명] 부품 가격 순정`

검색 결과를 리포트 하단에 보충 정보로 추가하라.

### Step 6: 후속 질문 대응
사용자가 특정 항목에 대해 추가 질문하면:
- 해당 항목의 공임나라/모비스 기준가를 다시 설명
- 정비소에 어떻게 문의해야 하는지 구체적으로 안내
- 필요하면 웹 검색으로 최신 시장가 확인

## 에러 상황 처리

### Playwright 미설치
```
모비스 부품가격 조회를 위해 Playwright가 필요합니다.
다음 명령으로 설치해주세요:
  pip install playwright && playwright install chromium
```

### UPSTAGE_API_KEY 미설정
```
Upstage API 키가 설정되지 않았습니다.
1. https://console.upstage.ai 에서 API 키를 발급받으세요.
2. ./assets/.env 파일에 UPSTAGE_API_KEY=your-key 를 추가하세요.
```

### 차량 매칭 실패
차량명이 모비스 모델 목록에 없는 경우:
- 부품번호가 기재된 항목은 번호로 직접 검색 가능 (차량 정보 불필요)
- 부품명 검색은 불가 → Solar Chat 추정으로 대체
- 사용자에게 정확한 차량명+연식 재확인 요청

### 모비스 봇 차단
IP 차단 발생 시:
- 부품번호 검색은 재시도
- 부품명 검색은 스킵 → Solar Chat 추정으로 대체
- 시간이 지나면 자동 복구됨을 안내

## 편차 판정 기준

| 편차 | 판정 | 의미 |
|------|------|------|
| -5% ~ +5% | 🟢 적정 | 시장 기준 범위 내 |
| +5% ~ +15% | 🟡 다소 높음 | 확인 권장 |
| +15% ~ +30% | 🟠 높음 | 정비소 문의 권장 |
| +30% 이상 | 🔴 매우 높음 | 다른 견적 비교 강력 권장 |
| -5% ~ -15% | 🔵 다소 낮음 | 호환 부품 가능성 |
| -15% 이하 | 🔵 낮음 | 재생/호환 부품 또는 묶음 할인 가능성 |

## 기술 스택

- **OCR**: Upstage Information Extract API
- **차량 매칭**: Upstage Solar Chat + 모비스 모델 목록 (JSON 번들링)
- **공임 조회**: 공임나라 AJAX API (requests)
- **부품 조회**: 현대모비스 간단검색 (Playwright stealth)
- **검증 엔진**: 편차 계산 + 매칭 신뢰도 필터 + 한국어 제안 생성
- **리포트**: 마크다운 생성 (API 호출 없음)

## 파일 구조

```
car-repair-estimate-validator/
├── SKILL.md                    # 이 파일
├── scripts/
│   ├── run_pipeline.py         # 전체 파이프라인 진입점
│   ├── parse_estimate_ie.py    # OCR (Information Extract)
│   ├── match_vehicle_model.py  # 차량 모델 매칭
│   ├── smart_lookup.py         # 가격 조회 (Solar Chat + 공임나라 + 모비스)
│   ├── lookup_gongim.py        # 공임나라 API
│   ├── lookup_mobis.py         # 모비스 Playwright
│   ├── enhance_with_synonyms.py # 동의어 사전 보강
│   ├── verify_estimate.py      # 검증 엔진
│   ├── fallback_solar_estimate.py # Solar Chat 가격 추정
│   └── generate_report.py      # 리포트 생성
├── references/
│   ├── parsed-estimate-schema.json       # OCR 데이터 모델
│   ├── parsed-estimate-flat-schema.json  # IE용 플래트 스키마
│   ├── mobis-models.json                 # 모비스 차량 모델 목록
│   ├── standard-repair-times.json        # 표준정비시간 데이터
│   ├── labor-synonyms.json              # 공임 동의어 사전
│   └── parts-synonyms.json             # 부품 동의어 사전
└── assets/
    ├── .env.example            # API 키 템플릿
    └── .env                    # 실제 API 키 (Git 제외)
```
