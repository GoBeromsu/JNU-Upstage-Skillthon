# -*- coding: utf-8 -*-
"""
방법 C: 네이버 쇼핑 검색으로 부품/소모품 시장가 조회

네이버 쇼핑 BFF API (공개 엔드포인트, 키 불필요)를 직접 호출하여
비교불가 항목의 시장 가격을 검색한다.
"""

import json
import sys
import time
import requests

# 비교불가 항목 13건
UNMATCHED_ITEMS = [
    {"desc": "고장원인 분석작업", "type": "labor", "price": 14400, "search_term": None},
    {"desc": "브레이크 오일 교환 및 에어빼기", "type": "labor", "price": 57600, "search_term": "브레이크 오일"},
    {"desc": "공기필터", "type": "labor", "price": 11340, "search_term": "자동차 공기필터"},
    {"desc": "프론트 브레이크 디스크 (양쪽)", "type": "labor", "price": 50400, "search_term": None},
    {"desc": "리어 브레이크 패드(양쪽)", "type": "labor", "price": 48470, "search_term": None},
    {"desc": "오토매틱오일교환(장비사용)", "type": "labor", "price": 42480, "search_term": "ATF 미션오일"},
    {"desc": "프론트브레이크디스크(양쪽)", "type": "labor", "price": 51800, "search_term": None},
    {"desc": "리어브레이크디스크어셈블리(양쪽)", "type": "labor", "price": 59200, "search_term": None},
    {"desc": "브레이크 오일 교환", "type": "labor", "price": 35500, "search_term": "브레이크 오일"},
    {"desc": "엔진오일,휠터및에어크리너", "type": "labor", "price": 38780, "search_term": "엔진오일 필터 세트"},
    {"desc": "엔진오일, 휠터및에어크리너", "type": "labor", "price": 38230, "search_term": "엔진오일 필터 세트"},
    {"desc": "Diagnostic Tool Operation (EPB)", "type": "labor", "price": 14800, "search_term": None},
    {"desc": "브레이크 오일 (볼트로닉)", "type": "part", "price": 51240, "search_term": "볼트로닉 브레이크 오일",
     "quantity": 2, "unit_price": 25620},
]


def naver_shopping_search(query: str, limit: int = 5) -> dict:
    """
    네이버 쇼핑 BFF API 직접 호출.
    k-skill 프록시 불필요 — 공개 엔드포인트 사용.
    """
    url = "https://search.shopping.naver.com/api/search/all"
    params = {
        "query": query,
        "sort": "rel",
        "pagingIndex": 1,
        "pagingSize": limit,
        "viewType": "list",
        "productSet": "total",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json",
        "Accept-Language": "ko-KR,ko;q=0.9",
        "Referer": "https://search.shopping.naver.com/",
    }

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=10)
        resp.raise_for_status()
        data = resp.json()

        # shoppingResult.products 에서 가격 추출
        products = []
        shopping_result = data.get("shoppingResult", {})
        product_list = shopping_result.get("products", [])

        for p in product_list[:limit]:
            price = p.get("price", 0)
            if isinstance(price, str):
                price = int(price.replace(",", "")) if price else 0
            products.append({
                "title": p.get("productTitle", "").replace("<b>", "").replace("</b>", ""),
                "price": price,
                "mall": p.get("mallName", ""),
                "category": p.get("category1Name", ""),
            })

        prices = [p["price"] for p in products if p["price"] > 0]
        return {
            "query": query,
            "total": shopping_result.get("total", 0),
            "products": products,
            "price_min": min(prices) if prices else 0,
            "price_max": max(prices) if prices else 0,
            "price_avg": int(sum(prices) / len(prices)) if prices else 0,
        }

    except Exception as e:
        return {"query": query, "error": str(e), "products": [], "price_min": 0, "price_max": 0}


def test_naver_shopping():
    """네이버 쇼핑 검색 테스트."""
    print("=== 방법 C: 네이버 쇼핑 검색 테스트 ===\n")

    searchable = 0
    found = 0

    for i, item in enumerate(UNMATCHED_ITEMS, 1):
        desc = item["desc"]
        search_term = item.get("search_term")

        print(f"[{i:2d}] {desc}")
        print(f"     견적가: {item['price']:>10,}원 [{item['type']}]")

        if not search_term:
            print(f"     → 검색 불가 (순수 공임 항목, 네이버 쇼핑 대상 아님)")
            print()
            continue

        searchable += 1
        print(f"     검색어: '{search_term}'", file=sys.stderr)

        result = naver_shopping_search(search_term)
        time.sleep(0.5)  # rate limiting

        if result.get("error"):
            print(f"     → 오류: {result['error']}")
        elif result["price_min"] > 0:
            found += 1
            n = result["total"]
            p_min = result["price_min"]
            p_max = result["price_max"]
            p_avg = result["price_avg"]

            # 부품 항목은 수량 고려
            est_unit = item.get("unit_price", item["price"])
            in_range = "✓" if p_min <= est_unit <= p_max else "✗"

            print(f"     → 검색결과: {n:,}건")
            print(f"     → 가격범위: {p_min:,} ~ {p_max:,}원 (평균 {p_avg:,}원)")
            print(f"     → 견적 단가 {est_unit:,}원 범위내: {in_range}")

            # 상위 3개 상품
            for j, p in enumerate(result["products"][:3], 1):
                title = p["title"][:40]
                print(f"        {j}. {title} — {p['price']:,}원 ({p['mall']})")
        else:
            print(f"     → 검색결과 없음")

        print()

    total = len(UNMATCHED_ITEMS)
    print(f"검색 가능: {searchable}/{total}")
    print(f"가격 확인: {found}/{searchable} (검색 가능 항목 중)")
    print(f"\n참고: 순수 공임(노동비) 항목은 네이버 쇼핑 검색 대상이 아닙니다.")
    print(f"      네이버 쇼핑은 부품/소모품 가격 비교에만 유효합니다.")


if __name__ == "__main__":
    test_naver_shopping()
