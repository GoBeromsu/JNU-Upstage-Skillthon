/**
 * DB 모듈 — DATABASE_URL 환경변수가 있으면 PostgreSQL, 없으면 JSON 파일 폴백
 */
const fs   = require('fs');
const path = require('path');

const USE_PG = !!process.env.DATABASE_URL;

/* ── PostgreSQL Pool ────────────────────────────────────── */
let pool;
if (USE_PG) {
  const { Pool } = require('pg');
  pool = new Pool({
    connectionString: process.env.DATABASE_URL,
    ssl: { rejectUnauthorized: false },
  });
}

/* ── 테이블 초기화 (서버 시작 시 1회) ──────────────────── */
async function init() {
  if (!USE_PG) {
    console.log('[DB] DATABASE_URL 없음 → JSON 파일 모드');
    return;
  }
  await pool.query(`
    CREATE TABLE IF NOT EXISTS reviews (
      id             TEXT PRIMARY KEY,
      business_id    TEXT,
      business_name  TEXT,
      area           TEXT,
      industry       TEXT,
      criteria_flags TEXT,
      review_text    TEXT,
      purified_text  TEXT,
      proof_files    TEXT,
      coworker_count TEXT,
      user_id        TEXT,
      status         TEXT DEFAULT 'pending',
      submitted_at   TIMESTAMPTZ DEFAULT NOW(),
      reviewed_at    TIMESTAMPTZ,
      reject_reason  TEXT
    );
    CREATE TABLE IF NOT EXISTS notifications (
      id         TEXT PRIMARY KEY,
      user_id    TEXT,
      message    TEXT,
      is_read    BOOLEAN DEFAULT false,
      created_at TIMESTAMPTZ DEFAULT NOW()
    );
  `);
  console.log('[DB] PostgreSQL 연결 및 테이블 초기화 완료');
}

/* ── JSON 폴백 유틸 ────────────────────────────────────── */
const DB_DIR = path.join(__dirname, '../../data');
if (!fs.existsSync(DB_DIR)) fs.mkdirSync(DB_DIR, { recursive: true });

function readTable(name) {
  const file = path.join(DB_DIR, `${name}.json`);
  if (!fs.existsSync(file)) return [];
  return JSON.parse(fs.readFileSync(file, 'utf8'));
}
function writeTable(name, data) {
  const file = path.join(DB_DIR, `${name}.json`);
  fs.writeFileSync(file, JSON.stringify(data, null, 2), 'utf8');
}

/* ── DB 인터페이스 ─────────────────────────────────────── */
const db = {
  init,

  async getPendingReviews(status = null) {
    if (USE_PG) {
      const q = status
        ? 'SELECT * FROM reviews WHERE status=$1 ORDER BY submitted_at DESC'
        : 'SELECT * FROM reviews ORDER BY submitted_at DESC';
      const { rows } = await pool.query(q, status ? [status] : []);
      return rows;
    }
    const rows = readTable('pending_reviews');
    return status ? rows.filter(r => r.status === status) : rows;
  },

  async insertReview(review) {
    if (USE_PG) {
      await pool.query(
        `INSERT INTO reviews
          (id, business_id, business_name, area, industry,
           criteria_flags, review_text, purified_text,
           proof_files, coworker_count, user_id, status)
         VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11,$12)`,
        [
          review.id, review.business_id, review.business_name,
          review.area, review.industry, review.criteria_flags,
          review.review_text, review.purified_text, review.proof_files,
          review.coworker_count, review.user_id || null, review.status,
        ]
      );
      return;
    }
    const rows = readTable('pending_reviews');
    rows.push({ ...review, submitted_at: new Date().toLocaleString('ko-KR') });
    writeTable('pending_reviews', rows);
  },

  async updateReviewStatus(id, status, extra = {}) {
    if (USE_PG) {
      const vals = [id, status];
      const sets = ['status=$2', 'reviewed_at=NOW()'];
      if (extra.reject_reason !== undefined) {
        sets.push(`reject_reason=$${vals.length + 1}`);
        vals.push(extra.reject_reason);
      }
      const { rows } = await pool.query(
        `UPDATE reviews SET ${sets.join(', ')} WHERE id=$1 RETURNING *`,
        vals
      );
      return rows[0] || null;
    }
    const rows = readTable('pending_reviews');
    const idx = rows.findIndex(r => r.id === id);
    if (idx < 0) return false;
    rows[idx] = { ...rows[idx], status, reviewed_at: new Date().toLocaleString('ko-KR'), ...extra };
    writeTable('pending_reviews', rows);
    return rows[idx];
  },

  async findReview(id) {
    if (USE_PG) {
      const { rows } = await pool.query('SELECT * FROM reviews WHERE id=$1', [id]);
      return rows[0] || null;
    }
    return readTable('pending_reviews').find(r => r.id === id) || null;
  },

  async addNotification(userId, message) {
    if (USE_PG) {
      await pool.query(
        'INSERT INTO notifications (id, user_id, message) VALUES ($1,$2,$3)',
        [Date.now().toString(), userId, message]
      );
      return;
    }
    const rows = readTable('notifications');
    rows.push({ id: Date.now().toString(), userId, message, isRead: false, createdAt: new Date().toLocaleString('ko-KR') });
    writeTable('notifications', rows);
  },

  async getNotifications(userId) {
    if (USE_PG) {
      const { rows } = await pool.query(
        'SELECT * FROM notifications WHERE user_id=$1 ORDER BY created_at DESC',
        [userId]
      );
      return rows;
    }
    return readTable('notifications').filter(n => n.userId === userId);
  },
};

module.exports = db;
