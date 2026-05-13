"""
공임나라 표준공임비 조회 스크립트 (프로토타입)

사용법:
    python lookup_gongim.py                      # 전체 카테고리 목록 조회
    python lookup_gongim.py --category 엔진오일   # 특정 카테고리의 공임비 조회
"""

import requests
import re
import json
import sys
from html.parser import HTMLParser

BASE_URL = "https://www.gongim.com/front/html/proc"

HEADERS = {
    "Content-Type": "application/x-www-form-urlencoded",
    "X-Requested-With": "XMLHttpRequest",
    "Referer": "https://www.gongim.com/front/html/repair.php",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

# 국산차 = 39, 수입차 = 40, 타이어 = 41
CATE_DOMESTIC = "39"


def get_categories(cate_no=CATE_DOMESTIC):
    """카테고리 목록 조회"""
    resp = requests.post(
        f"{BASE_URL}/getGongImCateList.php",
        data={"cateNo": cate_no},
        headers=HEADERS,
        timeout=10
    )
    resp.encoding = "utf-8"

    # HTML 파싱: data-catesubno와 버튼 텍스트 추출
    categories = re.findall(
        r'data-catesubno="(\d+)"[^>]*>([^<]+)</button>',
        resp.text
    )
    return [{"id": cid, "name": name.strip()} for cid, name in categories]


def get_labor_costs(cate_no=CATE_DOMESTIC, cate_sub_no="612511"):
    """특정 카테고리의 공임비 상세 조회"""
    resp = requests.post(
        f"{BASE_URL}/getGongImCateSubList1.php",
        data={"cateNo": cate_no, "cateSubNo": cate_sub_no},
        headers=HEADERS,
        timeout=10
    )
    resp.encoding = "utf-8"
    html = resp.text

    # 카테고리 제목
    title_match = re.search(r'jewon_tl">([^<]+)</div>', html)
    title = title_match.group(1).strip() if title_match else "unknown"

    # 수정일
    date_match = re.search(r'수정일\s*:\s*([\d.]+)', html)
    update_date = date_match.group(1) if date_match else None

    # 테이블에서 공임비 데이터 추출
    # 패턴: 구분 | 작업종류 | 공임비(원) + 소요시간(분)
    items = []

    # 각 테이블 행에서 데이터 추출
    rows = re.findall(r'<tr>(.*?)</tr>', html, re.DOTALL)
    for row in rows:
        cells = re.findall(r'<td[^>]*>(.*?)</td>', row, re.DOTALL)
        if len(cells) >= 2:
            # 마지막 셀에서 가격과 시간 추출
            last_cell = cells[-1]
            price_match = re.search(r'([\d,]+)\s*원', last_cell)
            time_match = re.search(r'\((\d+)분\)', last_cell)

            if price_match:
                # 작업종류 (중간 셀들)
                work_type = re.sub(r'<[^>]+>', '', cells[-2] if len(cells) >= 3 else cells[0]).strip()
                category = re.sub(r'<[^>]+>', '', cells[0]).strip() if len(cells) >= 3 else ""

                items.append({
                    "category": category,
                    "work_type": work_type,
                    "price_krw": int(price_match.group(1).replace(",", "")),
                    "time_minutes": int(time_match.group(1)) if time_match else None
                })

    return {
        "title": title,
        "update_date": update_date,
        "items": items
    }


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--category":
        target = sys.argv[2] if len(sys.argv) > 2 else None

        # 카테고리 목록에서 매칭
        categories = get_categories()
        matched = None
        for cat in categories:
            if target and target in cat["name"]:
                matched = cat
                break

        if matched:
            print(f"[{matched['name']}] 공임비 조회 중...")
            result = get_labor_costs(cate_sub_no=matched["id"])
            print(json.dumps(result, ensure_ascii=False, indent=2))
        else:
            print(f"'{target}' 카테고리를 찾을 수 없습니다.")
            print("사용 가능한 카테고리:")
            for cat in categories:
                print(f"  - {cat['name']}")
    else:
        # 전체 카테고리 목록
        categories = get_categories()
        print("=== 공임나라 국산차 정비공임 카테고리 ===")
        for cat in categories:
            print(f"  [{cat['id']}] {cat['name']}")
