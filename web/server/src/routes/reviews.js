const express = require('express');
const router = express.Router();
const db = require('../db/database');
const { v4: uuidv4 } = require('uuid');
const multer = require('multer');
const path = require('path');
const fs = require('fs');

const PROOF_DIR = path.join(__dirname, '../../uploads/proof');
if (!fs.existsSync(PROOF_DIR)) fs.mkdirSync(PROOF_DIR, { recursive: true });

const upload = multer({
  dest: PROOF_DIR,
  limits: { fileSize: 10 * 1024 * 1024 },
});

// POST /api/reviews  — 후기 제출
router.post('/', upload.array('proofFiles', 5), async (req, res) => {
  try {
    const {
      businessId, businessName, area, industry,
      criteriaFlags, reviewText, purifiedText, coworkerCount,
    } = req.body;

    if (!businessName || !area || !industry || !criteriaFlags) {
      return res.status(400).json({ error: '필수 항목이 누락되었습니다.' });
    }

    const proofFiles = (req.files || []).map(f => ({
      originalName: f.originalname,
      url:      `/uploads/proof/${f.filename}`,
      mimetype: f.mimetype,
    }));

    const id = uuidv4().slice(0, 8);

    await db.insertReview({
      id,
      business_id:    businessId || `${businessName}_${area}`,
      business_name:  businessName,
      area,
      industry,
      criteria_flags: typeof criteriaFlags === 'string' ? criteriaFlags : JSON.stringify(criteriaFlags),
      review_text:    reviewText   || '',
      purified_text:  purifiedText || '',
      proof_files:    JSON.stringify(proofFiles),
      coworker_count: coworkerCount || '',
      status:         'pending',
    });

    res.json({
      status: 'submitted',
      reviewId: id,
      message: '후기가 제출되었습니다. 관리자 검수 후 지도에 반영됩니다.',
    });
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: e.message });
  }
});

// GET /api/reviews/my  — 내 후기 목록
router.get('/my', async (req, res) => {
  try {
    const userId = req.query.userId;
    if (!userId) return res.json([]);
    const all = await db.getPendingReviews();
    const rows = all
      .filter(r => r.user_id === userId)
      .sort((a, b) => new Date(b.submitted_at) - new Date(a.submitted_at));
    res.json(rows);
  } catch (e) {
    console.error(e);
    res.status(500).json({ error: e.message });
  }
});

module.exports = router;
