/**
 * 파일 스토리지 유틸
 * R2 환경변수가 있으면 Cloudflare R2, 없으면 로컬 파일시스템
 */
const path = require('path');
const fs   = require('fs');
const { S3Client, PutObjectCommand } = require('@aws-sdk/client-s3');

const USE_R2 = !!(
  process.env.R2_ACCOUNT_ID &&
  process.env.R2_ACCESS_KEY_ID &&
  process.env.R2_SECRET_ACCESS_KEY &&
  process.env.R2_BUCKET_NAME
);

let r2Client;
if (USE_R2) {
  r2Client = new S3Client({
    region: 'auto',
    endpoint: `https://${process.env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com`,
    credentials: {
      accessKeyId:     process.env.R2_ACCESS_KEY_ID,
      secretAccessKey: process.env.R2_SECRET_ACCESS_KEY,
    },
  });
  console.log('[Storage] Cloudflare R2 모드');
} else {
  console.log('[Storage] 로컬 파일시스템 모드');
}

/**
 * 파일 업로드
 * @param {Buffer} buffer  파일 내용
 * @param {string} filename  저장할 파일명
 * @param {string} mimetype  MIME 타입
 * @returns {Promise<string>}  브라우저에서 접근 가능한 URL
 */
async function uploadFile(buffer, filename, mimetype) {
  if (USE_R2) {
    const key = `proof/${filename}`;
    await r2Client.send(new PutObjectCommand({
      Bucket:      process.env.R2_BUCKET_NAME,
      Key:         key,
      Body:        buffer,
      ContentType: mimetype,
    }));
    const publicUrl = process.env.R2_PUBLIC_URL || `https://${process.env.R2_BUCKET_NAME}.${process.env.R2_ACCOUNT_ID}.r2.cloudflarestorage.com`;
    return `${publicUrl}/${key}`;
  }

  // 로컬 폴백
  const PROOF_DIR = path.join(__dirname, '../../uploads/proof');
  if (!fs.existsSync(PROOF_DIR)) fs.mkdirSync(PROOF_DIR, { recursive: true });
  fs.writeFileSync(path.join(PROOF_DIR, filename), buffer);
  return `/uploads/proof/${filename}`;
}

module.exports = { uploadFile, USE_R2 };
