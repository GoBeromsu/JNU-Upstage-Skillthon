#!/usr/bin/env python3
"""
recommend.py — 클린알바맵 지능형 검색 및 맞춤 추천

사용자 입력을 SEARCH / RECOMMEND 두 의도로 분류한 뒤 알맞은 결과를 반환한다.

사용법:
    python recommend.py "스타벅스"                          # SEARCH
    python recommend.py "상대 카페"                         # SEARCH
    python recommend.py "주휴수당 챙겨주는 예대 카페"        # RECOMMEND
    python recommend.py "클린지수 높은 편의점 알바 추천해줘" # RECOMMEND
    echo '{"query": "..."}' | python recommend.py
"""

import os, sys, json
from pathlib import Path
from openai import OpenAI

UPSTAGE_API_KEY = os.environ.get("UPSTAGE_API_KEY")
if not UPSTAGE_API_KEY:
    print(json.dumps({"error": "UPSTAGE_API_KEY 환경변수가 설정되지 않았습니다."}, ensure_ascii=False))
    sys.exit(1)

client = OpenAI(api_key=UPSTAGE_API_KEY, base_url="https://api.upstage.ai/v1")

DATA_DIR = Path(__file__).parent.parent / "data"

CRITERIA_KEYS = [
    "근로계약서 미작성",
    "최저시급 미준수",
    "주휴수당 미지급",
    "휴게시간 부족",
    "급여 지급 지연",
    "사전 협의 없는 스케줄 변경",
    "반복적이고 지속적인 대타 요구 및 강요",
    "초과근무 급여 미지급",
]

CRITERIA_POSITIVE = {
    "근로계약서 미작성": "근로계약서 작성",
    "최저시급 미준수": "최저시급 준수",
    "주휴수당 미지급": "주휴수당 지급",
    "휴게시간 부족": "충분한 휴게시간 보장",
    "급여 지급 지연": "정시 급여지급",
    "사전 협의 없는 스케줄 변경": "사전 협의된 스케줄 관리",
    "반복적이고 지속적인 대타 요구 및 강요": "합리적인 대타 요청",
    "초과근무 급여 미지급": "초과근무 급여 지급",
}

# 상권 별칭 → 정식 상권명 매핑
AREA_ALIASES: dict[str, str] = {
    "상대": "상대",
    "상과대": "상대",
    "예대": "예대",
    "예술대": "예대",
    "정문": "정문",
    "전남대 정문": "정문",
    "후문": "후문",
    "전남대 후문": "후문",
    "전철우": "전철우",
    "전철우 사거리": "전철우",
}

def normalize_area(area: str | None) -> str | None:
    if not area:
        return area
    return AREA_ALIASES.get(area.strip(), area.strip())

# ── 스키마 ──────────────────────────────────────────────────────────────

INTENT_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "intent_classification",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "intent": {
                    "type": "string",
                    "description": "SEARCH 또는 RECOMMEND",
                },
                "search_term": {
                    "type": ["string", "null"],
                    "description": "SEARCH인 경우 검색할 핵심 키워드 (업체명·상권명·업종명). RECOMMEND이면 null.",
                },
            },
            "required": ["intent", "search_term"],
            "additionalProperties": False,
        },
    },
}

PARSE_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "parsed_preferences",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "area": {"type": ["string", "null"], "description": "상권명 (상대/예대/정문/후문/전철우) 또는 null"},
                "industry": {"type": ["string", "null"], "description": "업종명 또는 null"},
                "min_clean_score": {"type": ["integer", "null"], "description": "최소 클린지수 (0–100) 또는 null"},
                "avoid_list": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "기피 위반 항목 목록",
                },
            },
            "required": ["area", "industry", "min_clean_score", "avoid_list"],
            "additionalProperties": False,
        },
    },
}

RECOMMEND_SCHEMA = {
    "type": "json_schema",
    "json_schema": {
        "name": "recommendation_result",
        "strict": True,
        "schema": {
            "type": "object",
            "properties": {
                "recommendations": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "rank": {"type": "integer"},
                            "name": {"type": "string"},
                            "area": {"type": "string"},
                            "industry": {"type": "string"},
                            "clean_score": {"type": "integer"},
                            "review_count": {"type": "integer"},
                            "highlights": {"type": "array", "items": {"type": "string"}},
                            "cautions": {"type": "array", "items": {"type": "string"}},
                            "reason": {"type": "string"},
                        },
                        "required": ["rank", "name", "area", "industry", "clean_score",
                                     "review_count", "highlights", "cautions", "reason"],
                        "additionalProperties": False,
                    },
                },
                "summary": {"type": "string"},
            },
            "required": ["recommendations", "summary"],
            "additionalProperties": False,
        },
    },
}

# ── 시스템 프롬프트 ─────────────────────────────────────────────────────

INTENT_SYSTEM = """당신은 클린알바맵 검색 의도 분류 전문가입니다.
사용자 입력이 '단순 검색'인지 '맞춤 추천'인지 분류하세요.

SEARCH (단순 검색): 특정 업체명, 브랜드명, 상권명, 업종명 등 명사형 단순 입력
  예) "스타벅스", "상대 카페", "GS25", "예대", "편의점"

RECOMMEND (맞춤 추천): 알바 조건·근무환경·복지를 포함하는 문장형 또는 복합 조건 입력
  예) "주휴수당 챙겨주는 카페", "휴게시간 넉넉한 곳 추천", "클린지수 80 이상 예대 알바"

SEARCH인 경우 search_term에 핵심 검색 키워드를 추출하세요.
RECOMMEND인 경우 search_term은 null로 반환하세요."""

PARSE_SYSTEM = """당신은 알바 검색 조건 분석 전문가입니다.
사용자의 자연어 요청을 분석하여 검색 조건을 추출하세요.

상권 (정식명 → 별칭): 상대(상과대), 예대(예술대), 정문(전남대 정문), 후문(전남대 후문), 전철우(전철우 사거리)
별칭이 입력되어도 반드시 정식 상권명(상대/예대/정문/후문/전철우)으로 반환하세요.
업종: 카페, 식당, 편의점, 주점, 패스트푸드, 기타
기피 항목: 근로계약서 미작성, 최저시급 미준수, 주휴수당 미지급, 휴게시간 부족,
  급여 지급 지연, 사전 협의 없는 스케줄 변경, 반복적이고 지속적인 대타 요구 및 강요,
  초과근무 급여 미지급

명시되지 않은 값은 null로 반환하세요. 항상 한국어로 응답하세요."""

RECOMMEND_SYSTEM = """당신은 클린알바맵 추천 전문가입니다.
제공된 후보 업체 목록과 사용자 조건을 바탕으로 최대 3개 업체를 추천하세요.
각 업체는 누적 리뷰 통계에서 산출된 클린지수와 위반/준수 항목을 보유합니다.
highlights와 cautions는 8개 클린지수 산출 항목 기준만 사용하세요.
친근하고 실용적인 언어로 작성하세요. 항상 한국어로 응답하세요."""

# ── 데이터 로드 ─────────────────────────────────────────────────────────

def load_businesses() -> list:
    """data/ 폴더의 모든 업체 JSON을 로드하고 누적 리뷰 기반 highlights/cautions를 산출한다."""
    businesses = []
    for path in sorted(DATA_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            agg = data.get("aggregate", {})
            n = agg.get("review_count", 0)
            counts = agg.get("criteria_violation_counts", {})

            if n >= 2:
                cautions = [k for k in CRITERIA_KEYS if counts.get(k, 0) / n >= 0.3]
                highlights = [CRITERIA_POSITIVE[k] for k in CRITERIA_KEYS if counts.get(k, 0) == 0]
            elif n == 1:
                cautions = [k for k in CRITERIA_KEYS if counts.get(k, 0) > 0]
                highlights = [CRITERIA_POSITIVE[k] for k in CRITERIA_KEYS if counts.get(k, 0) == 0]
            else:
                cautions, highlights = [], []

            businesses.append({
                "business_id": data["business_id"],
                "name": data["name"],
                "area": data["area"],
                "industry": data["industry"],
                "lat": data.get("lat"),
                "lon": data.get("lon"),
                "clean_score": agg.get("clean_score", 100),
                "review_count": n,
                "highlights": highlights,
                "cautions": cautions,
            })
        except Exception:
            continue
    return businesses

# ── 의도 분류 ───────────────────────────────────────────────────────────

def classify_intent(query: str) -> dict:
    resp = client.chat.completions.create(
        model="solar-pro",
        messages=[
            {"role": "system", "content": INTENT_SYSTEM},
            {"role": "user", "content": query},
        ],
        response_format=INTENT_SCHEMA,
        temperature=0.0,
        max_tokens=128,
    )
    return json.loads(resp.choices[0].message.content)

# ── SEARCH 경로 ─────────────────────────────────────────────────────────

def search_businesses(search_term: str, businesses: list) -> list:
    """업체명·상권·업종에 대해 부분 문자열 매칭으로 검색한다. 상권 별칭도 정식명으로 정규화하여 검색한다."""
    term = search_term.strip().lower()
    canonical_area = normalize_area(search_term)  # 별칭이면 정식 상권명으로 변환
    results = [
        b for b in businesses
        if term in b["name"].lower()
        or b["area"] == canonical_area
        or term in b["area"].lower()
        or term in b["industry"].lower()
    ]
    return sorted(results, key=lambda x: x["clean_score"], reverse=True)


def handle_search(search_term: str, businesses: list) -> dict:
    results = search_businesses(search_term, businesses)
    return {
        "intent": "SEARCH",
        "search_term": search_term,
        "count": len(results),
        "results": results,
    }

# ── RECOMMEND 경로 ──────────────────────────────────────────────────────

def parse_preferences(query: str) -> dict:
    resp = client.chat.completions.create(
        model="solar-pro",
        messages=[
            {"role": "system", "content": PARSE_SYSTEM},
            {"role": "user", "content": query},
        ],
        response_format=PARSE_SCHEMA,
        temperature=0.1,
        max_tokens=256,
    )
    return json.loads(resp.choices[0].message.content)


def filter_candidates(businesses: list, prefs: dict) -> list:
    candidates = []
    for b in businesses:
        if prefs.get("area") and b["area"] != prefs["area"]:
            continue
        if prefs.get("industry") and b["industry"] != prefs["industry"]:
            continue
        if prefs.get("min_clean_score") and b["clean_score"] < prefs["min_clean_score"]:
            continue
        if prefs.get("avoid_list") and any(a in b["cautions"] for a in prefs["avoid_list"]):
            continue
        candidates.append(b)
    return sorted(candidates, key=lambda x: x["clean_score"], reverse=True)[:10]


def generate_recommendations(query: str, prefs: dict, candidates: list) -> dict:
    if not candidates:
        return {
            "intent": "RECOMMEND",
            "recommendations": [],
            "summary": "조건에 맞는 알바를 찾지 못했습니다. 조건을 완화하거나 다른 상권을 시도해보세요.",
            "parsed_preferences": prefs,
        }

    user_msg = (
        f"사용자 요청: {query}\n\n"
        f"파악된 조건: {json.dumps(prefs, ensure_ascii=False)}\n\n"
        f"후보 업체 (누적 리뷰 기반 클린지수 순):\n"
        f"{json.dumps(candidates, ensure_ascii=False, indent=2)}\n\n"
        "최대 3개를 추천하고 각 이유를 설명해주세요."
    )
    resp = client.chat.completions.create(
        model="solar-pro",
        messages=[
            {"role": "system", "content": RECOMMEND_SYSTEM},
            {"role": "user", "content": user_msg},
        ],
        response_format=RECOMMEND_SCHEMA,
        temperature=0.3,
        max_tokens=512,
    )
    result = json.loads(resp.choices[0].message.content)
    result["intent"] = "RECOMMEND"
    result["parsed_preferences"] = prefs
    return result


def handle_recommend(query: str, businesses: list) -> dict:
    prefs = parse_preferences(query)
    if prefs.get("area"):
        prefs["area"] = normalize_area(prefs["area"])  # LLM이 별칭을 반환한 경우 정규화
    candidates = filter_candidates(businesses, prefs)
    return generate_recommendations(query, prefs, candidates)

# ── 진입점 ──────────────────────────────────────────────────────────────

def main():
    raw_input = None   # hint 여부 확인에 재사용
    if not sys.stdin.isatty():
        raw = sys.stdin.read().strip()
        try:
            raw_input = json.loads(raw)
            query = raw_input.get("query", raw)
        except json.JSONDecodeError:
            query = raw
    elif len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    else:
        print(json.dumps({"error": "검색어 또는 조건을 입력해주세요."}, ensure_ascii=False))
        sys.exit(1)

    if not query.strip():
        print(json.dumps({"error": "빈 텍스트는 처리할 수 없습니다."}, ensure_ascii=False))
        sys.exit(1)

    businesses = load_businesses()
    if not businesses:
        print(json.dumps({
            "error": "등록된 사업장이 없습니다. add_review.py로 리뷰를 추가해주세요."
        }, ensure_ascii=False))
        sys.exit(1)

    # hint=RECOMMEND 가 전달된 경우 의도 분류 LLM 호출 생략 (서버에서 이미 판별)
    if isinstance(raw_input, dict) and raw_input.get("hint") == "RECOMMEND":
        result = handle_recommend(query, businesses)
    else:
        intent_info = classify_intent(query)
        if intent_info["intent"] == "SEARCH":
            result = handle_search(intent_info["search_term"] or query, businesses)
        else:
            result = handle_recommend(query, businesses)

    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
