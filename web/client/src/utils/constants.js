export const CRITERIA_KEYS = [
  '근로계약서 미작성',
  '최저시급 미준수',
  '주휴수당 미지급',
  '휴게시간 부족',
  '급여 지급 지연',
  '사전 협의 없는 스케줄 변경',
  '반복적이고 지속적인 대타 요구 및 강요',
  '초과근무 급여 미지급',
];

export const AREAS = ['상대', '예대', '정문', '후문', '전철우'];
export const INDUSTRIES = ['카페', '식당', '편의점', '주점', '패스트푸드', '기타'];

export const COLOR_MAP = {
  green: '#22c55e',
  yellow: '#eab308',
  orange: '#f97316',
  red: '#ef4444',
};

export const SCORE_LABEL = {
  green: '우수',
  yellow: '보통',
  orange: '주의',
  red: '위험',
};

export function scoreToColor(score) {
  if (score >= 80) return 'green';
  if (score >= 60) return 'yellow';
  if (score >= 40) return 'orange';
  return 'red';
}
