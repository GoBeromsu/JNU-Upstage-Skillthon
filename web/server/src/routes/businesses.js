const express = require('express');
const router = express.Router();
const path = require('path');
const fs = require('fs');
const crypto = require('crypto');

const SKILLS_DIR = path.join(__dirname, '../../../../skills');
const ALBA_DATA_DIR = path.join(SKILLS_DIR, 'alba-recommender/data');

const AREA_COORDS = {
  '상대': [35.1767, 126.9082],
  '예대': [35.1783, 126.9126],
  '정문': [35.1759, 126.9061],
  '후문': [35.1795, 126.9148],
  '전철우': [35.1778, 126.9171],
};

const CRITERIA_KEYS = [
  '근로계약서 미작성', '최저시급 미준수', '주휴수당 미지급',
  '휴게시간 부족', '급여 지급 지연', '사전 협의 없는 스케줄 변경',
  '반복적이고 지속적인 대타 요구 및 강요', '초과근무 급여 미지급',
];
const CRITERIA_POSITIVE = {
  '근로계약서 미작성': '근로계약서 작성',
  '최저시급 미준수': '최저시급 준수',
  '주휴수당 미지급': '주휴수당 지급',
  '휴게시간 부족': '충분한 휴게시간 보장',
  '급여 지급 지연': '정시 급여지급',
  '사전 협의 없는 스케줄 변경': '사전 협의된 스케줄 관리',
  '반복적이고 지속적인 대타 요구 및 강요': '합리적인 대타 요청',
  '초과근무 급여 미지급': '초과근무 급여 지급',
};

function getCoords(businessId, area) {
  const [baseLat, baseLon] = AREA_COORDS[area] || [35.1767, 126.9082];
  const hash = parseInt(crypto.createHash('md5').update(businessId).digest('hex').slice(0, 8), 16);
  const latOffset = ((hash % 200) - 100) * 0.00008;
  const lonOffset = (((hash >> 8) % 200) - 100) * 0.00008;
  return [+(baseLat + latOffset).toFixed(6), +(baseLon + lonOffset).toFixed(6)];
}

function scoreToColor(score) {
  if (score >= 80) return 'green';
  if (score >= 60) return 'yellow';
  if (score >= 40) return 'orange';
  return 'red';
}

function loadBusinesses() {
  if (!fs.existsSync(ALBA_DATA_DIR)) return [];
  return fs.readdirSync(ALBA_DATA_DIR)
    .filter(f => f.endsWith('.json'))
    .map(f => {
      try {
        const data = JSON.parse(fs.readFileSync(path.join(ALBA_DATA_DIR, f), 'utf8'));
        const agg = data.aggregate || {};
        const n = agg.review_count || 0;
        const counts = agg.criteria_violation_counts || {};

        let cautions = [], highlights = [];
        if (n >= 2) {
          cautions = CRITERIA_KEYS.filter(k => (counts[k] || 0) / n >= 0.3);
          highlights = CRITERIA_KEYS.filter(k => (counts[k] || 0) === 0).map(k => CRITERIA_POSITIVE[k]);
        } else if (n === 1) {
          cautions = CRITERIA_KEYS.filter(k => (counts[k] || 0) > 0);
          highlights = CRITERIA_KEYS.filter(k => (counts[k] || 0) === 0).map(k => CRITERIA_POSITIVE[k]);
        }

        const oxStats = {};
        CRITERIA_KEYS.forEach(k => {
          const v = counts[k] || 0;
          oxStats[k] = { ok: n - v, violation: v, violationRate: n > 0 ? Math.round(v / n * 100) : 0 };
        });

        const [lat, lon] = (data.lat && data.lon) ? [data.lat, data.lon] : getCoords(data.business_id, data.area);
        const score = agg.clean_score || 100;

        return {
          businessId: data.business_id,
          name: data.name,
          area: data.area,
          industry: data.industry,
          cleanScore: score,
          color: scoreToColor(score),
          reviewCount: n,
          highlights,
          cautions,
          oxStats,
          lat,
          lon,
          reviews: (data.reviews || []).slice(-10).reverse(),
          lastUpdated: agg.last_updated || '',
          jobPostings: data.job_postings || [],
        };
      } catch { return null; }
    }).filter(Boolean);
}

// GET /api/businesses
router.get('/', (req, res) => {
  res.json(loadBusinesses());
});

// GET /api/businesses/ranking
router.get('/ranking', (req, res) => {
  const businesses = loadBusinesses();
  const ranked = businesses.sort((a, b) => b.cleanScore - a.cleanScore).slice(0, 20);
  res.json(ranked.map((b, i) => ({ rank: i + 1, ...b })));
});

// GET /api/businesses/:id
router.get('/:id', (req, res) => {
  const businesses = loadBusinesses();
  const biz = businesses.find(b => b.businessId === req.params.id);
  if (!biz) return res.status(404).json({ error: '사업장을 찾을 수 없습니다.' });
  res.json(biz);
});

module.exports = router;
