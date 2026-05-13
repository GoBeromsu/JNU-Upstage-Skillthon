# -*- coding: utf-8 -*-
"""
방법 A: Solar Chat으로 비교불가 항목의 시장 가격 범위 유추

Solar Chat에 비교불가 항목을 보내서 일반적인 가격 범위를 추론하게 한다.
"""

import json
import os
import sys
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
for env_path in [
    PROJECT_ROOT / "skills" / "solar-skill-creator" / "assets" / ".env",
    SCRIPT_DIR.parent / "assets" / ".env",
]:
    if env_path.exists():
        load_dotenv(env_path)
        break

# 두 견적서에서 추출한 비교불가 항목 13건
UNMATCHED_ITEMS = [
    # 공임 미매칭 (레이 2015)
    {"desc": "고장원인 분석작업", "type": "labor", "price": 14400, "vehicle": "기아 레이 2015"},
    {"desc": "브레이크 오일 교환 및 에어빼기", "type": "labor", "price": 57600, "vehicle": "기아 레이 2015"},
    {"desc": "공기필터", "type": "labor", "price": 11340, "vehicle": "기아 레이 2015"},
    {"desc": "프론트 브레이크 디스크 (양쪽)", "type": "labor", "price": 50400, "vehicle": "기아 레이 2015"},
    {"desc": "리어 브레이크 패드(양쪽)", "type": "labor", "price": 48470, "vehicle": "기아 레이 2015"},
    # 공임 미매칭 (스포티지 2022)
    {"desc": "오토매틱오일교환(장비사용)", "type": "labor", "price": 42480, "vehicle": "기아 스포티지 2022"},
    {"desc": "프론트브레이크디스크(양쪽)", "type": "labor", "price": 51800, "vehicle": "기아 스포티지 2022"},
    {"desc": "리어브레이크디스크어셈블리(양쪽)", "type": "labor", "price": 59200, "vehicle": "기아 스포티지 2022"},
    {"desc": "브레이크 오일 교환", "type": "labor", "price": 35500, "vehicle": "기아 스포티지 2022"},
    # 공임 저신뢰
    {"desc": "엔진오일,휠터및에어크리너", "type": "labor", "price": 38780, "vehicle": "기아 레이 2015"},
    {"desc": "엔진오일, 휠터및에어크리너", "type": "labor", "price": 38230, "vehicle": "기아 스포티지 2022"},
    {"desc": "Diagnostic Tool Operation (EPB)", "type": "labor", "price": 14800, "vehicle": "기아 스포티지 2022"},
    # 부품 미매칭
    {"desc": "브레이크 오일 (볼트로닉)", "type": "part", "price": 51240, "vehicle": "기아 스포티지 2022",
     "part_code": "01100001", "quantity": 2, "unit_price": 25620},
]


def solar_chat(prompt: str, system: str = "") -> str:
    api_key = os.getenv("UPSTAGE_API_KEY")
    client = OpenAI(api_key=api_key, base_url="https://api.upstage.ai/v1")
    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})
    resp = client.chat.completions.create(
        model="solar-pro3", messages=messages, temperature=0.1, max_tokens=2000
    )
    return resp.choices[0].message.content.strip()


def test_solar_price_inference():
    """Solar Chat에 비교불가 항목을 보내서 가격 범위를 유추."""

    items_text = ""
    for i, item in enumerate(UNMATCHED_ITEMS, 1):
        items_text += f"{i}. [{item['type']}] {item['desc']} — 견적가: {item['price']:,}원 (차량: {item['vehicle']})\n"

    prompt = f"""당신은 자동차 정비 가격 전문가입니다.

아래는 정비 견적서에서 추출한 항목들입니다. 각 항목의 **일반적인 시장 가격 범위**를 알려주세요.

## 항목 목록
{items_text}

## 응답 규칙
1. 각 항목에 대해 JSON 배열로 응답하세요.
2. type이 "labor"인 항목은 공임비(작업비)입니다. 한국 일반 정비소 기준의 공임 범위를 알려주세요.
3. type이 "part"인 항목은 부품비입니다. 순정 부품 기준의 가격 범위를 알려주세요.
4. price_min과 price_max는 원(KRW) 단위 정수입니다.
5. confidence는 가격 추정의 확신도 (high/medium/low)입니다.
6. source는 가격 추정 근거입니다.

## 응답 형식 (JSON 배열)
[
  {{"item_index": 1, "desc": "고장원인 분석작업", "price_min": 10000, "price_max": 20000, "confidence": "medium", "source": "일반 정비소 진단비 기준"}},
  ...
]

JSON 배열만 반환하세요."""

    print("Solar Chat 호출 중...", file=sys.stderr)
    raw = solar_chat(prompt, system="정확한 JSON 배열만 반환하세요.")

    # JSON 파싱
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        results = json.loads(raw)
        if isinstance(results, dict):
            # Solar Chat이 dict로 래핑한 경우
            for key in ("items", "result", "data", "results"):
                if key in results and isinstance(results[key], list):
                    results = results[key]
                    break
        if not isinstance(results, list):
            print(f"예상치 않은 응답 형식: {type(results)}", file=sys.stderr)
            print(f"원본: {raw[:500]}", file=sys.stderr)
            return
    except json.JSONDecodeError:
        print(f"JSON 파싱 실패: {raw[:500]}", file=sys.stderr)
        return

    # 결과 출력
    print("\n=== 방법 A: Solar Chat 가격 유추 결과 ===\n")
    matched = 0
    for r in results:
        if isinstance(r, str):
            print(f"문자열 항목 스킵: {r[:80]}", file=sys.stderr)
            continue
        idx = r.get("item_index", 0)
        if 1 <= idx <= len(UNMATCHED_ITEMS):
            item = UNMATCHED_ITEMS[idx - 1]
            est = item["price"]
            p_min = r.get("price_min", 0)
            p_max = r.get("price_max", 0)
            conf = r.get("confidence", "?")
            source = r.get("source", "")

            in_range = "✓" if p_min <= est <= p_max else "✗"
            if p_min > 0:
                matched += 1

            print(f"[{idx:2d}] {item['desc']}")
            print(f"     견적가: {est:>10,}원")
            print(f"     추정범위: {p_min:>10,} ~ {p_max:>10,}원  범위내:{in_range}  신뢰:{conf}")
            print(f"     근거: {source}")
            print()

    print(f"매칭률: {matched}/{len(UNMATCHED_ITEMS)} ({matched/len(UNMATCHED_ITEMS)*100:.0f}%)")


if __name__ == "__main__":
    test_solar_price_inference()
