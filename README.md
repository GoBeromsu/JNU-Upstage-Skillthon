# 🛡️ 전남대 클린알바맵 (Clean Alba Map)

> **Upstage Solar AI 기반 법적 리스크 차단 및 투명한 알바 환경 검증 플랫폼**

전남대 주요 상권의 아르바이트 근무 환경 데이터를 **Upstage Solar Pro LLM** 기반 AI 스킬로 분석하여, 감정적 리뷰의 **법적 순화**와 **근로계약서 자동 검증**을 통해 사용자에게 발생할 수 있는 법적 리스크를 선제적으로 차단하고, 대학생 구직자들이 건강한 고용 환경을 선택할 수 있도록 지원합니다.

[![Powered by Upstage](https://img.shields.io/badge/Powered%20by-Upstage%20Solar-blue)](https://upstage.ai)
[![Built with Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-orange)](https://claude.ai/code)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

🔗 **배포 주소:** [https://jnu-upstage-skillthon-production.up.railway.app](https://jnu-upstage-skillthon-production.up.railway.app)

---

## 👥 팀 소개: 조오타

| 이름 | 역할 |
|---|---|
| 오영서 (팀장) | AI Skill Engineering, Back-end |
| 성다은 | AI Skill Engineering, Front-end |
| 조아라 | AI Skill Engineering, PM |

---

## 🌟 서비스 핵심 가치

1. **법적 리스크 차단** — LLM 기반 필터링 및 순화로 명예훼손 소지 표현을 사전에 제거하여 작성자와 플랫폼을 보호합니다.
2. **신뢰도 높은 정보** — 관리자의 근로 인증 자료(계약서, 입금 내역 등) 검수를 거친 실제 후기만 수집합니다.
3. **정량적 클린지수** — 8가지 근로기준법 항목을 점수화하여 지도 위에 컬러 핀(🟢/🟡/🟠/🔴)으로 시각화합니다.

---

## 🛠️ AI Skill 구성

| 스킬 | 역할 | 사용 API |
|---|---|---|
| `review-purify-skill` | 후기 작성 시 명예훼손·욕설 등 법적 리스크 표현 탐지 및 3가지 순화 버전 제안 | Upstage Solar LLM |
| `contract-analyzer` | 근로계약서 이미지/PDF 분석 — 17개 필드 추출 및 위반 항목 탐지 | Document Parse + Solar LLM |
| `alba-recommender` | 자연어 의도 분류(SEARCH/RECOMMEND) 기반 클린지수 맞춤 알바 추천 | Upstage Solar LLM |

---

## 🔄 전체 시스템 흐름

```
[알바생]
   │
   ├─① 근로계약서 업로드
   │      ↓
   │   contract-analyzer
   │   (Document Parse → Solar LLM)
   │   → 17개 필드 추출 · 위반 항목 · 리스크 등급 반환
   │
   ├─② 근무 후기 작성 (주관식 텍스트)
   │      ↓
   │   review-purify-skill
   │   (Solar LLM — 명예훼손·욕설 탐지)
   │   → 3가지 순화 버전 제안 → 사용자 선택 → 제출
   │
   └─③ O/X 체크리스트 제출 (8개 객관 항목)
          ↓
       alba-recommender / add_review.py
       (LLM 없음 — 단순 산수로 클린지수 동적 산출)
          ↓
       data/{업체id}.json  누적 저장
          ↓
       alba-recommender / recommend.py
       (Solar LLM — 의도 분류 → SEARCH / RECOMMEND)
       → 클린지수 기반 맞춤 알바 추천
```

---

## 📊 클린지수 산출 공식

사용자가 근무 후 직접 체크한 **8개 항목의 O/X 데이터**만으로 산출합니다. AI가 텍스트를 읽고 추론하지 않습니다.

$$\text{CleanScore} = 100 - \sum_{i=1}^{8} \left(\frac{\text{위반 건수}_i}{\text{전체 리뷰 수}} \times 12.5\right)$$

| # | 위반 항목 |
|---|---|
| 1 | 근로계약서 미작성 |
| 2 | 최저시급 미준수 |
| 3 | 주휴수당 미지급 |
| 4 | 휴게시간 부족 |
| 5 | 급여 지급 지연 |
| 6 | 사전 협의 없는 스케줄 변경 |
| 7 | 반복적이고 지속적인 대타 요구 및 강요 |
| 8 | 초과근무 급여 미지급 |

---

## 🏗️ 기술 스택

| 구분 | 내용 |
|---|---|
| Front-end | React.js, 카카오맵 API |
| Back-end | Node.js (Express), PostgreSQL |
| AI Skill | Python 3.11, Upstage Solar (`solar-pro3`), Document Parse API, JSON Schema (`strict: true`) |
| Infra | Vercel, Railway, GitHub |

---

## 📂 레포 구조

```
JNU-Upstage-Skillthon/
├── skills/
│   ├── review-purify-skill/       # [Skill 1] 알바 후기 법적 순화
│   │   ├── SKILL.md
│   │   ├── scripts/purify.py
│   │   └── assets/
│   ├── contract-analyzer/         # [Skill 2] 근로계약서 자동 검증
│   │   ├── SKILL.md
│   │   ├── scripts/analyze_contract.py
│   │   └── assets/
│   └── alba-recommender/          # [Skill 3] 지능형 알바 추천
│       ├── SKILL.md
│       ├── scripts/
│       │   ├── recommend.py       # 검색·추천 (Solar LLM 의도 분류)
│       │   └── add_review.py      # 리뷰 등록 및 클린지수 갱신
│       └── data/                  # {business_id}.json 누적 데이터
└── README.md
```

---

## 🚀 빠른 시작

### 환경 변수 설정

각 스킬의 `assets/.env.example`을 참고하여 `.env` 파일을 생성한다.

```bash
UPSTAGE_API_KEY=your_api_key_here
```

### 스킬별 실행 예시

**① 근로계약서 분석**
```bash
cd skills/contract-analyzer
python scripts/analyze_contract.py ./assets/recent_contract.png
```

**② 후기 순화**
```bash
cd skills/review-purify-skill
python scripts/purify.py "사장 성질 더럽고 월급도 맨날 늦게 줌"
```

**③ 리뷰 등록 (O/X 체크 데이터 제출)**
```bash
cd skills/alba-recommender
echo '{
  "name": "카페 봄봄", "area": "예대", "industry": "카페",
  "criteria_flags": {
    "근로계약서 미작성": false, "최저시급 미준수": false,
    "주휴수당 미지급": false, "휴게시간 부족": true,
    "급여 지급 지연": false, "사전 협의 없는 스케줄 변경": false,
    "반복적이고 지속적인 대타 요구 및 강요": false, "초과근무 급여 미지급": false
  },
  "review_text": "쉬는 시간이 부족했어요."
}' | python scripts/add_review.py
```

**④ 알바 추천**
```bash
cd skills/alba-recommender
python scripts/recommend.py "클린지수 높은 상대 카페 알바 추천해줘"
```

---

## 🤖 에이전트 확장: 클린알바 어드바이저

대화형 인터페이스를 통해 **근로기준법 멘토링**과 **맞춤형 알바 매칭**을 통합 제공하는 AI 어드바이저로 확장 예정입니다.
