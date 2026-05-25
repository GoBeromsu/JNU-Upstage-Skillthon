const express = require('express');
const crypto  = require('crypto');
const router  = express.Router();
const db      = require('../db/database');
const { spawn } = require('child_process');
const path    = require('path');

const SKILLS_DIR    = path.join(__dirname, '../../../../skills');
const PYTHON        = process.platform === 'win32' ? 'python' : 'python3';
const ADMIN_SECRET  = process.env.ADMIN_SECRET || 'jnu-alba-admin-2024';

/* ── 관리자 토큰 검증 ─────────────────────────────────────── */
function makeAdminToken(userId) {
  return crypto.createHmac('sha256', ADMIN_SECRET).update(String(userId)).digest('hex');
}

function adminAuth(req, res, next) {
  const userId = req.headers['x-user-id'];
  const token  = req.headers['x-admin-token'];

  if (!userId || !token) {
    return res.status(401).json({ error: '관리자 인증이 필요합니다.' });
  }
  const expected = makeAdminToken(userId);
  if (token !== expected) {
    return res.status(401).json({ error: '관리자 권한이 없습니다.' });
  }
  next();
}

/* ── add_review.py 실행 헬퍼 ─────────────────────────────── */
function runAddReview(payload) {
  return new Promise((resolve, reject) => {
    const scriptPath = path.join(SKILLS_DIR, 'alba-recommender/scripts/add_review.py');
    const proc = spawn(PYTHON, [scriptPath], {
      cwd: path.join(SKILLS_DIR, 'alba-recommender'),
      env: { ...process.env, PYTHONUTF8: '1', PYTHONIOENCODING: 'utf-8' },
    });

    let stdout = '', stderr = '';
    proc.stdout.on('data', d => stdout += d.toString());
    proc.stderr.on('data', d => stderr += d.toString());
    proc.stdin.write(JSON.stringify(payload));
    proc.stdin.end();

    proc.on('close', code => {
      console.log('[Admin] add_review stdout:', stdout);
      if (stderr) console.error('[Admin] add_review stderr:', stderr);
      try { resolve(JSON.parse(stdout)); }
      catch { reject(new Error(stderr || `exit ${code}: ${stdout}`)); }
    });
    proc.on('error', reject);
  });
}

/* ── 파일 경로 → 브라우저 URL 변환 ──────────────────────── */
function toFileUrl(file) {
  if (!file) return file;
  if (file.url) return file;
  if (file.path) {
    const filename = file.path.replace(/\\/g, '/').split('/').pop();
    return { ...file, url: `/uploads/proof/${filename}` };
  }
  return file;
}

/* ── 공통 직렬화 ─────────────────────────────────────────── */
function serializeReview(r) {
  const rawFiles = typeof r.proof_files === 'string'
    ? JSON.parse(r.proof_files || '[]')
    : (r.proof_files || []);

  return {
    ...r,
    criteriaFlags: typeof r.criteria_flags === 'string'
      ? JSON.parse(r.criteria_flags || '{}')
      : (r.criteria_flags || {}),
    proofFiles: rawFiles.map(toFileUrl),
  };
}

/* ── GET /api/admin/pending ──────────────────────────────── */
router.get('/pending', adminAuth, async (req, res) => {
  try {
    const rows = await db.getPendingReviews('pending');
    res.json(rows.map(serializeReview));
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: e.message });
  }
});

/* ── GET /api/admin/all ──────────────────────────────────── */
router.get('/all', adminAuth, async (req, res) => {
  try {
    const rows = await db.getPendingReviews();
    res.json(rows.slice(0, 200).map(serializeReview));
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: e.message });
  }
});

/* ── POST /api/admin/approve/:id ─────────────────────────── */
router.post('/approve/:id', adminAuth, async (req, res) => {
  try {
    const review = await db.findReview(req.params.id);
    if (!review) return res.status(404).json({ error: '리뷰를 찾을 수 없습니다.' });

    const flags = typeof review.criteria_flags === 'string'
      ? JSON.parse(review.criteria_flags || '{}')
      : (review.criteria_flags || {});

    const payload = {
      business_id:    review.business_id,
      name:           review.business_name,
      area:           review.area,
      industry:       review.industry,
      criteria_flags: flags,
      review_text:    review.purified_text || review.review_text || '',
    };

    const addResult = await runAddReview(payload);
    console.log('[Admin] add_review 결과:', addResult);

    await db.updateReviewStatus(req.params.id, 'approved');

    if (review.user_id) {
      await db.addNotification(
        review.user_id,
        `"${review.business_name}" 후기가 승인되어 지도에 반영되었습니다.`
      );
    }

    res.json({ status: 'approved', id: req.params.id, addResult });
  } catch (e) {
    console.error('[Admin] approve error:', e.message);
    res.status(500).json({ error: e.message });
  }
});

/* ── POST /api/admin/reject/:id ──────────────────────────── */
router.post('/reject/:id', adminAuth, async (req, res) => {
  try {
    const { reason = '검수 기준 미달' } = req.body;
    const review = await db.findReview(req.params.id);
    if (!review) return res.status(404).json({ error: '리뷰를 찾을 수 없습니다.' });

    await db.updateReviewStatus(req.params.id, 'rejected', { reject_reason: reason });

    if (review.user_id) {
      await db.addNotification(
        review.user_id,
        `"${review.business_name}" 후기가 반려되었습니다. 사유: ${reason}`
      );
    }

    res.json({ status: 'rejected', id: req.params.id });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: e.message });
  }
});

module.exports = router;
