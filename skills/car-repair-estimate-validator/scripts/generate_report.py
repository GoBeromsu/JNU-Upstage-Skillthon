# -*- coding: utf-8 -*-
"""
검증 리포트 생성 — verify_estimate JSON → 한국어 마크다운 리포트

사용법:
    python generate_report.py verify_result.json
    python generate_report.py verify_result.json --format text   # 플레인 텍스트
"""

import json
import sys
import argparse
from pathlib import Path


def _fmt_krw(amount: int) -> str:
    """금액을 한국 원화 형식으로 포맷."""
    return f"{amount:,}원"


def _deviation_badge(level: str, level_kr: str = "") -> str:
    """편차 레벨을 시각적 배지로 변환."""
    badges = {
        "very_high": "🔴 매우 높음",
        "high": "🟠 높음",
        "slightly_high": "🟡 다소 높음",
        "normal": "🟢 적정",
        "slightly_low": "🔵 다소 낮음",
        "low": "🔵 낮음",
    }
    return badges.get(level, level_kr or level)


def _verdict_badge(level: str) -> str:
    """전체 판정 배지."""
    badges = {
        "reasonable": "✅ 적정",
        "slightly_high": "⚠️ 다소 높음",
        "high": "🚨 높음",
        "mixed": "⚠️ 항목별 편차 있음",
        "insufficient_data": "ℹ️ 데이터 부족",
    }
    return badges.get(level, level)


def generate_report(verify_result: dict, use_emoji: bool = True) -> str:
    """
    verify_estimate 결과를 한국어 마크다운 리포트로 변환.

    Args:
        verify_result: verify_estimate() 반환값
        use_emoji: 이모지 사용 여부

    Returns:
        마크다운 문자열
    """
    lines = []
    inp = verify_result["input_summary"]
    cov = verify_result["coverage"]
    agg = verify_result["aggregate"]
    verdict = verify_result["overall_verdict"]
    items = verify_result["items"]

    # ── 제목 ──
    lines.append("# 자동차 정비 견적서 검증 리포트")
    lines.append("")

    # ── 기본 정보 ──
    lines.append("## 기본 정보")
    lines.append(f"- **차량**: {inp['vehicle_model']}")
    lines.append(f"- **견적 총액**: {_fmt_krw(inp['estimate_grand_total'])}")
    parts_total = inp.get("estimate_parts_total", 0)
    labor_total = inp.get("estimate_labor_total", 0)
    if parts_total or labor_total:
        lines.append(f"  - 부품: {_fmt_krw(parts_total)} / 공임: {_fmt_krw(labor_total)}")
    lines.append(f"- **검증 항목**: 전체 {cov['total_items']}개 중 "
                 f"공임 {cov['labor_comparable']}개, 부품 {cov['parts_comparable']}개 비교 가능 "
                 f"({cov['coverage_pct']:.0f}%)")
    lines.append("")

    # ── 종합 판정 ──
    lines.append("## 종합 판정")
    badge = _verdict_badge(verdict["level"]) if use_emoji else verdict["level_kr"]
    lines.append(f"**{badge}**")
    lines.append("")
    lines.append(f"> {verdict['summary_kr']}")
    lines.append("")

    # ── 공임 비교 테이블 ──
    labor_items = [it for it in items
                   if it.get("labor_comparison") and it["labor_comparison"].get("match_reliable")]
    if labor_items:
        lines.append("## 공임 비교")
        lines.append("")
        lines.append("| 항목 | 견적 공임 | 공임나라 기준 | 편차 | 판정 |")
        lines.append("|------|----------|-------------|------|------|")
        for it in labor_items:
            lc = it["labor_comparison"]
            desc = it["raw_description"]
            if len(desc) > 20:
                desc = desc[:18] + ".."
            badge = _deviation_badge(lc["level"]) if use_emoji else lc["level_kr"]
            lines.append(
                f"| {desc} | {_fmt_krw(lc['estimate_price'])} | "
                f"{_fmt_krw(lc['reference_price'])} | "
                f"{lc['deviation_pct']:+.1f}% | {badge} |"
            )
        lines.append("")

    # ── 부품 비교 테이블 ──
    parts_items = [it for it in items
                   if it.get("parts_comparison") and it["parts_comparison"].get("match_reliable")]
    if parts_items:
        lines.append("## 부품 비교")
        lines.append("")
        lines.append("| 항목 | 수량 | 견적 부품비 | 모비스 정가 | 편차 | 판정 |")
        lines.append("|------|------|-----------|-----------|------|------|")
        for it in parts_items:
            pc = it["parts_comparison"]
            desc = it["raw_description"]
            if len(desc) > 20:
                desc = desc[:18] + ".."
            qty = pc.get("quantity", 1)
            badge = _deviation_badge(pc["level"]) if use_emoji else pc["level_kr"]
            lines.append(
                f"| {desc} | {qty} | {_fmt_krw(pc['estimate_price'])} | "
                f"{_fmt_krw(pc['reference_price'])} | "
                f"{pc['deviation_pct']:+.1f}% | {badge} |"
            )
        lines.append("")

    # ── Solar Chat 추정 (비교불가/저신뢰 항목) ──
    solar_items = [it for it in items if it.get("solar_estimate")]
    if solar_items:
        lines.append("## Solar Chat 가격 추정 (참고용)")
        lines.append("")
        lines.append("> 공임나라/모비스에서 직접 비교할 수 없는 항목에 대해 Solar Chat AI가 시장 가격을 추정한 결과입니다.")
        lines.append("")
        lines.append("| 항목 | 견적가 | 추정 범위 | 판정 | 추정 근거 |")
        lines.append("|------|--------|----------|------|----------|")
        for it in solar_items:
            se = it["solar_estimate"]
            desc = it["raw_description"]
            if len(desc) > 18:
                desc = desc[:16] + ".."
            est_price = it.get("estimate_labor", 0) or it.get("estimate_parts", 0) or it.get("estimate_total", 0)
            p_min = se.get("price_min", 0)
            p_max = se.get("price_max", 0)
            verdict = se.get("verdict", "")
            basis = se.get("reference_basis", "")
            if len(basis) > 25:
                basis = basis[:23] + ".."
            lines.append(
                f"| {desc} | {_fmt_krw(est_price)} | "
                f"{_fmt_krw(p_min)}~{_fmt_krw(p_max)} | {verdict} | {basis} |"
            )
        lines.append("")

    # ── 비교 불가 항목 (Solar 추정도 없는 경우) ──
    no_ref_items = [it for it in items
                    if it["status"] in ("no_reference", "painting") and not it.get("solar_estimate")]
    if no_ref_items:
        lines.append("## 비교 불가 항목")
        lines.append("")
        for it in no_ref_items:
            reason = it.get("status_reason", "비교 데이터 없음")
            total = it.get("estimate_total", 0)
            lines.append(f"- **{it['raw_description']}** ({_fmt_krw(total)}) — {reason}")
        lines.append("")

    # ── 주의 항목 상세 ──
    attention_items = [it for it in items if it.get("suggestion")]
    if attention_items:
        lines.append("## 항목별 상세")
        lines.append("")
        for it in attention_items:
            lines.append(f"- {it['suggestion']}")
        lines.append("")

    # ── 종합 제안 ──
    if verify_result["suggestions"]:
        lines.append("## 종합 제안")
        lines.append("")
        for s in verify_result["suggestions"]:
            lines.append(f"- {s}")
        lines.append("")

    # ── 참고 사항 ──
    lines.append("---")
    lines.append("")
    lines.append("*이 리포트는 공임나라 표준 공임비와 현대모비스 순정 부품가를 기준으로 작성되었습니다. "
                 "실제 정비 비용은 정비소 위치, 차량 상태, 부품 등급(순정/호환/재생)에 따라 달라질 수 있습니다.*")
    lines.append("")

    return "\n".join(lines)


def generate_text_report(verify_result: dict) -> str:
    """이모지 없는 플레인 텍스트 리포트."""
    return generate_report(verify_result, use_emoji=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="검증 리포트 생성")
    parser.add_argument("verify_json", help="verify_estimate 결과 JSON 파일")
    parser.add_argument("--format", choices=["markdown", "text"], default="markdown",
                        help="출력 형식 (기본: markdown)")
    args = parser.parse_args()

    path = Path(args.verify_json)
    if not path.exists():
        print(f"파일을 찾을 수 없습니다: {path}", file=sys.stderr)
        sys.exit(1)

    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    if args.format == "text":
        print(generate_text_report(data))
    else:
        print(generate_report(data))
