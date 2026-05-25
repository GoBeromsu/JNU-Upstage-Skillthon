const express = require('express');
const router = express.Router();
const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');
const multer = require('multer');
const os = require('os');

const SKILLS_DIR = path.join(__dirname, '../../../../skills');
const PYTHON = process.platform === 'win32' ? 'python' : 'python3';

function runPython(scriptPath, args = [], stdinData = null, cwd = null) {
  return new Promise((resolve, reject) => {
    const proc = spawn(PYTHON, [scriptPath, ...args], {
      cwd: cwd || path.dirname(scriptPath),
      env: { ...process.env, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8' },
    });

    let stdout = '', stderr = '';
    proc.stdout.on('data', d => stdout += d.toString());
    proc.stderr.on('data', d => stderr += d.toString());

    // stdinData 유무와 관계없이 항상 stdin을 닫아야 Python이 블로킹되지 않음
    if (stdinData) {
      proc.stdin.write(typeof stdinData === 'string' ? stdinData : JSON.stringify(stdinData));
    }
    proc.stdin.end();

    proc.on('close', code => {
      console.log('\n=== Python stdout ===\n', stdout);
      console.error('=== Python stderr ===\n', stderr);
      console.log('=== exit code:', code, '===\n');
      try {
        resolve(JSON.parse(stdout));
      } catch {
        reject(new Error(stderr || `Python exit code ${code}: ${stdout}`));
      }
    });
    proc.on('error', reject);
  });
}

// 업체명 → { business_id, lat, lon } 조회 맵 (RECOMMEND 결과 좌표 보강용)
const BIZ_DATA_DIR = path.join(SKILLS_DIR, 'alba-recommender/data');
function buildBizMap() {
  const map = {};
  if (!fs.existsSync(BIZ_DATA_DIR)) return map;
  fs.readdirSync(BIZ_DATA_DIR)
    .filter(f => f.endsWith('.json'))
    .forEach(f => {
      try {
        const data = JSON.parse(fs.readFileSync(path.join(BIZ_DATA_DIR, f), 'utf8'));
        // 업체명 → 실제 데이터 매핑 (이름 완전일치 + 공백 정규화)
        const key = (data.name || '').trim();
        map[key] = {
          business_id: data.business_id,
          lat: data.lat ?? null,
          lon: data.lon ?? null,
        };
      } catch {}
    });
  return map;
}

// Python 결과의 업체 객체 → 프론트엔드 형식으로 변환
// bizMap: RECOMMEND 결과처럼 lat/lon이 없는 경우 이름으로 보강
function normalizeBiz(b, bizMap = {}) {
  const extra = bizMap[(b.name || '').trim()] || {};
  const score = b.clean_score ?? b.cleanScore ?? 100;
  let color = 'green';
  if (score < 40) color = 'red';
  else if (score < 60) color = 'orange';
  else if (score < 80) color = 'yellow';
  return {
    businessId:  b.business_id  || extra.business_id || b.businessId || b.name,
    name:        b.name,
    area:        b.area,
    industry:    b.industry,
    cleanScore:  score,
    color,
    reviewCount: b.review_count ?? b.reviewCount ?? 0,
    highlights:  b.highlights  || [],
    cautions:    b.cautions    || [],
    lat:         b.lat  ?? extra.lat  ?? null,
    lon:         b.lon  ?? extra.lon  ?? null,
    rank:        b.rank ?? null,
    reason:      b.reason ?? null,
  };
}

// ── SEARCH 빠른 경로 (Python/LLM 없이 Node.js 직접 검색) ─────────────
const AREA_ALIASES = {
  '상대': '상대', '상과대': '상대',
  '예대': '예대', '예술대': '예대',
  '정문': '정문', '전남대 정문': '정문',
  '후문': '후문', '전남대 후문': '후문',
  '전철우': '전철우', '전철우 사거리': '전철우',
};
const RECOMMEND_KEYWORDS = ['추천', '알려줘', '찾아줘', '조건', '이상', '어디', '주세요', '해줘', '싶어', '없을까', '있을까', '좋은', '괜찮은', '클린'];

function isLikelySearch(query) {
  if (query.length > 18) return false;
  return !RECOMMEND_KEYWORDS.some(kw => query.includes(kw));
}

function searchDirect(searchTerm) {
  if (!fs.existsSync(BIZ_DATA_DIR)) return [];
  const term = searchTerm.trim().toLowerCase();
  const canonicalArea = AREA_ALIASES[searchTerm.trim()] || null;
  const results = [];

  fs.readdirSync(BIZ_DATA_DIR).filter(f => f.endsWith('.json')).forEach(f => {
    try {
      const data = JSON.parse(fs.readFileSync(path.join(BIZ_DATA_DIR, f), 'utf8'));
      const name     = (data.name     || '').toLowerCase();
      const area     = (data.area     || '').toLowerCase();
      const industry = (data.industry || '').toLowerCase();
      const agg      = data.aggregate || {};

      const match = term && (
        name.includes(term) ||
        area.includes(term) ||
        industry.includes(term) ||
        (canonicalArea && data.area === canonicalArea)
      );
      if (!match) return;

      results.push(normalizeBiz({
        business_id:  data.business_id,
        name:         data.name,
        area:         data.area,
        industry:     data.industry,
        lat:          data.lat,
        lon:          data.lon,
        clean_score:  agg.clean_score  ?? 100,
        review_count: agg.review_count ?? 0,
        highlights:   [],
        cautions:     [],
      }));
    } catch {}
  });

  return results.sort((a, b) => b.cleanScore - a.cleanScore);
}

// POST /api/skills/recommend  — 검색/추천
router.post('/recommend', async (req, res) => {
  const { query } = req.body;
  if (!query) return res.status(400).json({ error: '검색어를 입력해주세요.' });

  // ── SEARCH 빠른 경로: Python 미사용, 즉시 반환 ──────────────
  if (isLikelySearch(query)) {
    const results = searchDirect(query);
    return res.json({ intent: 'SEARCH', search_term: query, count: results.length, results });
  }

  // ── RECOMMEND: Python + LLM ──────────────────────────────────
  try {
    const scriptPath = path.join(SKILLS_DIR, 'alba-recommender/scripts/recommend.py');
    // hint=RECOMMEND 전달 → Python이 의도분류 LLM 호출을 건너뜀
    const raw = await runPython(scriptPath, [], { query, hint: 'RECOMMEND' },
      path.join(SKILLS_DIR, 'alba-recommender'));

    const bizMap = buildBizMap();
    if (raw.results)         raw.results         = raw.results.map(b => normalizeBiz(b, bizMap));
    if (raw.recommendations) raw.recommendations = raw.recommendations.map(b => normalizeBiz(b, bizMap));

    res.json(raw);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// POST /api/skills/purify  — 후기 순화
router.post('/purify', async (req, res) => {
  const { reviewText } = req.body;
  if (!reviewText) return res.status(400).json({ error: '후기 텍스트를 입력해주세요.' });

  try {
    const scriptPath = path.join(SKILLS_DIR, 'review-purify-skill/scripts/purify.py');
    const result = await runPython(scriptPath, [], { review_text: reviewText },
      path.join(SKILLS_DIR, 'review-purify-skill'));
    res.json(result);
  } catch (e) {
    res.status(500).json({ error: e.message });
  }
});

// POST /api/skills/analyze-contract  — 근로계약서 분석
const upload = multer({ dest: os.tmpdir() });
router.post('/analyze-contract', upload.single('file'), async (req, res) => {
  if (!req.file) return res.status(400).json({ error: '파일을 업로드해주세요.' });

  const ext = path.extname(req.file.originalname) || '.jpg';
  const tmpPath = req.file.path + ext;
  fs.renameSync(req.file.path, tmpPath);

  try {
    const scriptPath = path.join(SKILLS_DIR, 'contract-analyzer/scripts/analyze_contract.py');
    // stdin JSON으로 파일 경로 전달 (args 방식은 stdin 블로킹 유발)
    const result = await runPython(scriptPath, [], { file_path: tmpPath },
      path.join(SKILLS_DIR, 'contract-analyzer'));
    res.json(result);
  } catch (e) {
    res.status(500).json({ error: e.message });
  } finally {
    try { fs.unlinkSync(tmpPath); } catch {}
  }
});

module.exports = router;
