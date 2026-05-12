# -*- coding: utf-8 -*-
"""
Solar Chat API를 활용한 차량 모델명 매칭 스크립트

견적서에서 추출한 차량명(예: "산타페 2018년형")을
모비스 검색 가능한 모델명(예: "싼타페 18")으로 변환하고,
mobis-models.json에서 catSeq를 찾아 반환한다.

사용법:
    python match_vehicle_model.py "산타페 2018년형"
    python match_vehicle_model.py "아반떼 2020년식"
    python match_vehicle_model.py "K5 2023"
"""

import json
import os
import sys
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# .env 파일 로드 (skills/solar-skill-creator/assets/.env.example 경로)
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent  # skills/docs/scripts → project root
ENV_PATHS = [
    PROJECT_ROOT / "skills" / "solar-skill-creator" / "assets" / ".env",
    SCRIPT_DIR.parent / "assets" / ".env",
]
for env_path in ENV_PATHS:
    if env_path.exists():
        load_dotenv(env_path)
        break

# 모비스 모델 목록 로드
MODELS_PATH = SCRIPT_DIR.parent / "mobis-models.json"
with open(MODELS_PATH, encoding="utf-8") as f:
    MOBIS_DATA = json.load(f)
    MODELS = MOBIS_DATA["models"]

# 모델명 목록을 텍스트로 준비 (Solar Chat 컨텍스트용)
MODEL_NAMES = sorted(set(v["name"] for v in MODELS.values()))


def match_vehicle_model(user_input: str) -> dict:
    """
    Solar Chat API를 호출하여 차량명을 모비스 모델명으로 변환한다.

    Args:
        user_input: 견적서에서 추출한 차량명 (예: "산타페 2018년형")

    Returns:
        {
            "input": "산타페 2018년형",
            "matched_name": "싼타페 18",
            "cat_seq": "1544597",
            "maker": "H",
            "vtype": "P",
            "confidence": "high"
        }
    """
    api_key = os.getenv("UPSTAGE_API_KEY")
    if not api_key:
        return {"error": "UPSTAGE_API_KEY가 설정되지 않았습니다."}

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.upstage.ai/v1"
    )

    # 모델명 목록을 줄바꿈으로 나열
    model_list_text = "\n".join(MODEL_NAMES)

    prompt = f"""당신은 현대모비스 차량 모델 매칭 전문가입니다.

사용자가 입력한 차량명을 아래 모비스 모델 목록에서 가장 적절한 것을 찾아주세요.

## 핵심 규칙: 모델 연식 매칭
모비스 모델명의 숫자는 출시 연도의 뒤 두 자리입니다.
- "싼타페 18" = 2018년 출시 모델
- "쏘나타 23" = 2023년 출시 모델
- "아반떼 20" = 2020년 출시 모델

따라서:
- "2018년형" → 뒤 두 자리 "18"과 매칭
- "2020년식" → "20"과 매칭
- "18년" → "18"과 매칭

## 기타 규칙
1. 모델 목록에 있는 이름 중 하나를 정확히 반환해야 합니다.
2. "산타페" → "싼타페", "소나타" → "쏘나타" 같은 표기 차이를 고려하세요.
3. 하이브리드, 전기차, N 라인 등 트림 정보가 있으면 반영하세요.
4. 매칭할 수 없으면 "NONE"을 반환하세요.

## 모비스 모델 목록
{model_list_text}

## 사용자 입력
{user_input}

## 응답 형식 (JSON)
{{"matched_name": "모델명", "confidence": "high/medium/low", "reason": "매칭 이유"}}"""

    response = client.chat.completions.create(
        model="solar-pro3",
        messages=[
            {"role": "system", "content": "정확한 JSON만 반환하세요. 다른 텍스트는 포함하지 마세요."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
        max_tokens=200
    )

    raw_response = response.choices[0].message.content.strip()

    # JSON 파싱
    try:
        # ```json ... ``` 래핑 제거
        if raw_response.startswith("```"):
            raw_response = raw_response.split("```")[1]
            if raw_response.startswith("json"):
                raw_response = raw_response[4:]
        result = json.loads(raw_response.strip())
    except json.JSONDecodeError:
        return {"error": f"Solar Chat 응답 파싱 실패: {raw_response}"}

    matched_name = result.get("matched_name", "NONE")

    if matched_name == "NONE":
        return {
            "input": user_input,
            "matched_name": None,
            "cat_seq": None,
            "error": "매칭 실패",
            "raw_response": result
        }

    # mobis-models.json에서 catSeq 찾기
    cat_seq = None
    maker = None
    vtype = None
    for seq, info in MODELS.items():
        if info["name"] == matched_name:
            cat_seq = seq
            maker = info["maker"]
            vtype = info["vtype"]
            break

    return {
        "input": user_input,
        "matched_name": matched_name,
        "cat_seq": cat_seq,
        "maker": maker,
        "vtype": vtype,
        "confidence": result.get("confidence", "unknown"),
        "reason": result.get("reason", "")
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python match_vehicle_model.py '차량명'")
        print("예시: python match_vehicle_model.py '산타페 2018년형'")
        sys.exit(1)

    user_input = sys.argv[1]
    result = match_vehicle_model(user_input)
    print(json.dumps(result, ensure_ascii=False, indent=2))
