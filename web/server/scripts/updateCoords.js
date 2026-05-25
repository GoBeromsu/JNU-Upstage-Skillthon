/**
 * 카카오 로컬 API로 실제 사업장 좌표를 검색해서 JSON 파일에 업데이트하는 스크립트
 * 실행: node scripts/updateCoords.js
 */
require('dotenv').config({ path: require('path').join(__dirname, '../.env') });

const https = require('https');
const fs = require('fs');
const path = require('path');

const REST_API_KEY = process.env.REST_API_KEY;
const DATA_DIR = path.join(__dirname, '../../../skills/alba-recommender/data');

// 전남대학교 중심 좌표 (검색 기준점)
const JNU_LAT = 35.1767;
const JNU_LON = 126.9082;

// 카카오 지도 실제 상호명으로 검색
const BUSINESSES = [
  { file: '메가MGC커피_전대정문점.json',     query: '메가MGC커피 전대정문점' },
  { file: '이디야커피_전남대정문점.json',     query: '이디야커피 전남대정문점' },
  { file: '파스쿠찌_후문점.json',            query: '파스쿠찌 전남대후문점' },
  { file: '더벤티_후문점.json',             query: '더벤티 전남대' },
  { file: '중앙닭갈비_후문점.json',          query: '중앙닭갈비 전남대' },
  { file: '탑독PC방_후문점.json',           query: '탑독PC방 전남대' },
  { file: '도토리베이커리_상대점.json',       query: '도토리베이커리 광주 북구' },
  { file: '천지연삼겹살_상대점.json',         query: '천지연삼겹살 광주 북구' },
  { file: '한신포차_전철우점.json',          query: '한신포차 전남대' },
  { file: '깐깐한족발_전철우점.json',         query: '깐깐한족발 전남대' },
];

function kakaoSearch(query) {
  return new Promise((resolve, reject) => {
    const params = new URLSearchParams({
      query,
      x: JNU_LON,
      y: JNU_LAT,
      radius: 3000,
      size: 5,
    });
    const options = {
      hostname: 'dapi.kakao.com',
      path: `/v2/local/search/keyword.json?${params}`,
      method: 'GET',
      headers: { Authorization: `KakaoAK ${REST_API_KEY}` },
    };

    const req = https.request(options, (res) => {
      let data = '';
      res.on('data', (chunk) => (data += chunk));
      res.on('end', () => {
        try { resolve(JSON.parse(data)); }
        catch (e) { reject(e); }
      });
    });
    req.on('error', reject);
    req.end();
  });
}

async function updateAll() {
  if (!REST_API_KEY) {
    console.error('❌ REST_API_KEY가 .env에 없습니다.');
    process.exit(1);
  }

  console.log('🗺️  카카오 로컬 API로 실제 좌표 검색 중...\n');

  for (const biz of BUSINESSES) {
    const filePath = path.join(DATA_DIR, biz.file);
    if (!fs.existsSync(filePath)) {
      console.warn(`⚠️  파일 없음: ${biz.file}`);
      continue;
    }

    try {
      const result = await kakaoSearch(biz.query);
      const docs = result.documents;

      if (!docs || docs.length === 0) {
        console.warn(`❌ 검색 결과 없음: "${biz.query}"`);
        // 후보 없으면 건너뜀 (기존 좌표 유지)
        continue;
      }

      // 검색 결과 전체 출력해서 사용자가 확인할 수 있게
      console.log(`🔍 "${biz.query}" 검색 결과:`);
      docs.forEach((d, i) => {
        console.log(`   [${i}] ${d.place_name} | ${d.road_address_name || d.address_name}`);
        console.log(`       lat: ${d.y}, lon: ${d.x}`);
      });

      const place = docs[0];
      const lat = parseFloat(place.y);
      const lon = parseFloat(place.x);

      const json = JSON.parse(fs.readFileSync(filePath, 'utf8'));
      json.lat = lat;
      json.lon = lon;
      fs.writeFileSync(filePath, JSON.stringify(json, null, 2), 'utf8');

      console.log(`✅ ${biz.file} → "${place.place_name}" (${lat}, ${lon})\n`);

      await new Promise(r => setTimeout(r, 200));
    } catch (e) {
      console.error(`❌ 오류 (${biz.file}):`, e.message);
    }
  }

  console.log('🎉 완료! 서버를 재시작하면 지도에 정확한 위치로 핀이 찍힙니다.');
}

updateAll();
