# -*- coding: utf-8 -*-
"""
자동차 정비 견적서 검증 파이프라인

사진 한 장 입력 → OCR → 차량 매칭 → 가격 조회 → 동의어 보강 → 검증 → Solar 추정 → 리포트

사용법:
    python run_pipeline.py 견적서.jpg
    python run_pipeline.py 견적서.jpg --vehicle "레이 2015"
    python run_pipeline.py 견적서.jpg --output report.md
    python run_pipeline.py 견적서.jpg --json
    python run_pipeline.py 견적서.jpg --save-intermediate
    python run_pipeline.py p1.jpg p2.jpg p3.jpg  # 다중 페이지
"""

import json
import os
import sys
import time
import argparse
from pathlib import Path

# ─── 의존성 체크 ──────────────────────────────────────────────────────

def _check_dependencies():
    """필수 의존성 체크. 없으면 안내 후 중단."""
    missing = []

    try:
        from openai import OpenAI
    except ImportError:
        missing.append("openai (pip install openai)")

    try:
        from dotenv import load_dotenv
    except ImportError:
        missing.append("python-dotenv (pip install python-dotenv)")

    try:
        import requests
    except ImportError:
        missing.append("requests (pip install requests)")

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        missing.append("playwright (pip install playwright && playwright install chromium)")

    if missing:
        print("필수 패키지가 설치되지 않았습니다:", file=sys.stderr)
        for m in missing:
            print(f"  - {m}", file=sys.stderr)
        print("\n설치 후 다시 실행하세요.", file=sys.stderr)
        sys.exit(1)

    # Playwright chromium 브라우저 체크
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            browser.close()
    except Exception as e:
        if "Executable doesn't exist" in str(e) or "browserType.launch" in str(e):
            print("Playwright Chromium 브라우저가 설치되지 않았습니다.", file=sys.stderr)
            print("  실행: playwright install chromium", file=sys.stderr)
            sys.exit(1)


# ─── .env 로드 ────────────────────────────────────────────────────────

SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent.parent

from dotenv import load_dotenv
for env_path in [
    PROJECT_ROOT / "skills" / "solar-skill-creator" / "assets" / ".env",
    SCRIPT_DIR.parent / "assets" / ".env",
]:
    if env_path.exists():
        load_dotenv(env_path)
        break

if not os.getenv("UPSTAGE_API_KEY"):
    print("UPSTAGE_API_KEY가 설정되지 않았습니다.", file=sys.stderr)
    print("skills/solar-skill-creator/assets/.env 파일을 확인하세요.", file=sys.stderr)
    sys.exit(1)


# ─── 모듈 import ──────────────────────────────────────────────────────

from parse_estimate_ie import parse_estimate_ie
from match_vehicle_model import match_vehicle_model
from smart_lookup import run_smart_lookup
from enhance_with_synonyms import enhance_lookup_result
from verify_estimate import verify_estimate
from generate_report import generate_report


# ─── 파이프라인 ───────────────────────────────────────────────────────

def run_pipeline(
    image_paths: list[str],
    vehicle_hint: str = "",
    save_intermediate: bool = False,
    output_dir: str = "",
) -> dict:
    """
    견적서 이미지 → 검증 리포트 전체 파이프라인.

    Args:
        image_paths: 견적서 이미지 파일 경로 리스트 (1장 또는 다중 페이지)
        vehicle_hint: 차량명 힌트 (OCR에서 못 읽었을 때 사용)
        save_intermediate: 중간 결과 JSON 저장 여부
        output_dir: 중간 결과 저장 디렉토리

    Returns:
        {"report_md": str, "verify_result": dict, "ocr_result": dict,
         "vehicle_match": dict, "lookup_result": dict, "api_calls": dict}
    """
    api_calls = {"information_extract": 0, "solar_chat": 0, "gongim": 0, "mobis": 0}
    t_start = time.time()
    base_name = Path(image_paths[0]).stem

    # ── Step 1: OCR ──
    print(f"[1/6] OCR 처리 중... ({len(image_paths)}장)", file=sys.stderr)
    t1 = time.time()

    if len(image_paths) == 1:
        ocr_result = parse_estimate_ie(image_paths[0])
        api_calls["information_extract"] = 1
    else:
        # 다중 페이지: 각각 OCR → items 합치기
        merged_items = []
        base_result = None
        for i, img_path in enumerate(image_paths):
            print(f"  페이지 {i+1}/{len(image_paths)}: {img_path}", file=sys.stderr)
            result = parse_estimate_ie(img_path)
            api_calls["information_extract"] += 1
            if base_result is None:
                base_result = result
            items = result.get("items", [])
            # 라인 번호 이어 붙이기
            offset = len(merged_items)
            for item in items:
                item["line_number"] = offset + item.get("line_number", 1)
            merged_items.extend(items)
        base_result["items"] = merged_items
        ocr_result = base_result

    print(f"  → {len(ocr_result.get('items', []))}개 항목 추출 ({time.time()-t1:.1f}초)", file=sys.stderr)

    if save_intermediate:
        _save_json(ocr_result, output_dir, f"{base_name}_ocr.json")

    if not ocr_result.get("items"):
        return {"error": "OCR에서 정비 항목을 추출하지 못했습니다.", "ocr_result": ocr_result}

    # ── Step 2: 차량 매칭 ──
    print("[2/6] 차량 모델 매칭 중...", file=sys.stderr)
    t2 = time.time()

    vehicle_name = vehicle_hint or ocr_result.get("vehicle_car_model", "")
    if not vehicle_name:
        print("  ⚠ 차량명을 찾을 수 없습니다. --vehicle 옵션으로 지정하세요.", file=sys.stderr)
        vehicle_match = {"matched_name": None, "cat_seq": None, "maker": None}
    else:
        vehicle_match = match_vehicle_model(vehicle_name)
        api_calls["solar_chat"] += 1
        matched = vehicle_match.get("matched_name")
        cat_seq = vehicle_match.get("cat_seq")
        if matched:
            print(f"  → '{vehicle_name}' → '{matched}' (catSeq={cat_seq})", file=sys.stderr)
        else:
            print(f"  ⚠ '{vehicle_name}' 매칭 실패. 모비스 부품명 검색 불가 (부품번호만 가능)", file=sys.stderr)

    print(f"  ({time.time()-t2:.1f}초)", file=sys.stderr)

    maker = vehicle_match.get("maker") or "H"
    cat_seq = vehicle_match.get("cat_seq") or ""
    vehicle_model = vehicle_match.get("matched_name") or vehicle_name

    # ── Step 3: 가격 조회 (공임나라 웹 조회 + 모비스 웹 조회) ──
    print("[3/6] 가격 조회 중 (공임나라 + 모비스)...", file=sys.stderr)
    t3 = time.time()

    lookup_result = run_smart_lookup(
        ocr_result, maker=maker, cat_seq=cat_seq, vehicle_model=vehicle_model
    )
    # smart_lookup 내부에서 Solar Chat N회 + 공임나라 M회 + 모비스 호출
    n_items = len(ocr_result.get("items", []))
    api_calls["solar_chat"] += n_items  # 항목당 1회

    print(f"  ({time.time()-t3:.1f}초)", file=sys.stderr)

    if save_intermediate:
        _save_json(lookup_result, output_dir, f"{base_name}_lookup.json")

    # ── Step 4: 동의어 사전 매핑 (미매칭 항목 재조회) ──
    print("[4/6] 동의어 사전 매핑으로 미매칭 항목 재조회 중...", file=sys.stderr)
    t4 = time.time()

    enhanced_result = enhance_lookup_result(lookup_result)

    print(f"  ({time.time()-t4:.1f}초)", file=sys.stderr)

    if save_intermediate:
        _save_json(enhanced_result, output_dir, f"{base_name}_enhanced.json")

    # ── Step 5: 검증 ──
    print("[5/6] 검증 분석 중...", file=sys.stderr)
    t5 = time.time()

    verify_result = verify_estimate(enhanced_result)

    print(f"  → 커버리지: {verify_result['coverage']['coverage_pct']:.0f}%, "
          f"판정: {verify_result['overall_verdict']['level_kr']}",
          file=sys.stderr)
    print(f"  ({time.time()-t5:.1f}초)", file=sys.stderr)

    if save_intermediate:
        _save_json(verify_result, output_dir, f"{base_name}_verify.json")

    # 비교불가 항목 안내
    unmatched_count = sum(1 for it in verify_result["items"]
                         if it["status"] in ("no_reference", "low_confidence"))
    if unmatched_count > 0:
        print(f"  ⚠ 비교불가 항목 {unmatched_count}건 — 에이전트 웹 검색으로 보충 필요", file=sys.stderr)

    # ── Step 6: 리포트 생성 ──
    print("[6/6] 리포트 생성 중...", file=sys.stderr)
    report_md = generate_report(verify_result)

    elapsed = time.time() - t_start
    print(f"\n✅ 완료 ({elapsed:.1f}초)", file=sys.stderr)
    print(f"API 호출: IE {api_calls['information_extract']}회, "
          f"Solar Chat ~{api_calls['solar_chat']}회, "
          f"공임나라 {api_calls['gongim']}회",
          file=sys.stderr)

    return {
        "report_md": report_md,
        "verify_result": verify_result,
        "ocr_result": ocr_result,
        "vehicle_match": vehicle_match,
        "lookup_result": enhanced_result,
        "api_calls": api_calls,
        "elapsed_seconds": elapsed,
    }


def _save_json(data: dict, output_dir: str, filename: str):
    """중간 결과 JSON 저장."""
    dir_path = Path(output_dir) if output_dir else Path(".")
    dir_path.mkdir(parents=True, exist_ok=True)
    path = dir_path / filename
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    print(f"  💾 저장: {path}", file=sys.stderr)


# ─── CLI ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="자동차 정비 견적서 검증 파이프라인",
        epilog="예시: python run_pipeline.py 견적서.jpg --vehicle '레이 2015' --output report.md"
    )
    parser.add_argument("images", nargs="+", help="견적서 이미지 파일 경로 (1장 또는 다중 페이지)")
    parser.add_argument("--vehicle", default="", help="차량명 힌트 (OCR에서 못 읽었을 때)")
    parser.add_argument("--output", "-o", default="", help="리포트 저장 경로 (.md)")
    parser.add_argument("--json", action="store_true", help="JSON 결과 출력 (리포트 대신)")
    parser.add_argument("--save-intermediate", action="store_true", help="중간 결과 JSON 저장")
    parser.add_argument("--skip-dep-check", action="store_true", help="의존성 체크 스킵")
    args = parser.parse_args()

    # 이미지 파일 존재 확인
    for img in args.images:
        if not Path(img).exists():
            print(f"파일을 찾을 수 없습니다: {img}", file=sys.stderr)
            sys.exit(1)

    # 의존성 체크
    if not args.skip_dep_check:
        _check_dependencies()

    # 파이프라인 실행
    output_dir = str(Path(args.output).parent) if args.output else str(Path(args.images[0]).parent)

    result = run_pipeline(
        image_paths=args.images,
        vehicle_hint=args.vehicle,
        save_intermediate=args.save_intermediate,
        output_dir=output_dir,
    )

    if "error" in result:
        print(f"오류: {result['error']}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        # JSON 출력 (report_md 제외)
        output = {k: v for k, v in result.items() if k != "report_md"}
        print(json.dumps(output, ensure_ascii=False, indent=2))
    elif args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(result["report_md"])
        print(f"리포트 저장: {args.output}", file=sys.stderr)
    else:
        print(result["report_md"])
