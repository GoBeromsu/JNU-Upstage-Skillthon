# -*- coding: utf-8 -*-
"""
방법 B 적용: 강화된 동의어 사전으로 smart_lookup 결과 보강

기존 smart_lookup 결과에서 gongim_match가 없는 항목에 대해
강화된 동의어 매핑 → 공임나라 실제 조회 → gongim_match 추가

사용법:
    python enhance_with_synonyms.py smart_lookup_result.json
"""

import json
import sys
from pathlib import Path

from lookup_gongim import get_categories, get_labor_costs

# 강화된 동의어 매핑: 견적서 표현 → {category, hint}
ENHANCED_SYNONYMS = {
    "고장원인 분석작업": {"category": "자동차점검", "hint": "점검"},
    "고장원인 분석": {"category": "자동차점검", "hint": "점검"},
    "브레이크 오일 교환 및 에어빼기": {"category": "브레이크", "hint": "브레이크오일"},
    "브레이크 오일 교환": {"category": "브레이크", "hint": "브레이크오일"},
    "브레이크오일교환": {"category": "브레이크", "hint": "브레이크오일"},
    "공기필터": {"category": "엔진오일", "hint": "에어클리너"},
    "프론트 브레이크 디스크 (양쪽)": {"category": "브레이크", "hint": "디스크"},
    "프론트 브레이크 디스크(양쪽)": {"category": "브레이크", "hint": "디스크"},
    "프론트브레이크디스크(양쪽)": {"category": "브레이크", "hint": "디스크"},
    "프론트브레이크디스크": {"category": "브레이크", "hint": "디스크"},
    "리어 브레이크 패드(양쪽)": {"category": "브레이크", "hint": "패드"},
    "리어 브레이크 패드": {"category": "브레이크", "hint": "패드"},
    "리어브레이크디스크어셈블리(양쪽)": {"category": "브레이크", "hint": "디스크"},
    "리어브레이크디스크어셈블리": {"category": "브레이크", "hint": "디스크"},
    "오토매틱오일교환(장비사용)": {"category": "미션오일", "hint": "오토미션"},
    "오토매틱오일교환": {"category": "미션오일", "hint": "오토미션"},
    "엔진오일,휠터및에어크리너": {"category": "엔진오일", "hint": "엔진오일"},
    "엔진오일, 휠터및에어크리너": {"category": "엔진오일", "hint": "엔진오일"},
    "Diagnostic Tool Operation (EPB)": {"category": "자동차점검", "hint": "점검"},
    "Diagnostic Tool Operation": {"category": "자동차점검", "hint": "점검"},
}


def find_synonym_match(desc: str) -> dict | None:
    """강화된 동의어로 매칭."""
    if desc in ENHANCED_SYNONYMS:
        return ENHANCED_SYNONYMS[desc]
    normalized = desc.replace(" ", "").replace("(", "(").replace(")", ")")
    for key, val in ENHANCED_SYNONYMS.items():
        if key.replace(" ", "").replace("(", "(").replace(")", ")") == normalized:
            return val
    for key, val in ENHANCED_SYNONYMS.items():
        if key in desc or desc in key:
            return val
    return None


def find_best_gongim_match(gongim_items: list, hint: str) -> dict | None:
    """공임나라 항목에서 힌트와 가장 잘 매칭되는 항목 찾기."""
    # 1차: 힌트가 작업명에 포함
    for item in gongim_items:
        wt = item["work_type"].replace("\r\n", " ").strip()
        if hint in wt or wt in hint:
            return item
    # 2차: 힌트 핵심어로 부분 매칭
    hint_core = hint.replace("교환", "").replace("교체", "").strip()
    if hint_core:
        for item in gongim_items:
            wt = item["work_type"].replace("\r\n", " ").strip()
            if hint_core in wt:
                return item
    return None


def enhance_lookup_result(lookup_result: dict) -> dict:
    """smart_lookup 결과에서 gongim_match 없는 항목을 보강."""
    items = lookup_result.get("items", [])

    # gongim_match 없는 공임 항목 찾기
    needs_enhancement = []
    for item in items:
        labor = item.get("estimate_labor", 0) or 0
        if labor > 0 and not item.get("gongim_match"):
            syn = find_synonym_match(item["raw_description"])
            if syn:
                needs_enhancement.append((item, syn))

    if not needs_enhancement:
        print("보강 대상 없음", file=sys.stderr)
        return lookup_result

    # 필요한 공임나라 카테고리 조회
    needed_categories = set(syn["category"] for _, syn in needs_enhancement)
    print(f"[보강] {len(needs_enhancement)}개 항목 대상, "
          f"공임나라 카테고리 {len(needed_categories)}개 조회", file=sys.stderr)

    categories = get_categories()
    cat_by_name = {c["name"]: c["id"] for c in categories}

    gongim_data = {}
    for cat_name in needed_categories:
        if cat_name in cat_by_name:
            cat_id = cat_by_name[cat_name]
            result = get_labor_costs(cate_sub_no=cat_id)
            gongim_data[cat_name] = result.get("items", [])
            print(f"  공임나라 '{cat_name}': {len(gongim_data[cat_name])}건", file=sys.stderr)

    # 매칭 적용
    enhanced_count = 0
    for item, syn in needs_enhancement:
        cat = syn["category"]
        hint = syn["hint"]
        if cat in gongim_data:
            best = find_best_gongim_match(gongim_data[cat], hint)
            if best:
                item["gongim_match"] = {
                    "work_type": best["work_type"].replace("\r\n", " ").strip(),
                    "price_krw": best["price_krw"],
                    "time_minutes": best.get("time_minutes"),
                }
                enhanced_count += 1
                print(f"  ✓ '{item['raw_description']}' → "
                      f"'{best['work_type'].replace(chr(13)+chr(10), ' ').strip()}' "
                      f"({best['price_krw']:,}원)", file=sys.stderr)
            else:
                print(f"  ✗ '{item['raw_description']}' → "
                      f"카테고리 '{cat}'에서 '{hint}' 매칭 실패", file=sys.stderr)

    print(f"[보강 완료] {enhanced_count}/{len(needs_enhancement)}건 추가 매칭", file=sys.stderr)
    return lookup_result


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python enhance_with_synonyms.py smart_lookup_result.json")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    with open(input_path, encoding="utf-8") as f:
        data = json.load(f)

    enhanced = enhance_lookup_result(data)
    print(json.dumps(enhanced, ensure_ascii=False, indent=2))
