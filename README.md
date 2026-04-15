# JNU × Upstage Skillthon

> **전남대학교 소프트웨어중심대학 × 업스테이지**
> 2026 교내 디지털 경진대회 (SW부문)

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Powered by Upstage](https://img.shields.io/badge/Powered%20by-Upstage%20Solar-blue)](https://upstage.ai)
[![Claude Code](https://img.shields.io/badge/Built%20with-Claude%20Code-orange)](https://claude.ai/code)

---

## 목차

- [JNU × Upstage Skillthon](#jnu--upstage-skillthon)
  - [목차](#목차)
  - [Skillthon이란?](#skillthon이란)
  - [크레딧 지원 — $70 무료 제공](#크레딧-지원--70-무료-제공)
    - [크레딧 받는 방법](#크레딧-받는-방법)
  - [사전 요구사항](#사전-요구사항)
  - [시작하는 방법](#시작하는-방법)
    - [1단계 — Repo Fork](#1단계--repo-fork)
    - [2단계 — Clone \& 열기](#2단계--clone--열기)
    - [3단계 — skill-creator 설치](#3단계--skill-creator-설치)
    - [4단계 — Skill 만들기](#4단계--skill-만들기)
  - [제출 구성](#제출-구성)
  - [References](#references)
  - [문의](#문의)

---

## Skillthon이란?

**하나의 Skill을 만드는 대회**입니다.

> **Skills for Your Daily Life** — 일상의 문제를 해결하는 AI Agent용 모듈을 만듭니다.

Skill은 AI Agent가 필요할 때 꺼내 쓰는 **단일 목적 도구**입니다. 사람이 직접 호출하지 않아도, Agent가 상황을 판단해 스스로 Skill을 선택·실행합니다.

## 크레딧 지원 — $70 무료 제공

대회 참가자 전원에게 **Upstage API 크레딧 $70**을 무료로 지원합니다.

### 크레딧 받는 방법

1. **[console.upstage.ai](https://console.upstage.ai)** 에 회원가입 / 로그인
2. 상단 **Dashboard** 탭 클릭
3. 좌측 메뉴 **Billing → Credit** 클릭
4. 우측 **Redeem code** 버튼 클릭

![Upstage 크레딧 리딤 방법](assets/referral_code.jpg)

5. 아래 코드 입력 후 확인

```
UPWAVE-KOH
```

> **$70 크레딧이 즉시 적립됩니다.**

---

## 사전 요구사항

| 도구 | 버전 | 용도 |
|------|------|------|
| [Claude Code](https://claude.ai/code) | 최신 | Skill 개발 환경 |
| Git | — | Fork & Clone |
| Upstage API 키 | — | [위 크레딧 지원](#크레딧-지원--70-무료-제공)으로 발급 |

---

## 시작하는 방법

> **이 가이드는 [Claude Code](https://claude.ai/code) 기준으로 작성되었습니다.**

### 1단계 — Repo Fork

GitHub 우측 상단 **Fork** 버튼 클릭

### 2단계 — Clone & 열기

```bash
git clone https://github.com/[내-username]/JNU-Upstage-Skillthon
cd JNU-Upstage-Skillthon
claude .
```

### 3단계 — skill-creator 설치

**방법 A — 마켓플레이스로 설치** (권장)

Claude Code 내에서 실행:

```
/plugin marketplace add gobeumsu/JNU-Upstage-Skillthon
/plugin install skill-creator@solar-skill-creator
```

**방법 B — 로컬 직접 로드**

```bash
claude skills add skills/skill-creator
```

> 설치 확인: Claude Code 내에서 `/skills` 실행 → `skill-creator` 목록에 표시

### 4단계 — Skill 만들기

Claude Code 프롬프트에 아래와 같이 입력하세요.  
**Upstage API 키 설정 등 모든 초기 설정을 skill-creator가 안내합니다.**

```
> 내 주변의 버터떡을 파는 곳을 가져오는 스킬을 만들고 싶어요
```

skill-creator가 순서대로 안내하는 항목:
1. Upstage API 키 입력 및 `.env` 설정
2. 만들 스킬 아이디어 인터뷰
3. 스킬 코드 생성 및 테스트
4. 제출용 파일 구조 완성

완성된 스킬 디렉토리가 repo 루트에 생성됩니다.

---

## 제출 구성

Fork된 repo의 `skills/` 아래에 **Anthropic 표준 Skill 포맷**으로 스킬을 추가합니다:

```
JNU-Upstage-Skillthon/
└── skills/
    ├── [내-스킬-이름]/
    │   ├── SKILL.md              # 필수: name·description + 스킬 지침
    │   ├── scripts/              # 선택: 실행 코드 (Upstage API 호출 등)
    │   ├── references/           # 선택: 참조 문서
    │   └── assets/               # 선택: 템플릿·파일 등
    └── skill-creator/            # 수정 금지
```

**SKILL.md 필수 frontmatter:**

```yaml
---
name: my-skill-name
description: 이 스킬이 하는 일과 언제 사용해야 하는지. (WHAT + WHEN)
---
```

**제출 전 체크리스트:**

- [ ] `SKILL.md`에 `name`과 `description`이 작성됨
- [ ] Claude Code에서 스킬이 정상 동작함
- [ ] `.env` 파일이 커밋되지 않음 (API 키 노출 방지)


## References

| 문서 | 설명 |
|------|------|
| [solar-skill-creator Marketplace](https://github.com/gobeumsu/JNU-Upstage-Skillthon) | 이 repo — `solar-skill-creator` 마켓플레이스 |
| [Claude Code Docs](https://docs.anthropic.com/en/docs/claude-code/) | Claude Code 공식 문서 (Skills, Plugins, Marketplace) |
| [Upstage Console Docs](https://console.upstage.ai/docs) | Solar LLM, Embeddings, Document Parse API 레퍼런스 |

---

## 문의

- **담당:** 조아라 연구원 / 고범수
- **전화:** 062-530-5364 / 010-4012-1143
- **이메일:** [rha852@jnu.ac.kr](mailto:rha852@jnu.ac.kr) / [gobeumsu@gmail.com](mailto:gobeumsu@gmail.com)
