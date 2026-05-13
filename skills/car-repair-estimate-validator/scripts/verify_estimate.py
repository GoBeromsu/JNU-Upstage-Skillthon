# -*- coding: utf-8 -*-
"""
견적서 검증 엔진

smart_lookup 결과를 받아서:
1) 항목별 공임/부품 편차(%) 계산
2) 매칭 신뢰도 필터링
3) 구체적 한국어 제안 생성
4) 전체 판정 및 리포트 반환

사용법:
    python verify_estimate.py smart_lookup_result.json
"""

import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ─── 상수 ────────────────────────────────────────────────────────────

KST = timezone(timedelta(hours=9))

# 편차 임계값 (%)
THRESHOLD_NORMAL = 5        # ±5% 이내: 적정
THRESHOLD_SLIGHTLY = 15     # +5~15%: 다소 높음 / -5~-15%: 다소 낮음
THRESHOLD_HIGH = 30         # +15~30%: 높음
# +30% 이상: 매우 높음 / -15% 이하: 낮음

# 매칭 신뢰도 — 가격 규모 비율 상한
MAGNITUDE_RATIO_LIMIT = 5   # reference/estimate 또는 역이 5배 이상이면 신뢰도 낮음

# 부품명 검색 가격 범위 비율 상한
PRICE_RANGE_RATIO_LIMIT = 3  # max/min > 3이면 신뢰도 낮음

# 커버리지 최소 비율 (%)
MIN_COVERAGE_PCT = 30

LEVEL_KR = {
    "normal": "적정",
    "slightly_high": "다소 높음",
    "high": "높음",
    "very_high": "매우 높음",
    "slightly_low": "다소 낮음",
    "low": "낮음",
}

VERDICT_KR = {
    "insufficient_data": "데이터 부족",
    "reasonable": "적정",
    "slightly_high": "다소 높음",
    "high": "높음",
    "mixed": "항목별 편차 있음",
}


# ─── 전처리 ──────────────────────────────────────────────────────────

def _clean_work_type(work_type: str) -> str:
    """공임나라 work_type의 여러 줄 설명을 첫 줄 핵심만 추출하고 공백 정리."""
    import re
    text = work_type.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not text:
        return ""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    main_lines = [l for l in lines if not l.startswith("*")]
    result = main_lines[0] if main_lines else (lines[0] if lines else text)
    # 연속 공백 정리
    result = re.sub(r'\s{2,}', ' ', result).strip()
    return result


def _classify_item(item: dict) -> str:
    """실제 가격 필드 기반 분류 (Solar Chat item_category 무시)."""
    labor = item.get("estimate_labor", 0) or 0
    parts = item.get("estimate_parts", 0) or 0
    total = item.get("estimate_total", 0) or 0

    if total == 0 and labor == 0 and parts == 0:
        return "zero_price"
    if labor > 0 and parts > 0:
        return "combined"
    if labor > 0:
        return "labor_only"
    if parts > 0:
        return "part_only"
    # total > 0 이지만 labor/parts 분리 안 됨
    return "combined"


def _has_keyword_overlap(desc: str, work_type: str) -> bool:
    """두 문자열 사이에 의미 있는 키워드 겹침이 있는지 확인."""
    stopwords = {"교환", "교체", "수리", "조립", "분해", "탈착", "좌", "우", "앞", "뒤",
                 "프런트", "리어", "양쪽", "1개", "세트", "어셈블리", "프론트"}

    def extract_keywords(text: str) -> set:
        # 간단한 키워드 추출: 2글자 이상, stopword 제외
        text = text.replace("\r\n", " ").replace("-", " ").replace("(", " ").replace(")", " ")
        words = text.split()
        return {w for w in words if len(w) >= 2 and w not in stopwords}

    kw1 = extract_keywords(desc)
    kw2 = extract_keywords(work_type)
    return bool(kw1 & kw2)


def _assess_match_quality(item: dict) -> dict:
    """매칭 신뢰도 평가."""
    gongim_reliable = False
    mobis_reliable = False
    reasons = []

    gm = item.get("gongim_match")
    mm = item.get("mobis_match")
    labor = item.get("estimate_labor", 0) or 0
    parts = item.get("estimate_parts", 0) or 0
    desc = item.get("raw_description", "")

    # 공임 매칭 신뢰도
    if gm and labor > 0:
        ref = gm.get("price_krw", 0)
        if ref > 0:
            ratio = max(ref / labor, labor / ref) if labor > 0 else 999
            if ratio > MAGNITUDE_RATIO_LIMIT:
                reasons.append(f"공임 가격 규모 불일치 (비율 {ratio:.1f}배)")
            elif not _has_keyword_overlap(desc, gm.get("work_type", "")):
                reasons.append("공임 매칭 키워드 무관")
            else:
                gongim_reliable = True

    # 모비스 매칭 신뢰도
    if mm:
        if mm.get("search_type") == "part_number":
            mobis_reliable = True
        elif mm.get("search_type") == "part_name":
            p_min = mm.get("price_min", 0)
            p_max = mm.get("price_max", 0)
            if p_min > 0 and p_max > 0:
                if p_max / p_min > PRICE_RANGE_RATIO_LIMIT:
                    reasons.append(f"부품 검색 가격 범위 넓음 ({p_min:,}~{p_max:,}원)")
                else:
                    mobis_reliable = True
            elif mm.get("total_results", 0) > 0:
                mobis_reliable = True

    return {"gongim_reliable": gongim_reliable, "mobis_reliable": mobis_reliable, "reasons": reasons}


# ─── 편차 계산 ────────────────────────────────────────────────────────

def _categorize_deviation(pct: float) -> str:
    """편차 %를 level 문자열로 변환."""
    if pct > THRESHOLD_HIGH:
        return "very_high"
    elif pct > THRESHOLD_SLIGHTLY:
        return "high"
    elif pct > THRESHOLD_NORMAL:
        return "slightly_high"
    elif pct >= -THRESHOLD_NORMAL:
        return "normal"
    elif pct >= -THRESHOLD_SLIGHTLY:
        return "slightly_low"
    else:
        return "low"


def _compute_deviation(estimate_price: int, reference_price: int) -> dict:
    """편차 계산."""
    if reference_price == 0:
        return None
    deviation_krw = estimate_price - reference_price
    deviation_pct = round((deviation_krw / reference_price) * 100, 1)
    level = _categorize_deviation(deviation_pct)
    return {
        "deviation_pct": deviation_pct,
        "deviation_krw": deviation_krw,
        "level": level,
        "level_kr": LEVEL_KR.get(level, level),
    }


# ─── 비교 ─────────────────────────────────────────────────────────────

def _compare_labor(item: dict, quality: dict) -> dict | None:
    """estimate_labor vs gongim_match.price_krw 비교."""
    gm = item.get("gongim_match")
    labor = item.get("estimate_labor", 0) or 0
    if not gm or labor == 0:
        return None

    ref_price = gm.get("price_krw", 0)
    if ref_price == 0:
        return None

    dev = _compute_deviation(labor, ref_price)
    if not dev:
        return None

    return {
        "reference_source": "공임나라",
        "reference_description": _clean_work_type(gm.get("work_type", "")),
        "reference_price": ref_price,
        "estimate_price": labor,
        "match_reliable": quality["gongim_reliable"],
        **dev,
    }


def _compare_parts(item: dict, quality: dict) -> dict | None:
    """estimate_parts vs mobis_match 비교. 수량 반영."""
    mm = item.get("mobis_match")
    parts = item.get("estimate_parts", 0) or 0
    if not mm or parts == 0:
        return None

    quantity = item.get("quantity", 1) or 1

    if mm.get("search_type") == "part_number":
        unit_ref = mm.get("price_krw", 0)
        if unit_ref == 0:
            return None
        # 수량 반영: 모비스 단가 × 수량 = 총 기준가
        ref_price = unit_ref * quantity
        dev = _compute_deviation(parts, ref_price)
        if not dev:
            return None
        result = {
            "reference_source": "모비스",
            "reference_description": mm.get("name_kr", ""),
            "reference_price": ref_price,
            "reference_unit_price": unit_ref,
            "quantity": quantity,
            "estimate_price": parts,
            "search_type": "part_number",
            "part_number": mm.get("part_number", ""),
            "match_reliable": quality["mobis_reliable"],
            **dev,
        }
        return result

    elif mm.get("search_type") == "part_name":
        p_min = mm.get("price_min", 0) * quantity
        p_max = mm.get("price_max", 0) * quantity
        if p_min == 0 and p_max == 0:
            return None

        # 범위 비교 (수량 반영 후)
        if parts < p_min:
            ref_price = p_min
        elif parts > p_max:
            ref_price = p_max
        else:
            ref_price = (p_min + p_max) // 2

        dev = _compute_deviation(parts, ref_price)
        if not dev:
            return None

        return {
            "reference_source": "모비스",
            "reference_description": f"'{mm.get('search_term', '')}' 검색 결과",
            "reference_price": ref_price,
            "price_range": {"min": p_min, "max": p_max},
            "estimate_price": parts,
            "search_type": "part_name",
            "total_results": mm.get("total_results", 0),
            "match_reliable": quality["mobis_reliable"],
            **dev,
        }

    return None


# ─── 제안 생성 ─────────────────────────────────────────────────────────

def _generate_item_suggestion(item_result: dict) -> str | None:
    """항목별 구체적 한국어 제안 생성."""
    suggestions = []
    desc = item_result["raw_description"]

    lc = item_result.get("labor_comparison")
    if lc and lc["match_reliable"]:
        est = lc["estimate_price"]
        ref = lc["reference_price"]
        diff = lc["deviation_krw"]
        pct = lc["deviation_pct"]
        level = lc["level"]
        wt = lc["reference_description"]

        if level in ("high", "very_high"):
            suggestions.append(
                f"{desc} 공임 {est:,}원 → 공임나라 기준 {ref:,}원 "
                f"(차액 {diff:,}원, +{pct}%). "
                f"정비소에 '{wt}' 공임 산정 근거(시간당 단가 × 작업시간)를 요청하세요."
            )
        elif level == "slightly_high":
            suggestions.append(
                f"{desc} 공임 {est:,}원 → 공임나라 '{wt}' 기준 {ref:,}원 대비 "
                f"{diff:,}원(+{pct}%) 높습니다."
            )
        elif level == "low":
            suggestions.append(
                f"{desc} 공임 {est:,}원 → 공임나라 기준 {ref:,}원보다 "
                f"{abs(diff):,}원 낮습니다. 다른 항목과 묶음 할인이 적용되었을 수 있습니다."
            )
    elif lc and not lc["match_reliable"]:
        suggestions.append(
            f"{desc}: 공임 비교 데이터의 정확도가 낮아 참고용으로만 활용하세요 "
            f"(공임나라 '{lc['reference_description']}' {lc['reference_price']:,}원)."
        )

    pc = item_result.get("parts_comparison")
    if pc and pc["match_reliable"]:
        est = pc["estimate_price"]
        ref = pc["reference_price"]
        diff = pc["deviation_krw"]
        pct = pc["deviation_pct"]
        level = pc["level"]
        ptno = pc.get("part_number", "")

        if level in ("high", "very_high"):
            if pc["search_type"] == "part_number" and ptno:
                suggestions.append(
                    f"{desc} 부품비 {est:,}원 → 모비스 순정가 {ref:,}원 "
                    f"(차액 {diff:,}원, +{pct}%). "
                    f"부품 코드 {ptno}의 순정 부품 사용 여부를 확인하고, "
                    f"비순정이면 순정가 대비 할인이 적용되어야 합니다."
                )
            else:
                pr = pc.get("price_range", {})
                suggestions.append(
                    f"{desc} 부품비 {est:,}원 → 모비스 '{pc.get('reference_description', '')}' "
                    f"{pr.get('min', 0):,}~{pr.get('max', 0):,}원 범위 초과. "
                    f"정확한 부품번호를 요청하여 정가를 확인하세요."
                )
        elif level == "slightly_high":
            suggestions.append(
                f"{desc} 부품비 {est:,}원 → 모비스 정가 {ref:,}원 대비 "
                f"{diff:,}원(+{pct}%) 높습니다. "
                f"부품 등급(순정A/호환B/재생C)을 확인하세요."
            )
        elif level == "low":
            suggestions.append(
                f"{desc} 부품비 {est:,}원 → 모비스 순정가 {ref:,}원보다 "
                f"{abs(diff):,}원 낮습니다. 호환(B등급) 또는 재생(C등급) 부품 "
                f"사용 가능성이 있으니, 견적서 부품 코드란의 등급 표기(A/B/C/D)를 확인하세요."
            )
    elif pc and not pc["match_reliable"]:
        suggestions.append(
            f"{desc}: 부품 비교 데이터의 정확도가 낮아 참고용으로만 활용하세요."
        )

    return " ".join(suggestions) if suggestions else None


# ─── 집계 ─────────────────────────────────────────────────────────────

def _build_summary_stats(item_results: list, lookup_result: dict) -> dict:
    """전체 집계 통계."""
    labor_estimates = []
    labor_references = []
    labor_above = 0
    labor_normal = 0
    labor_below = 0

    parts_estimates = []
    parts_references = []
    parts_above = 0
    parts_normal = 0
    parts_below = 0

    for ir in item_results:
        lc = ir.get("labor_comparison")
        if lc and lc.get("match_reliable"):
            labor_estimates.append(lc["estimate_price"])
            labor_references.append(lc["reference_price"])
            level = lc["level"]
            if level in ("slightly_high", "high", "very_high"):
                labor_above += 1
            elif level == "normal":
                labor_normal += 1
            else:
                labor_below += 1

        pc = ir.get("parts_comparison")
        if pc and pc.get("match_reliable"):
            parts_estimates.append(pc["estimate_price"])
            parts_references.append(pc["reference_price"])
            level = pc["level"]
            if level in ("slightly_high", "high", "very_high"):
                parts_above += 1
            elif level == "normal":
                parts_normal += 1
            else:
                parts_below += 1

    def overall_pct(estimates, references):
        total_ref = sum(references)
        if total_ref == 0:
            return 0.0
        total_est = sum(estimates)
        return round(((total_est - total_ref) / total_ref) * 100, 1)

    return {
        "labor_analysis": {
            "total_estimate": lookup_result.get("estimate_labor_total", 0),
            "comparable_estimate": sum(labor_estimates),
            "comparable_reference": sum(labor_references),
            "overall_deviation_pct": overall_pct(labor_estimates, labor_references),
            "items_above_normal": labor_above,
            "items_normal": labor_normal,
            "items_below_normal": labor_below,
        },
        "parts_analysis": {
            "total_estimate": lookup_result.get("estimate_parts_total", 0),
            "comparable_estimate": sum(parts_estimates),
            "comparable_reference": sum(parts_references),
            "overall_deviation_pct": overall_pct(parts_estimates, parts_references),
            "items_above_normal": parts_above,
            "items_normal": parts_normal,
            "items_below_normal": parts_below,
        },
    }


# ─── 전체 제안 & 판정 ──────────────────────────────────────────────────

def _generate_overall_suggestions(coverage: dict, aggregate: dict, item_results: list) -> list[str]:
    """전체 한국어 제안 목록."""
    suggestions = []
    total = coverage["total_items"]
    comparable = coverage["labor_comparable"] + coverage["parts_comparable"]
    not_comparable = coverage["not_comparable"]
    cov_pct = coverage["coverage_pct"]

    # 커버리지
    if cov_pct < MIN_COVERAGE_PCT:
        suggestions.append(
            f"전체 {total}개 항목 중 {comparable}개({cov_pct:.0f}%)만 가격 비교가 가능했습니다. "
            f"나머지 {not_comparable}개 항목은 공임나라/모비스에 해당 데이터가 없어 "
            f"검증 범위가 제한적입니다."
        )

    # 공임 요약
    la = aggregate["labor_analysis"]
    if la["comparable_reference"] > 0:
        lpct = la["overall_deviation_pct"]
        if lpct > THRESHOLD_NORMAL:
            suggestions.append(
                f"비교 가능한 공임 항목은 공임나라 기준 대비 평균 {lpct:+.1f}% 높은 수준입니다."
            )
        elif lpct < -THRESHOLD_NORMAL:
            suggestions.append(
                f"비교 가능한 공임 항목은 공임나라 기준 대비 평균 {abs(lpct):.1f}% 낮은 수준입니다."
            )
        else:
            suggestions.append(
                f"비교 가능한 공임 항목은 공임나라 기준 대비 평균 {lpct:+.1f}% 수준으로 적정 범위입니다."
            )

    # 부품 요약
    pa = aggregate["parts_analysis"]
    if pa["comparable_reference"] > 0:
        ppct = pa["overall_deviation_pct"]
        if ppct > THRESHOLD_NORMAL:
            suggestions.append(
                f"비교 가능한 부품 항목은 모비스 정가 대비 평균 {ppct:+.1f}% 높습니다."
            )
        elif ppct < -THRESHOLD_NORMAL:
            suggestions.append(
                f"비교 가능한 부품 항목은 모비스 정가 대비 평균 {abs(ppct):.1f}% 낮습니다."
            )
        else:
            suggestions.append(
                f"비교 가능한 부품 항목은 모비스 정가 대비 평균 {ppct:+.1f}% 수준으로 적정 범위입니다."
            )

    # 높은 항목 요약
    high_items = []
    total_diff = 0
    for ir in item_results:
        for comp_key in ("labor_comparison", "parts_comparison"):
            comp = ir.get(comp_key)
            if comp and comp.get("match_reliable") and comp["level"] in ("high", "very_high"):
                high_items.append(ir["raw_description"])
                total_diff += comp["deviation_krw"]

    if high_items:
        item_list = ", ".join(high_items[:5])
        suggestions.append(
            f"기준가 대비 높은 항목 {len(high_items)}건의 총 차액은 {total_diff:,}원입니다. "
            f"정비소에 각 항목의 단가 산출 근거를 문의하세요: {item_list}"
        )

    # 부품번호 없는 항목
    no_ptno_count = sum(
        1 for ir in item_results
        if ir.get("parts_comparison") and ir["parts_comparison"].get("search_type") == "part_name"
    )
    if no_ptno_count > 0:
        suggestions.append(
            f"부품번호 없이 부품명으로만 조회한 항목이 {no_ptno_count}건 있습니다. "
            f"정비소에 견적서 부품 코드란 기재를 요청하면"
            f"(자동차관리법 제58조 의무) 모비스 정가와 1:1 비교가 가능합니다."
        )

    return suggestions


def _compute_verdict(coverage: dict, aggregate: dict) -> dict:
    """최종 판정 — 공임/부품 별도 판정 후 종합."""
    cov_pct = coverage["coverage_pct"]

    if cov_pct < MIN_COVERAGE_PCT:
        return {
            "level": "insufficient_data",
            "level_kr": VERDICT_KR["insufficient_data"],
            "summary_kr": (
                f"비교 가능한 항목이 전체의 {cov_pct:.0f}%에 불과하여 "
                f"견적 전체에 대한 판단이 어렵습니다."
            ),
        }

    la = aggregate["labor_analysis"]
    pa = aggregate["parts_analysis"]

    lpct = la["overall_deviation_pct"]
    ppct = pa["overall_deviation_pct"]
    has_labor = la["comparable_reference"] > 0
    has_parts = pa["comparable_reference"] > 0

    if not has_labor and not has_parts:
        return {
            "level": "insufficient_data",
            "level_kr": VERDICT_KR["insufficient_data"],
            "summary_kr": "신뢰할 수 있는 비교 항목이 없어 판단이 어렵습니다.",
        }

    # 공임/부품 각각 판정
    labor_level = _categorize_deviation(lpct) if has_labor else "normal"
    parts_level = _categorize_deviation(ppct) if has_parts else "normal"

    # 둘 중 더 심각한 쪽이 전체 판정
    level_severity = {"normal": 0, "slightly_low": 0, "low": 0,
                      "slightly_high": 1, "high": 2, "very_high": 3}
    labor_sev = level_severity.get(labor_level, 0)
    parts_sev = level_severity.get(parts_level, 0)
    max_sev = max(labor_sev, parts_sev)

    # summary 문장 구성
    parts_summary = []
    if has_labor:
        parts_summary.append(f"공임은 공임나라 대비 평균 {lpct:+.1f}%")
    if has_parts:
        parts_summary.append(f"부품은 모비스 정가 대비 평균 {ppct:+.1f}%")
    comparison_text = ", ".join(parts_summary)

    if max_sev == 0:
        return {
            "level": "reasonable",
            "level_kr": VERDICT_KR["reasonable"],
            "summary_kr": f"비교된 항목 기준, {comparison_text} 수준으로 적정 범위입니다.",
        }
    elif max_sev == 1:
        # 어느 쪽이 다소 높은지 명시
        high_side = "공임" if labor_sev >= parts_sev else "부품"
        return {
            "level": "slightly_high",
            "level_kr": VERDICT_KR["slightly_high"],
            "summary_kr": (
                f"비교된 항목 기준, {comparison_text} 수준입니다. "
                f"{high_side}이 다소 높으니 해당 항목을 확인해보세요."
            ),
        }
    else:
        high_side = "공임" if labor_sev >= parts_sev else "부품"
        return {
            "level": "high",
            "level_kr": VERDICT_KR["high"],
            "summary_kr": (
                f"비교된 항목 기준, {comparison_text} 수준입니다. "
                f"{high_side}이 기준가 대비 높으니 정비소에 산정 근거를 확인하세요."
            ),
        }


# ─── 메인 ─────────────────────────────────────────────────────────────

def verify_estimate(lookup_result: dict) -> dict:
    """
    smart_lookup 출력을 받아 검증 리포트를 반환한다.

    Args:
        lookup_result: run_smart_lookup() 반환값

    Returns:
        검증 리포트 dict
    """
    items = lookup_result.get("items", [])

    # 항목별 검증
    item_results = []
    labor_comparable = 0
    parts_comparable = 0
    not_comparable = 0

    for item in items:
        eff_cat = _classify_item(item)

        if eff_cat == "zero_price":
            item_results.append({
                "line_number": item.get("line_number", 0),
                "raw_description": item.get("raw_description", ""),
                "estimate_labor": 0,
                "estimate_parts": 0,
                "estimate_total": 0,
                "effective_category": "zero_price",
                "labor_comparison": None,
                "parts_comparison": None,
                "suggestion": None,
                "status": "skipped",
            })
            continue

        quality = _assess_match_quality(item)
        lc = _compare_labor(item, quality) if eff_cat in ("labor_only", "combined") else None
        pc = _compare_parts(item, quality) if eff_cat in ("part_only", "combined") else None

        # 상태 결정
        has_any = lc is not None or pc is not None
        if has_any:
            reliable_any = (lc and lc["match_reliable"]) or (pc and pc["match_reliable"])
            if reliable_any:
                status = "comparable"
                if lc and lc["match_reliable"]:
                    labor_comparable += 1
                if pc and pc["match_reliable"]:
                    parts_comparable += 1
            else:
                status = "low_confidence"
                not_comparable += 1
        else:
            # 도장 항목 체크
            cat = item.get("item_category", "")
            if cat == "painting":
                status = "painting"
            else:
                status = "no_reference"
            not_comparable += 1

        ir = {
            "line_number": item.get("line_number", 0),
            "raw_description": item.get("raw_description", ""),
            "estimate_labor": item.get("estimate_labor", 0) or 0,
            "estimate_parts": item.get("estimate_parts", 0) or 0,
            "estimate_total": item.get("estimate_total", 0) or 0,
            "effective_category": eff_cat,
            "labor_comparison": lc,
            "parts_comparison": pc,
            "suggestion": None,
            "status": status,
        }

        if status == "painting":
            ir["status_reason"] = "도장 항목 — 표준 비교 기준이 없습니다."
        elif status == "no_reference":
            ir["status_reason"] = "비교 데이터 없음 — 공임나라/모비스에서 해당 항목을 찾지 못했습니다."

        ir["suggestion"] = _generate_item_suggestion(ir)
        item_results.append(ir)

    # 커버리지
    total_items = len(items)
    comparable_items = labor_comparable + parts_comparable
    # 중복 카운트 제거를 위해 실제 비교 가능 항목 수 계산
    comparable_unique = sum(1 for ir in item_results if ir["status"] == "comparable")
    coverage_pct = round((comparable_unique / total_items * 100), 1) if total_items > 0 else 0

    coverage = {
        "labor_comparable": labor_comparable,
        "parts_comparable": parts_comparable,
        "not_comparable": not_comparable,
        "total_items": total_items,
        "coverage_pct": coverage_pct,
    }

    # 집계
    aggregate = _build_summary_stats(item_results, lookup_result)

    # 전체 제안
    suggestions = _generate_overall_suggestions(coverage, aggregate, item_results)

    # 최종 판정
    verdict = _compute_verdict(coverage, aggregate)

    return {
        "verification_version": "1.0.0",
        "verified_at": datetime.now(KST).isoformat(),
        "input_summary": {
            "vehicle_model": lookup_result.get("vehicle_model", ""),
            "maker": lookup_result.get("maker", ""),
            "estimate_grand_total": lookup_result.get("estimate_grand_total", 0),
            "estimate_parts_total": lookup_result.get("estimate_parts_total", 0),
            "estimate_labor_total": lookup_result.get("estimate_labor_total", 0),
            "total_items": total_items,
        },
        "coverage": coverage,
        "items": item_results,
        "aggregate": aggregate,
        "suggestions": suggestions,
        "overall_verdict": verdict,
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("사용법: python verify_estimate.py smart_lookup_result.json")
        sys.exit(1)

    input_path = Path(sys.argv[1])
    if not input_path.exists():
        print(f"파일을 찾을 수 없습니다: {input_path}", file=sys.stderr)
        sys.exit(1)

    with open(input_path, encoding="utf-8") as f:
        lookup_result = json.load(f)

    report = verify_estimate(lookup_result)
    print(json.dumps(report, ensure_ascii=False, indent=2))
