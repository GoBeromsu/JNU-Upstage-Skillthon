# -*- coding: utf-8 -*-
"""
Solar Chat 기반 스마트 가격 조회 스크립트

OCR 결과의 각 항목을 Solar Chat으로 분석하여:
1) 공임나라에서 검색할 수 있는 공임 작업명으로 변환
2) 모비스에서 검색할 수 있는 부품명으로 변환
한 뒤, 실제 가격을 조회하여 비교 결과를 반환한다.

사용법:
    python smart_lookup.py ocr_result.json
    python smart_lookup.py ocr_result.json --maker H --model-year 2014
"""

import json
import os
import sys
import argparse
from pathlib import Path

from openai import OpenAI
from dotenv import load_dotenv

# .env 로드
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent
ENV_PATHS = [
    PROJECT_ROOT / "skills" / "solar-skill-creator" / "assets" / ".env.example",
    PROJECT_ROOT / ".claude" / "skills" / "solar-skill-creator" / "assets" / ".env.example",
]
for env_path in ENV_PATHS:
    if env_path.exists():
        load_dotenv(env_path)
        break

# 공임나라 카테고리 목록 (하드코딩 — 변경 빈도 낮음)
GONGIM_CATEGORIES = [
    "엔진오일", "미션오일", "브레이크", "부동액", "파워오일", "연료필터",
    "배터리", "점화계통", "에어컨/히터", "등속조인트/핸들", "범퍼/펜더/소음기",
    "자동차점검", "마운트(미미)", "스테빌라이저", "사이드미러", "블랙박스",
    "시동모터", "발전기", "외부벨트", "쇼바교환/로우암", "타이밍벨트", "스로틀바디 클리닝"
]


def solar_chat(prompt: str, system: str = "") -> str:
    """Solar Chat API 호출 유틸리티"""
    api_key = os.getenv("UPSTAGE_API_KEY")
    client = OpenAI(api_key=api_key, base_url="https://api.upstage.ai/v1")

    messages = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    resp = client.chat.completions.create(
        model="solar-pro3",
        messages=messages,
        temperature=0.1,
        max_tokens=2000
    )
    return resp.choices[0].message.content.strip()


def match_items_with_solar(items: list, vehicle_model: str) -> list:
    """
    Solar Chat으로 OCR 항목들을 공임나라/모비스 검색어로 한 번에 매핑한다.
    API 호출을 최소화하기 위해 모든 항목을 한 번에 보낸다.
    """
    items_text = ""
    for item in items:
        desc = item.get("raw_description", "")
        labor = item.get("labor_cost", 0)
        parts = item.get("part_subtotal", 0)
        items_text += f"- {item.get('line_number', '?')}. {desc} (부품비: {parts:,}원, 공임: {labor:,}원)\n"

    categories_text = "\n".join(f"- {c}" for c in GONGIM_CATEGORIES)

    prompt = f"""당신은 자동차 정비 견적서 분석 전문가입니다.

아래는 "{vehicle_model}" 차량의 정비 견적서에서 OCR로 추출한 항목들입니다.
각 항목에 대해 공임나라와 현대모비스에서 가격을 검색할 수 있도록 매핑해주세요.

## 견적서 항목
{items_text}

## 공임나라 카테고리 목록
{categories_text}

## 작업

각 항목마다 아래를 판단해주세요:

1. **gongim_category**: 이 작업의 공임을 조회하려면 공임나라 어떤 카테고리에서 찾아야 하는지. 위 카테고리 중 하나를 정확히 적으세요. 해당 없으면 null.
2. **gongim_search_hint**: 공임나라 카테고리 내에서 이 작업과 가장 유사한 작업명. 예: "리어범퍼 교환" → "범퍼교환". 해당 없으면 null.
3. **mobis_search_term**: 이 항목에 교체 부품이 있다면, 현대모비스에서 검색할 부품명 (3글자 이상 한글). 예: "배기파이프3번(머플러)" → "머플러". 부품이 없는 공임 항목이면 null.
4. **item_category**: 이 항목의 종류. "labor_only"(공임만), "part_only"(부품만), "combined"(부품+공임), "painting"(도장), "etc"(기타)

## 응답 형식 (JSON 배열)
[
  {{"line_number": 1, "gongim_category": "범퍼/펜더/소음기", "gongim_search_hint": "범퍼교환", "mobis_search_term": "리어 범퍼", "item_category": "labor_only"}},
  ...
]

JSON 배열만 반환하세요."""

    raw = solar_chat(prompt, system="정확한 JSON 배열만 반환하세요. 코드블록(```)으로 감싸지 마세요.")

    # JSON 파싱 (여러 형식 대응)
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    # 1차 시도: 그대로 파싱
    try:
        result = json.loads(raw)
        if isinstance(result, list):
            return result
        if isinstance(result, dict):
            return [result]
    except json.JSONDecodeError:
        pass

    # 2차 시도: 줄바꿈으로 구분된 JSON 객체들 (JSONL 형식)
    try:
        results = []
        for line in raw.strip().split("\n"):
            line = line.strip().rstrip(",")
            if line.startswith("{"):
                results.append(json.loads(line))
        if results:
            return results
    except json.JSONDecodeError:
        pass

    # 3차 시도: 배열 래핑
    try:
        return json.loads("[" + raw + "]")
    except json.JSONDecodeError:
        pass

    print(f"[경고] Solar Chat 응답 파싱 실패: {raw[:300]}", file=sys.stderr)
    return []


def run_smart_lookup(ocr_result: dict, maker: str = "H", cat_seq: str = "", vehicle_model: str = "") -> dict:
    """
    OCR 결과를 받아서 Solar Chat 매핑 → 공임나라/모비스 검색 → 비교 결과 반환

    Args:
        ocr_result: Information Extract OCR 결과 (flat schema)
        maker: 제조사 코드 (H/K)
        cat_seq: 모비스 모델 코드
        vehicle_model: 차종명 (예: "LF 쏘나타")

    Returns:
        항목별 비교 결과
    """
    from lookup_gongim import get_categories, get_labor_costs

    items = ocr_result.get("items", [])
    if not items:
        return {"error": "항목이 없습니다."}

    if not vehicle_model:
        vehicle_model = ocr_result.get("vehicle_car_model", "알 수 없음")

    # Step 1: Solar Chat으로 모든 항목 매핑
    print(f"[1/3] Solar Chat으로 {len(items)}개 항목 매핑 중...", file=sys.stderr)
    mappings = match_items_with_solar(items, vehicle_model)

    # mapping을 line_number로 인덱싱
    mapping_by_line = {m["line_number"]: m for m in mappings}

    # Step 2: 공임나라 조회
    print("[2/3] 공임나라 공임비 조회 중...", file=sys.stderr)
    categories = get_categories()
    cat_by_name = {c["name"]: c["id"] for c in categories}

    # 필요한 카테고리만 조회 (중복 제거)
    needed_categories = set()
    for m in mappings:
        gc = m.get("gongim_category")
        if gc and gc in cat_by_name:
            needed_categories.add(gc)

    gongim_data = {}
    for cat_name in needed_categories:
        cat_id = cat_by_name[cat_name]
        result = get_labor_costs(cate_sub_no=cat_id)
        gongim_data[cat_name] = result.get("items", [])

    # Step 3: 모비스 부품 검색 (Playwright)
    print("[3/3] 모비스 부품가격 조회 중...", file=sys.stderr)
    mobis_results = {}
    needed_parts = set()
    for m in mappings:
        mt = m.get("mobis_search_term")
        if mt:
            needed_parts.add(mt)

    if needed_parts and cat_seq:
        from lookup_mobis import create_stealth_browser, search_parts, parse_parts_html
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser, page = create_stealth_browser(p)
            page.goto("https://www.mobis-as.com/simple_search_part.do", timeout=15000)
            page.wait_for_load_state("networkidle", timeout=10000)

            for part_name in needed_parts:
                html = search_parts(page, maker=maker, vtyp="P", cat_seq=cat_seq, search_term=part_name)
                result = parse_parts_html(html)
                mobis_results[part_name] = result
                print(f"  모비스 '{part_name}': {result['total']}건", file=sys.stderr)

            browser.close()

    # Step 4: 결과 조합
    results = []
    for item in items:
        ln = item.get("line_number", 0)
        mapping = mapping_by_line.get(ln, {})

        entry = {
            "line_number": ln,
            "raw_description": item.get("raw_description", ""),
            "estimate_total": item.get("line_total", 0),
            "estimate_labor": item.get("labor_cost", 0),
            "estimate_parts": item.get("part_subtotal", 0),
            "item_category": mapping.get("item_category", "unknown"),
            "gongim_match": None,
            "mobis_match": None,
        }

        # 공임나라 매칭
        gc = mapping.get("gongim_category")
        hint = mapping.get("gongim_search_hint")
        if gc and gc in gongim_data and hint:
            best_match = None
            for g_item in gongim_data[gc]:
                wt = g_item["work_type"].replace("\r\n", " ").strip()
                if hint in wt or wt in hint:
                    best_match = g_item
                    break
            # 못 찾으면 부분 매칭
            if not best_match:
                for g_item in gongim_data[gc]:
                    wt = g_item["work_type"].replace("\r\n", " ").strip()
                    # 키워드 기반 매칭
                    hint_words = hint.replace("교환", "").replace("교체", "").strip()
                    if hint_words and hint_words in wt:
                        best_match = g_item
                        break

            if best_match:
                entry["gongim_match"] = {
                    "work_type": best_match["work_type"].replace("\r\n", " ").strip(),
                    "price_krw": best_match["price_krw"],
                    "time_minutes": best_match.get("time_minutes"),
                }

        # 모비스 매칭
        mt = mapping.get("mobis_search_term")
        if mt and mt in mobis_results and mobis_results[mt]["total"] > 0:
            parts = mobis_results[mt]["parts"]
            # 가격 범위
            prices = [p["price_krw"] for p in parts]
            entry["mobis_match"] = {
                "search_term": mt,
                "total_results": mobis_results[mt]["total"],
                "price_min": min(prices),
                "price_max": max(prices),
                "top_results": parts[:3],
            }

        results.append(entry)

    # 합계
    summary = {
        "vehicle_model": vehicle_model,
        "maker": maker,
        "estimate_grand_total": ocr_result.get("summary_grand_total", 0),
        "estimate_subtotal": ocr_result.get("summary_subtotal", 0),
        "estimate_vat": ocr_result.get("summary_vat", 0),
        "items": results,
    }

    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Solar Chat 기반 스마트 가격 조회")
    parser.add_argument("ocr_json", help="OCR 결과 JSON 파일 경로")
    parser.add_argument("--maker", default="H", help="제조사: H(현대), K(기아)")
    parser.add_argument("--cat-seq", default="", help="모비스 모델 코드 (catSeq)")
    parser.add_argument("--vehicle-model", default="", help="차종명")
    args = parser.parse_args()

    with open(args.ocr_json, encoding="utf-8") as f:
        ocr_result = json.load(f)

    result = run_smart_lookup(
        ocr_result,
        maker=args.maker,
        cat_seq=args.cat_seq,
        vehicle_model=args.vehicle_model
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
