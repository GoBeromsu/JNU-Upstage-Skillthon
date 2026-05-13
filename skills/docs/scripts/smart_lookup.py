# -*- coding: utf-8 -*-
"""
Solar Chat 기반 스마트 가격 조회 스크립트

OCR 결과의 각 항목을 Solar Chat으로 개별 분석하여:
1) 공임나라에서 검색할 수 있는 공임 작업명으로 변환
2) 모비스에서 검색할 수 있는 부품명으로 변환
한 뒤, 실제 가격을 조회하여 비교 결과를 반환한다.

사용법:
    python smart_lookup.py ocr_result.json --maker H --cat-seq 1544503 --vehicle-model "쏘나타 YF"
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
    PROJECT_ROOT / "skills" / "solar-skill-creator" / "assets" / ".env",
    SCRIPT_DIR.parent / "assets" / ".env",
]
for env_path in ENV_PATHS:
    if env_path.exists():
        load_dotenv(env_path)
        break

# 공임나라 카테고리 목록
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
        max_tokens=300
    )
    return resp.choices[0].message.content.strip()


def match_single_item(item: dict, vehicle_model: str) -> dict:
    """
    Solar Chat으로 단일 항목을 공임나라/모비스 검색어로 매핑한다.
    """
    desc = item.get("raw_description", "")
    labor = item.get("labor_cost", 0)
    parts = item.get("part_subtotal", 0)
    part_code = item.get("raw_part_code", "")
    line_total = item.get("line_total", 0)

    categories_text = ", ".join(GONGIM_CATEGORIES)

    # 공급가액(부품+공임 합산) 형태인 경우
    is_combined_price = (labor == 0 and parts == 0 and line_total > 0)

    prompt = f"""차량: {vehicle_model}
항목: {desc}
부품코드: {part_code or "없음"}
부품비: {parts:,}원, 공임: {labor:,}원, 합계: {line_total:,}원

공임나라 카테고리: {categories_text}

이 정비 항목에 대해 JSON으로 답하세요:
- gongim_category: 공임나라 카테고리 중 하나 (해당 없으면 null)
- gongim_search_hint: 공임나라에서 찾을 작업명 (예: "범퍼교환", "쇼바교환") (해당 없으면 null)
- mobis_search_term: 모비스에서 검색할 부품명 3글자 이상 (예: "머플러", "브레이크 패드") (부품 없으면 null)
- item_category: labor_only / part_only / combined / painting / supply_price / etc

JSON만 반환하세요."""

    raw = solar_chat(prompt, system="정확한 JSON 객체 하나만 반환하세요.")

    # JSON 파싱
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    try:
        result = json.loads(raw)
        return result
    except json.JSONDecodeError:
        return {
            "gongim_category": None,
            "gongim_search_hint": None,
            "mobis_search_term": None,
            "item_category": "unknown"
        }


def run_smart_lookup(ocr_result: dict, maker: str = "H", cat_seq: str = "", vehicle_model: str = "") -> dict:
    """
    OCR 결과를 받아서 Solar Chat 매핑 -> 공임나라/모비스 검색 -> 비교 결과 반환
    """
    from lookup_gongim import get_categories, get_labor_costs

    items = ocr_result.get("items", [])
    if not items:
        return {"error": "항목이 없습니다."}

    if not vehicle_model:
        vehicle_model = ocr_result.get("vehicle_car_model", "알 수 없음")

    # Step 1: Solar Chat으로 항목 하나씩 매핑
    print(f"[1/3] Solar Chat으로 {len(items)}개 항목 개별 매핑 중...", file=sys.stderr)
    mappings = []
    for i, item in enumerate(items):
        mapping = match_single_item(item, vehicle_model)
        mapping["line_number"] = item.get("line_number", i + 1)
        mappings.append(mapping)
        desc = item.get("raw_description", "")[:20]
        cat = mapping.get("gongim_category") or "-"
        mobis = mapping.get("mobis_search_term") or "-"
        print(f"  [{i+1}/{len(items)}] {desc}... → 공임:{cat}, 모비스:{mobis}", file=sys.stderr)

    mapping_by_line = {m["line_number"]: m for m in mappings}

    # Step 2: 공임나라 조회
    print("[2/3] 공임나라 공임비 조회 중...", file=sys.stderr)
    categories = get_categories()
    cat_by_name = {c["name"]: c["id"] for c in categories}

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
        print(f"  공임나라 '{cat_name}': {len(gongim_data[cat_name])}건", file=sys.stderr)

    # Step 3: 모비스 부품 검색
    print("[3/3] 모비스 부품가격 조회 중...", file=sys.stderr)
    mobis_results = {}

    # 3-A: 부품번호가 있는 항목은 부품번호로 직접 검색
    part_numbers = {}
    for item in items:
        ptno = item.get("raw_part_code", "").strip()
        if ptno and len(ptno) >= 5 and ptno not in ("A", "B", "C", "D", "F"):
            part_numbers[ptno] = item.get("raw_description", "")

    # 3-B: 부품명 검색이 필요한 항목
    needed_parts = set()
    for m in mappings:
        mt = m.get("mobis_search_term")
        if mt:
            needed_parts.add(mt)

    if part_numbers or (needed_parts and cat_seq):
        from lookup_mobis import create_stealth_browser, search_parts, parse_parts_html
        from playwright.sync_api import sync_playwright

        with sync_playwright() as p:
            browser, page = create_stealth_browser(p)
            page.goto("https://www.mobis-as.com/simple_search_part.do", timeout=15000)
            page.wait_for_load_state("networkidle", timeout=10000)

            # 부품번호 직접 검색
            for ptno, desc in part_numbers.items():
                html = search_parts(page, maker=maker, srch_type="ptno", search_term=ptno)
                result = parse_parts_html(html)
                if result["total"] > 0:
                    mobis_results[f"ptno:{ptno}"] = result
                    print(f"  모비스 부품번호 '{ptno}': {result['total']}건 ({result['parts'][0]['price_krw']:,}원)", file=sys.stderr)
                else:
                    print(f"  모비스 부품번호 '{ptno}': 조회 불가", file=sys.stderr)

            # 부품명 검색
            if cat_seq:
                for part_name in needed_parts:
                    html = search_parts(page, maker=maker, vtyp="P", cat_seq=cat_seq, search_term=part_name)
                    result = parse_parts_html(html)
                    mobis_results[part_name] = result
                    if result["total"] > 0:
                        print(f"  모비스 '{part_name}': {result['total']}건", file=sys.stderr)
                    else:
                        print(f"  모비스 '{part_name}': 0건", file=sys.stderr)

            browser.close()

    # Step 4: 결과 조합
    results = []
    for item in items:
        ln = item.get("line_number", 0)
        mapping = mapping_by_line.get(ln, {})
        ptno = item.get("raw_part_code", "").strip()

        entry = {
            "line_number": ln,
            "raw_description": item.get("raw_description", ""),
            "raw_part_code": ptno,
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
            if not best_match:
                for g_item in gongim_data[gc]:
                    wt = g_item["work_type"].replace("\r\n", " ").strip()
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

        # 모비스 매칭 — 부품번호 우선
        if ptno and f"ptno:{ptno}" in mobis_results:
            mr = mobis_results[f"ptno:{ptno}"]
            if mr["total"] > 0:
                part = mr["parts"][0]
                entry["mobis_match"] = {
                    "search_type": "part_number",
                    "part_number": ptno,
                    "name_kr": part["name_kr"],
                    "price_krw": part["price_krw"],
                }

        # 모비스 매칭 — 부품명 검색
        if not entry["mobis_match"]:
            mt = mapping.get("mobis_search_term")
            if mt and mt in mobis_results and mobis_results[mt]["total"] > 0:
                parts = mobis_results[mt]["parts"]
                prices = [p["price_krw"] for p in parts]
                entry["mobis_match"] = {
                    "search_type": "part_name",
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
        "estimate_parts_total": ocr_result.get("summary_parts_total", 0),
        "estimate_labor_total": ocr_result.get("summary_labor_total", 0),
        "estimate_subtotal": ocr_result.get("summary_subtotal", 0),
        "estimate_vat": ocr_result.get("summary_vat", 0),
        "estimate_grand_total": ocr_result.get("summary_grand_total", 0),
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
