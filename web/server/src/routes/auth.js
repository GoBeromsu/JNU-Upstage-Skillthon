const express  = require('express');
const https    = require('https');
const qs       = require('querystring');
const crypto   = require('crypto');
const router   = express.Router();

const REST_API_KEY        = process.env.REST_API_KEY;
const KAKAO_CLIENT_SECRET = process.env.KAKAO_CLIENT_SECRET;
const REDIRECT_URI        = process.env.REDIRECT_URI   || 'http://localhost:3000/oauth/kakao';
const ADMIN_KAKAO_ID      = process.env.ADMIN_KAKAO_ID || '';
const ADMIN_SECRET        = process.env.ADMIN_SECRET   || 'jnu-alba-admin-2024';

console.log('[Auth] REST_API_KEY:', REST_API_KEY ? `${REST_API_KEY.slice(0,4)}...${REST_API_KEY.slice(-4)} (${REST_API_KEY.length}자)` : '❌ 없음');
console.log('[Auth] REDIRECT_URI:', REDIRECT_URI);
console.log('[Auth] ADMIN_KAKAO_ID:', ADMIN_KAKAO_ID || '(미설정 — 로그인 후 콘솔에서 확인)');

/* ── 관리자 토큰 생성 ──────────────────────────────────────── */
function makeAdminToken(userId) {
  return crypto.createHmac('sha256', ADMIN_SECRET).update(String(userId)).digest('hex');
}

/* ── HTTPS 요청 헬퍼 ─────────────────────────────────────── */
function request(method, url, { body, headers = {} } = {}) {
  return new Promise((resolve, reject) => {
    const u = new URL(url);
    const bodyStr = body ? (typeof body === 'string' ? body : qs.stringify(body)) : '';
    const opts = {
      hostname: u.hostname,
      path:     u.pathname + u.search,
      method,
      headers: {
        ...headers,
        ...(bodyStr ? { 'Content-Length': Buffer.byteLength(bodyStr) } : {}),
      },
    };
    const req = https.request(opts, res => {
      let data = '';
      res.on('data', c => data += c);
      res.on('end', () => {
        try { resolve(JSON.parse(data)); }
        catch { resolve(data); }
      });
    });
    req.on('error', reject);
    if (bodyStr) req.write(bodyStr);
    req.end();
  });
}

/* GET /api/auth/kakao-url */
router.get('/kakao-url', (req, res) => {
  const url =
    `https://kauth.kakao.com/oauth/authorize` +
    `?client_id=${REST_API_KEY}` +
    `&redirect_uri=${encodeURIComponent(REDIRECT_URI)}` +
    `&response_type=code` +
    `&prompt=login`;
  res.json({ url });
});

/* POST /api/auth/kakao — 인가코드 → 토큰 → 사용자 정보 */
router.post('/kakao', async (req, res) => {
  const { code } = req.body;
  if (!code) return res.status(400).json({ error: '인가코드가 없습니다.' });

  try {
    // 1) 액세스 토큰 발급
    const tokenBody = {
      grant_type:   'authorization_code',
      client_id:    REST_API_KEY,
      redirect_uri: REDIRECT_URI,
      code,
    };
    if (KAKAO_CLIENT_SECRET) tokenBody.client_secret = KAKAO_CLIENT_SECRET;

    const tokenData = await request('POST', 'https://kauth.kakao.com/oauth/token', {
      headers: { 'Content-Type': 'application/x-www-form-urlencoded;charset=utf-8' },
      body: tokenBody,
    });

    console.log('[Auth] tokenData:', JSON.stringify(tokenData));
    if (tokenData.error) throw new Error(tokenData.error_description || tokenData.error);

    // 2) 사용자 정보 조회
    const userData = await request('GET', 'https://kapi.kakao.com/v2/user/me', {
      headers: { Authorization: `Bearer ${tokenData.access_token}` },
    });

    console.log('[Auth] userData:', JSON.stringify(userData));

    const userId     = String(userData.id);
    const isAdmin    = !!(ADMIN_KAKAO_ID && userId === ADMIN_KAKAO_ID);
    const adminToken = isAdmin ? makeAdminToken(userId) : null;

    // ADMIN_KAKAO_ID 미설정 시 현재 로그인 ID를 안내 로그로 출력
    if (!ADMIN_KAKAO_ID) {
      console.log(`[Auth] ⚠️  ADMIN_KAKAO_ID가 설정되지 않았습니다.`);
      console.log(`[Auth] 👉  이 계정을 관리자로 지정하려면 .env에 추가하세요:`);
      console.log(`[Auth]     ADMIN_KAKAO_ID=${userId}`);
    } else {
      console.log(`[Auth] 로그인 userId=${userId} | isAdmin=${isAdmin}`);
    }

    res.json({
      accessToken: tokenData.access_token,
      user: {
        id:           userId,
        nickname:     userData.kakao_account?.profile?.nickname || '전남대생',
        profileImage: userData.kakao_account?.profile?.profile_image_url || null,
        isAdmin,
        adminToken,
      },
    });
  } catch (e) {
    console.error('[Auth] error:', e.message);
    res.status(500).json({ error: e.message });
  }
});

module.exports = router;
module.exports.makeAdminToken = makeAdminToken;
