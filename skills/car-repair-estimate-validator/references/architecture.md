# 기술 스택

- **OCR**: Upstage Information Extract API
- **차량 매칭**: Upstage Solar Chat + 모비스 모델 목록 (JSON 번들링)
- **공임 조회**: 공임나라 웹 조회 (requests, AJAX POST)
- **부품 조회**: 현대모비스 간단검색 웹 조회 (Playwright stealth)
- **동의어 매핑**: 공임/부품 동의어 사전으로 매칭률 향상
- **검증 엔진**: 편차 계산 + 매칭 신뢰도 필터 + 한국어 제안 생성
- **비교불가 항목 보충**: 에이전트 실시간 웹 검색으로 시장 참고가 확인
- **리포트**: 마크다운 생성 (API 호출 없음)
