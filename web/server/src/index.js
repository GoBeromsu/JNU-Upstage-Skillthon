require('dotenv').config({ path: require('path').join(__dirname, '../.env') });

const express = require('express');
const cors = require('cors');
const path = require('path');

const app = express();
const PORT = process.env.PORT || 4000;

app.use(cors());
app.use(express.json());
app.use(express.urlencoded({ extended: true }));

// API 라우트
app.use('/api/auth',       require('./routes/auth'));
app.use('/api/businesses', require('./routes/businesses'));
app.use('/api/reviews',    require('./routes/reviews'));
app.use('/api/skills',     require('./routes/skills'));
app.use('/api/admin',      require('./routes/admin'));

// 업로드 파일 정적 서빙
const uploadsDir = path.join(__dirname, '../uploads');
app.use('/uploads', express.static(uploadsDir));

// 정적 파일 (프로덕션 빌드)
const clientDist = path.join(__dirname, '../../client/dist');
const fs = require('fs');
if (fs.existsSync(clientDist)) {
  app.use(express.static(clientDist));
  app.get('*', (req, res) => res.sendFile(path.join(clientDist, 'index.html')));
}

app.listen(PORT, '0.0.0.0', () => {
  console.log(`[클린알바맵] 서버 실행 중: http://0.0.0.0:${PORT}`);
});
