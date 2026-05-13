# -*- coding: utf-8 -*-
"""
Solar Chat 기반 비교불가 항목 가격 추정 (fallback)

verify_estimate 결과에서 비교불가/저신뢰 항목을 찾아
Solar Chat으로 가격 범위를 추정하고 결과에 추가한다.

사용법:
    python fallback_solar_estimate.py verify_result.json
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


def estimate_unmatched_items(verify_result: dict) -> dict:
    """비교불가/저신뢰 항목에 Solar Chat 가격 추정을 추가."""
    vehicle = verify_result.get("input_summary", {}).get("vehicle_model", "알 수 없음")
    items = verify_result.get("items", [])

    unmatched = []
    for item in items:
        if item["status"] in ("no_reference", "low_confidence"):
            unmatched.append(item)

    if not unmatched:
        print("Solar Chat 추정 대상 없음", file=sys.stderr)
        return verify_result

    print(f"[Solar Chat] {len(unmatched)}개 비교불가 항목 가격 추정 중...", file=sys.stderr)

    items_text = ""
    for i, item in enumerate(unmatched, 1):
        labor = item.get("estimate_labor", 0)
        parts = item.get("estimate_parts", 0)
        total = item.get("estimate_total", 0)
        desc = item["raw_description"]

        if labor > 0 and parts > 0:
            price_type_hint = "combined (공임+부품 합산)"
        elif labor > 0:
            price_type_hint = "labor (공임만 추정할 것)"
        elif parts > 0:
            price_type_hint = "part (부품비만 추정할 것)"
        else:
            price_type_hint = "combined (공임+부품 합산 추정할 것)"

        items_text += f"{i}. {desc} [{price_type_hint}]\n"

    prompt = f"""당신은 한국 자동차 정비 가격 전문가입니다.

## 차량 정보
- 차종: {vehicle}

## 요청
아래 정비 항목들의 적정 가격 범위를 추정해주세요.

## 핵심 규칙
- 각 항목의 [price_type]을 반드시 확인하세요:
  - **labor (공임만)**: 해당 항목은 견적서에서 공임비만 기재된 것입니다. 부품비는 별도 행에 청구되므로, **공임비만** 추정하세요. 부품비를 합산하지 마세요.
  - **part (부품비만)**: 해당 항목은 부품비만 기재된 것입니다. **부품비만** 추정하세요.
  - **combined (공임+부품 합산)**: 공임과 부품이 합산된 금액입니다. **공임+부품 합산 가격**을 추정하세요.

## 가격 산정 기준
- 공임: 공임나라(gongim.com) 표준 공임비 기준
- 부품비: 현대모비스(mobis-as.com) 순정 부품 정가 기준
- 차종(소형차/중형차/SUV)에 따른 차이를 반영

## 정비 항목
{items_text}

## 응답 형식 (JSON 배열만 반환)
[
  {{
    "item_index": 1,
    "price_type": "labor / part / combined",
    "price_min": 최저가(원),
    "price_max": 최고가(원),
    "reference_basis": "추정 근거"
  }}
]"""

    raw = solar_chat(prompt, system="자동차 정비 가격을 공임나라·현대모비스 기준으로 추정합니다. JSON 배열만 반환하세요.")

    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        estimates = json.loads(raw)
        if isinstance(estimates, dict):
            for key in ("items", "result", "data", "results"):
                if key in estimates and isinstance(estimates[key], list):
                    estimates = estimates[key]
                    break
        if not isinstance(estimates, list):
            print(f"Solar Chat 응답이 배열이 아님: {raw[:200]}", file=sys.stderr)
            return verify_result
    except json.JSONDecodeError:
        print(f"Solar Chat JSON 파싱 실패: {raw[:300]}", file=sys.stderr)
        return verify_result

    for est in estimates:
        if not isinstance(est, dict):
            continue
        idx = est.get("item_index", 0)
        if 1 <= idx <= len(unmatched):
            target = unmatched[idx - 1]
            p_min = est.get("price_min", 0)
            p_max = est.get("price_max", 0)
            target["solar_estimate"] = {
                "price_type": est.get("price_type", "unknown"),
                "price_min": p_min,
                "price_max": p_max,
                "reference_basis": est.get("reference_basis", ""),
            }

            # 견적가가 추정 범위 내인지 판정
            est_price = target.get("estimate_labor", 0) or target.get("estimate_parts", 0) or target.get("estimate_total", 0)
            if p_min > 0 and p_max > 0 and est_price > 0:
                if est_price < p_min:
                    pct = round((est_price - p_min) / p_min * 100, 1)
                    target["solar_estimate"]["verdict"] = f"추정 범위보다 {abs(pct)}% 낮음"
                elif est_price > p_max:
                    pct = round((est_price - p_max) / p_max * 100, 1)
                    target["solar_estimate"]["verdict"] = f"추정 범위보다 {pct}% 높음"
                else:
                    target["solar_estimate"]["verdict"] = "추정 범위 내 (적정)"

            print(f"  [{idx}] {target['raw_description']} → {p_min:,}~{p_max:,}원 "
                  f"({est.get('reference_basis', '')})", file=sys.stderr)

    estimated = sum(1 for u in unmatched if u.get("solar_estimate"))
    print(f"[Solar Chat] {estimated}/{len(unmatched)}개 추정 완료", file=sys.stderr)
    return verify_result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python fallback_solar_estimate.py verify_result.json")
        sys.exit(1)

    with open(sys.argv[1], encoding="utf-8") as f:
        data = json.load(f)

    result = estimate_unmatched_items(data)
    print(json.dumps(result, ensure_ascii=False, indent=2))
