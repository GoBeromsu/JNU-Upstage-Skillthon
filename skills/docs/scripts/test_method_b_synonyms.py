# -*- coding: utf-8 -*-
"""
방법 B: 공임나라 동의어 사전 강화로 매칭률 향상 테스트

기존 동의어 사전에 빠진 매핑을 추가하고,
공임나라 카테고리 매칭을 다시 시도한다.
"""

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent
DOCS_DIR = SCRIPT_DIR.parent

# 기존 공임나라 카테고리 목록 (smart_lookup.py에서 가져옴)
GONGIM_CATEGORIES = [
    "엔진오일", "미션오일", "브레이크", "부동액", "파워오일", "연료필터",
    "배터리", "점화계통", "에어컨/히터", "등속조인트/핸들", "범퍼/펜더/소음기",
    "자동차점검", "마운트(미미)", "스테빌라이저", "사이드미러", "블랙박스",
    "시동모터", "발전기", "외부벨트", "쇼바교환/로우암", "타이밍벨트", "스로틀바디 클리닝"
]

# 비교불가 항목 13건
UNMATCHED_ITEMS = [
    {"desc": "고장원인 분석작업", "type": "labor", "price": 14400},
    {"desc": "브레이크 오일 교환 및 에어빼기", "type": "labor", "price": 57600},
    {"desc": "공기필터", "type": "labor", "price": 11340},
    {"desc": "프론트 브레이크 디스크 (양쪽)", "type": "labor", "price": 50400},
    {"desc": "리어 브레이크 패드(양쪽)", "type": "labor", "price": 48470},
    {"desc": "오토매틱오일교환(장비사용)", "type": "labor", "price": 42480},
    {"desc": "프론트브레이크디스크(양쪽)", "type": "labor", "price": 51800},
    {"desc": "리어브레이크디스크어셈블리(양쪽)", "type": "labor", "price": 59200},
    {"desc": "브레이크 오일 교환", "type": "labor", "price": 35500},
    {"desc": "엔진오일,휠터및에어크리너", "type": "labor", "price": 38780},
    {"desc": "엔진오일, 휠터및에어크리너", "type": "labor", "price": 38230},
    {"desc": "Diagnostic Tool Operation (EPB)", "type": "labor", "price": 14800},
    {"desc": "브레이크 오일 (볼트로닉)", "type": "part", "price": 51240},
]

# 기존 동의어 사전 로드
with open(DOCS_DIR / "labor-synonyms.json", encoding="utf-8") as f:
    EXISTING_SYNONYMS = json.load(f)

# 기존 동의어 매핑 구축 (synonym → standard_name)
existing_map = {}
mappings = EXISTING_SYNONYMS.get("mappings", EXISTING_SYNONYMS)
if isinstance(mappings, list):
    for entry in mappings:
        for syn in entry.get("synonyms", []):
            existing_map[syn] = entry["standard_name"]
elif isinstance(mappings, dict):
    # mappings가 dict인 경우 (구버전)
    pass


def check_existing_match(desc: str) -> str | None:
    """기존 동의어 사전으로 매칭 시도."""
    # 정확 매칭
    if desc in existing_map:
        return existing_map[desc]
    # 부분 매칭 (동의어가 desc에 포함)
    for syn, std in existing_map.items():
        if syn in desc or desc in syn:
            return f"{std} (부분매칭: '{syn}')"
    return None


# ── 새로운 동의어 매핑 (수동 분석 기반) ──
# 공임나라 카테고리 → 작업 유형 힌트와 함께 매핑
NEW_SYNONYMS = {
    # 고장원인 분석 → 자동차점검
    "고장원인 분석작업": {"category": "자동차점검", "hint": "고장원인분석", "reason": "점검/진단 작업"},
    "고장원인 분석": {"category": "자동차점검", "hint": "고장원인분석", "reason": "점검/진단 작업"},

    # 브레이크 오일 교환 → 브레이크
    "브레이크 오일 교환 및 에어빼기": {"category": "브레이크", "hint": "브레이크오일교환", "reason": "브레이크 오일 관련"},
    "브레이크 오일 교환": {"category": "브레이크", "hint": "브레이크오일교환", "reason": "브레이크 오일 관련"},
    "브레이크오일교환": {"category": "브레이크", "hint": "브레이크오일교환", "reason": "브레이크 오일 관련"},

    # 공기필터 교환 공임 → 엔진오일 (에어클리너 포함)
    "공기필터": {"category": "엔진오일", "hint": "에어크리너", "reason": "에어클리너/필터 교환은 엔진오일 카테고리"},

    # 브레이크 디스크 교환 → 브레이크
    "프론트 브레이크 디스크 (양쪽)": {"category": "브레이크", "hint": "디스크교환", "reason": "브레이크 디스크 교환"},
    "프론트 브레이크 디스크(양쪽)": {"category": "브레이크", "hint": "디스크교환", "reason": "브레이크 디스크 교환"},
    "프론트브레이크디스크(양쪽)": {"category": "브레이크", "hint": "디스크교환", "reason": "브레이크 디스크 교환"},
    "프론트브레이크디스크": {"category": "브레이크", "hint": "디스크교환", "reason": "브레이크 디스크 교환"},

    # 리어 브레이크 패드 → 브레이크
    "리어 브레이크 패드(양쪽)": {"category": "브레이크", "hint": "브레이크패드교환", "reason": "브레이크 패드 교환"},
    "리어 브레이크 패드": {"category": "브레이크", "hint": "브레이크패드교환", "reason": "브레이크 패드 교환"},

    # 리어 디스크 어셈블리 → 브레이크
    "리어브레이크디스크어셈블리(양쪽)": {"category": "브레이크", "hint": "디스크교환", "reason": "브레이크 디스크 교환"},
    "리어브레이크디스크어셈블리": {"category": "브레이크", "hint": "디스크교환", "reason": "브레이크 디스크 교환"},

    # 오토매틱오일교환 → 미션오일
    "오토매틱오일교환(장비사용)": {"category": "미션오일", "hint": "오토미션오일교환", "reason": "ATF 교환"},
    "오토매틱오일교환": {"category": "미션오일", "hint": "오토미션오일교환", "reason": "ATF 교환"},

    # 복합 작업: 엔진오일+필터+에어크리너
    "엔진오일,휠터및에어크리너": {"category": "엔진오일", "hint": "엔진오일 교환", "reason": "엔진오일+필터+에어크리너 복합"},
    "엔진오일, 휠터및에어크리너": {"category": "엔진오일", "hint": "엔진오일 교환", "reason": "엔진오일+필터+에어크리너 복합"},

    # EPB 진단 → 자동차점검 또는 브레이크
    "Diagnostic Tool Operation (EPB)": {"category": "브레이크", "hint": "EPB", "reason": "전자식 주차브레이크 진단"},
    "Diagnostic Tool Operation": {"category": "자동차점검", "hint": "진단", "reason": "진단기 사용"},
}


def check_new_match(desc: str) -> dict | None:
    """새 동의어 사전으로 매칭 시도."""
    # 정확 매칭
    if desc in NEW_SYNONYMS:
        return NEW_SYNONYMS[desc]
    # 공백/괄호 정규화
    normalized = desc.replace(" ", "").replace("(", "(").replace(")", ")")
    for key, val in NEW_SYNONYMS.items():
        if key.replace(" ", "").replace("(", "(").replace(")", ")") == normalized:
            return val
    # 부분 매칭
    for key, val in NEW_SYNONYMS.items():
        if key in desc or desc in key:
            return val
    return None


def test_synonym_enhancement():
    """동의어 사전 강화 테스트."""
    print("=== 방법 B: 동의어 사전 강화 테스트 ===\n")

    old_matched = 0
    new_matched = 0

    for i, item in enumerate(UNMATCHED_ITEMS, 1):
        desc = item["desc"]
        old = check_existing_match(desc)
        new = check_new_match(desc)

        old_mark = "✓" if old else "✗"
        new_mark = "✓" if new else "✗"

        if old:
            old_matched += 1
        if new:
            new_matched += 1

        print(f"[{i:2d}] {desc}")
        print(f"     견적가: {item['price']:>10,}원 [{item['type']}]")
        print(f"     기존사전: {old_mark} {old or '매칭 없음'}")
        if new:
            print(f"     신규사전: {new_mark} 카테고리={new['category']}, 힌트={new['hint']}")
            print(f"               사유: {new['reason']}")
        else:
            print(f"     신규사전: {new_mark} 매칭 없음")
        print()

    total = len(UNMATCHED_ITEMS)
    print(f"기존 매칭률: {old_matched}/{total} ({old_matched/total*100:.0f}%)")
    print(f"신규 매칭률: {new_matched}/{total} ({new_matched/total*100:.0f}%)")
    print(f"개선: +{new_matched - old_matched}건")


if __name__ == "__main__":
    test_synonym_enhancement()
