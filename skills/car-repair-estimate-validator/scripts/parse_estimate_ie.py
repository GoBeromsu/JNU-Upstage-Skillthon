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
