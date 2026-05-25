/**
 * 간단한 JSON 파일 기반 DB (개발/데모용)
 * 프로덕션에서는 PostgreSQL로 교체 예정
 */
const fs = require('fs');
const path = require('path');

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

const db = {
  // pending_reviews CRUD
  getPendingReviews(status = null) {
    const rows = readTable('pending_reviews');
    return status ? rows.filter(r => r.status === status) : rows;
  },
  insertReview(review) {
    const rows = readTable('pending_reviews');
    rows.push({ ...review, submitted_at: new Date().toLocaleString('ko-KR') });
    writeTable('pending_reviews', rows);
  },
  updateReviewStatus(id, status, extra = {}) {
    const rows = readTable('pending_reviews');
    const idx = rows.findIndex(r => r.id === id);
    if (idx < 0) return false;
    rows[idx] = { ...rows[idx], status, reviewed_at: new Date().toLocaleString('ko-KR'), ...extra };
    writeTable('pending_reviews', rows);
    return rows[idx];
  },
  findReview(id) {
    return readTable('pending_reviews').find(r => r.id === id) || null;
  },
  // notifications
  addNotification(userId, message) {
    const rows = readTable('notifications');
    rows.push({ id: Date.now().toString(), userId, message, isRead: false, createdAt: new Date().toLocaleString('ko-KR') });
    writeTable('notifications', rows);
  },
  getNotifications(userId) {
    return readTable('notifications').filter(n => n.userId === userId);
  },
};

module.exports = db;
