# -*- coding: utf-8 -*-
"""
견적서 OCR 파싱 스크립트

Upstage Document Parse API로 견적서 사진을 파싱하고,
Solar Chat API로 ParsedEstimate JSON 구조로 변환한다.

사용법:
    python parse_estimate.py /path/to/estimate_photo.jpg
    python parse_estimate.py /path/to/estimate_photo.jpg --html-only  # HTML만 출력 (디버깅용)
"""

import json
import os
import sys
import argparse
from pathlib import Path

import requests
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

# ParsedEstimate JSON Schema 로드
SCHEMA_PATH = SCRIPT_DIR.parent / "parsed-estimate-schema.json"
with open(SCHEMA_PATH, encoding="utf-8") as f:
    PARSED_ESTIMATE_SCHEMA = json.load(f)


def document_parse(image_path: str) -> dict:
    """
    Upstage Document Parse API로 견적서 이미지를 파싱한다.

    Args:
        image_path: 견적서 이미지 파일 경로 (JPG/PNG)

    Returns:
        Document Parse API 응답 (content.html, content.markdown, elements 포함)
    """
    api_key = os.getenv("UPSTAGE_API_KEY")
    if not api_key:
        raise RuntimeError("UPSTAGE_API_KEY가 설정되지 않았습니다.")

    with open(image_path, "rb") as f:
        resp = requests.post(
            "https://api.upstage.ai/v1/document-digitization",
            headers={"Authorization": f"Bearer {api_key}"},
            files={"document": f},
            data={
                "model": "document-parse",
                "ocr": "force",
                "output_formats": '["html","markdown"]',
            },
        )
    resp.raise_for_status()
    return resp.json()


def html_to_parsed_estimate(html_content: str, markdown_content: str = "") -> dict:
    """
    Solar Chat API로 Document Parse 결과를 ParsedEstimate JSON으로 변환한다.

    Args:
        html_content: Document Parse에서 추출한 HTML
        markdown_content: Document Parse에서 추출한 Markdown (보조)

    Returns:
        ParsedEstimate 구조의 dict
    """
    api_key = os.getenv("UPSTAGE_API_KEY")
    if not api_key:
        raise RuntimeError("UPSTAGE_API_KEY가 설정되지 않았습니다.")

    client = OpenAI(
        api_key=api_key,
        base_url="https://api.upstage.ai/v1"
    )

    # 스키마에서 description을 포함한 간략 버전을 프롬프트에 포함
    schema_str = json.dumps(PARSED_ESTIMATE_SCHEMA, ensure_ascii=False, indent=2)

    prompt = f"""당신은 자동차 정비 견적서 OCR 데이터 추출 전문가입니다.

아래 HTML은 자동차 정비 견적서를 OCR로 파싱한 결과입니다.
이 HTML에서 정보를 추출하여 주어진 JSON 스키마에 맞게 변환해주세요.

## 핵심 규칙

1. **항목 테이블(items)이 가장 중요합니다.** 각 행의 정비내용, 부품비, 공임비, 합계를 정확히 추출하세요.
2. **가격은 모두 정수(원)로 변환하세요.** "62,400원" → 62400, "62,400" → 62400
3. **날짜는 ISO 형식(YYYY-MM-DD)으로 변환하세요.**
4. **주행거리는 km 단위 정수로 변환하세요.** "45,230km" → 45230
5. **raw_description**: 견적내용 칸의 텍스트를 그대로 넣으세요.
6. **raw_part_code**: 코드 칸이 있으면 그대로 넣으세요. 없으면 null.
7. **item_type**: 한 줄에 부품비와 공임비가 모두 있으면 "combined", 부품비만 있으면 "part_only", 공임비만 있으면 "labor_only".
8. **insurance_type**: 보험 관련 내용이 보이면 "insurance", 일반이면 "general", 판단 불가면 "unknown".
9. **추출할 수 없는 필드는 null로 설정하세요.**
10. **ocr_meta.is_standard_format**: 자동차관리법 별지 제89호의3 양식이면 true.
11. **ocr_meta.parse_confidence**: 전체적인 추출 신뢰도를 0.0~1.0으로 평가하세요.
12. **ocr_meta.warnings**: 의심스러운 값(음수 가격, 비현실적 주행거리 등)이 있으면 기록하세요.

## JSON 스키마
{schema_str}

## 견적서 HTML
{html_content}

## 견적서 Markdown (참고용)
{markdown_content}

위 데이터를 분석하여 JSON 스키마에 맞는 JSON만 반환하세요. 다른 텍스트는 포함하지 마세요."""

    response = client.chat.completions.create(
        model="solar-pro3",
        messages=[
            {"role": "system", "content": "정확한 JSON만 반환하세요. 코드블록(```)으로 감싸지 마세요."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.1,
        max_tokens=4000
    )

    raw_response = response.choices[0].message.content.strip()

    # JSON 파싱 (```json ... ``` 래핑 제거)
    if raw_response.startswith("```"):
        raw_response = raw_response.split("```")[1]
        if raw_response.startswith("json"):
            raw_response = raw_response[4:]
        raw_response = raw_response.strip()

    try:
        return json.loads(raw_response)
    except json.JSONDecodeError as e:
        return {"error": f"JSON 파싱 실패: {e}", "raw_response": raw_response[:500]}


def parse_estimate(image_path: str, html_only: bool = False) -> dict:
    """
    전체 파이프라인: 이미지 → Document Parse → Solar Chat → ParsedEstimate

    Args:
        image_path: 견적서 이미지 파일 경로
        html_only: True이면 Document Parse HTML만 반환 (디버깅용)

    Returns:
        ParsedEstimate JSON 또는 HTML (html_only=True일 때)
    """
    # Step 1: Document Parse
    print(f"[1/2] Document Parse 호출 중... ({image_path})", file=sys.stderr)
    parse_result = document_parse(image_path)

    html_content = parse_result.get("content", {}).get("html", "")
    markdown_content = parse_result.get("content", {}).get("markdown", "")
    pages_billed = parse_result.get("usage", {}).get("pages", 0)
    print(f"  → HTML: {len(html_content)} chars, Markdown: {len(markdown_content)} chars, Pages: {pages_billed}", file=sys.stderr)

    if html_only:
        return {
            "html": html_content,
            "markdown": markdown_content,
            "elements": parse_result.get("elements", []),
            "pages": pages_billed
        }

    # Step 2: Solar Chat으로 ParsedEstimate 변환
    print("[2/2] Solar Chat으로 ParsedEstimate 변환 중...", file=sys.stderr)
    parsed = html_to_parsed_estimate(html_content, markdown_content)

    return parsed


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="견적서 OCR 파싱")
    parser.add_argument("image_path", help="견적서 이미지 파일 경로")
    parser.add_argument("--html-only", action="store_true", help="Document Parse HTML만 출력 (디버깅용)")
    args = parser.parse_args()

    if not Path(args.image_path).exists():
        print(f"파일을 찾을 수 없습니다: {args.image_path}", file=sys.stderr)
        sys.exit(1)

    result = parse_estimate(args.image_path, html_only=args.html_only)
    print(json.dumps(result, ensure_ascii=False, indent=2))
