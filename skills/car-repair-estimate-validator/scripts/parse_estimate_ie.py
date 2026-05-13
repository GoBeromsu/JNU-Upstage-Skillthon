# -*- coding: utf-8 -*-
"""
견적서 OCR 파싱 — Information Extract 방식 (이미지 → JSON 1단계)

Upstage Information Extract API로 견적서 사진에서 직접 구조화된 JSON을 추출한다.

사용법:
    python parse_estimate_ie.py /path/to/estimate_photo.jpg
"""

import base64
import json
import os
import sys
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv

# .env 로드
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
ENV_PATHS = [
    PROJECT_ROOT / "skills" / "solar-skill-creator" / "assets" / ".env",
    SCRIPT_DIR.parent / "assets" / ".env",
]
for env_path in ENV_PATHS:
    if env_path.exists():
        load_dotenv(env_path)
        break

# Information Extract용 플래트닝된 스키마 로드
FLAT_SCHEMA_PATH = SCRIPT_DIR.parent / "references" / "parsed-estimate-flat-schema.json"
with open(FLAT_SCHEMA_PATH, encoding="utf-8") as f:
    FLAT_SCHEMA = json.load(f)


def parse_estimate_ie(image_path: str) -> dict:
    """
    Information Extract API로 견적서 이미지에서 직접 JSON을 추출한다.

    Args:
        image_path: 견적서 이미지 파일 경로 (JPG/PNG)

    Returns:
        플래트닝된 ParsedEstimate 구조의 dict
    """
    api_key = os.getenv("UPSTAGE_API_KEY")
    if not api_key:
        raise RuntimeError("UPSTAGE_API_KEY가 설정되지 않았습니다.")

    # Information Extract는 base_url이 다름
    client = OpenAI(
        api_key=api_key,
        base_url="https://api.upstage.ai/v1/information-extraction",
    )

    # 이미지를 base64로 인코딩
    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    print(f"[IE] Information Extract 호출 중... ({image_path})", file=sys.stderr)

    resp = client.chat.completions.create(
        model="information-extract",
        messages=[{
            "role": "user",
            "content": [{
                "type": "image_url",
                "image_url": {"url": f"data:application/octet-stream;base64,{b64}"},
            }],
        }],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "car_repair_estimate",
                "schema": FLAT_SCHEMA,
            },
        },
    )

    raw_content = resp.choices[0].message.content
    result = json.loads(raw_content)

    print(f"  → 추출 완료. tokens: {resp.usage.total_tokens if resp.usage else 'N/A'}", file=sys.stderr)

    # OCR 후처리: 행 분리/합침 오류 보정
    result = _postprocess_ocr(result)

    return result


def _postprocess_ocr(result: dict) -> dict:
    """OCR 결과의 items 테이블 행 분리/합침 오류를 보정한다."""
    items = result.get("items", [])
    if not items:
        return result

    fixed_items = []
    skip_next = False

    for i, item in enumerate(items):
        if skip_next:
            skip_next = False
            continue

        desc = item.get("raw_description", "").strip()
        labor = item.get("labor_cost", 0) or 0
        parts = item.get("part_subtotal", 0) or 0
        total = item.get("line_total", 0) or 0

        # 1) 행 분리 보정: 짧은 텍스트(3자 이하)이고 가격이 0이면 다음 행과 합침
        if len(desc) <= 3 and labor == 0 and parts == 0 and total == 0:
            if i + 1 < len(items):
                next_item = items[i + 1]
                next_desc = next_item.get("raw_description", "").strip()
                merged_desc = desc + next_desc
                next_item["raw_description"] = merged_desc
                skip_next = False  # 다음 항목이 merge된 것을 사용
                # 현재 항목은 스킵, 다음 항목의 desc만 업데이트
                items[i + 1]["raw_description"] = merged_desc
                print(f"  [OCR 보정] 행 병합: '{desc}' + '{next_desc}' → '{merged_desc}'", file=sys.stderr)
                continue

        # 2) 가격 0이고 텍스트만 있는 짧은 행은 이전 행에 합침
        if labor == 0 and parts == 0 and total == 0 and len(desc) > 0 and fixed_items:
            prev = fixed_items[-1]
            prev_desc = prev.get("raw_description", "")
            # 이전 항목도 가격이 0이면 합치지 않음
            prev_total = prev.get("line_total", 0) or 0
            if prev_total == 0 and len(desc) <= 10:
                prev["raw_description"] = prev_desc + desc
                print(f"  [OCR 보정] 행 병합(뒤): '{prev_desc}' + '{desc}' → '{prev['raw_description']}'", file=sys.stderr)
                continue

        fixed_items.append(item)

    # 3) 차량명 순서 보정: "SUV 스포티지 The" → "The SUV 스포티지" 패턴
    car_model = result.get("vehicle_car_model", "")
    if car_model:
        # "SUV 모델명 The" → "The SUV 모델명"
        import re
        m = re.match(r'^(SUV\s+)(.+?)\s+(The|the|THE)$', car_model)
        if m:
            fixed = f"{m.group(3)} {m.group(1).strip()} {m.group(2)}"
            print(f"  [OCR 보정] 차량명: '{car_model}' → '{fixed}'", file=sys.stderr)
            result["vehicle_car_model"] = fixed

    # 라인 번호 재정렬
    for idx, item in enumerate(fixed_items, 1):
        item["line_number"] = idx

    result["items"] = fixed_items
    return result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python parse_estimate_ie.py /path/to/estimate_photo.jpg")
        sys.exit(1)

    image_path = sys.argv[1]
    if not Path(image_path).exists():
        print(f"파일을 찾을 수 없습니다: {image_path}", file=sys.stderr)
        sys.exit(1)

    result = parse_estimate_ie(image_path)
    print(json.dumps(result, ensure_ascii=False, indent=2))
