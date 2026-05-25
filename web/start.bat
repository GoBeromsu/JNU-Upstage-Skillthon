@echo off
chcp 65001 > nul
echo ================================================
echo  전남대 클린알바맵 개발 서버 시작
echo ================================================
echo.

:: .env 없으면 예시 파일 복사
if not exist "%~dp0server\.env" (
  copy "%~dp0server\.env.example" "%~dp0server\.env"
  echo [!] server/.env 파일을 생성했습니다. UPSTAGE_API_KEY를 설정해주세요.
)
if not exist "%~dp0client\.env" (
  copy "%~dp0client\.env.example" "%~dp0client\.env"
  echo [!] client/.env 파일을 생성했습니다. VITE_KAKAO_MAP_KEY를 설정해주세요.
)

:: 패키지 설치
echo [1/2] 서버 패키지 설치 중...
cd "%~dp0server" && npm install --silent

echo [2/2] 클라이언트 패키지 설치 중...
cd "%~dp0client" && npm install --silent

echo.
echo  React 개발서버: http://localhost:3000
echo  API 서버:       http://localhost:4000
echo  관리자 페이지:  http://localhost:3000/admin.html
echo.
echo  두 창이 열립니다. 모두 닫으면 종료됩니다.
echo.

:: 서버 & 클라이언트 동시 실행
start "API Server" cmd /k "cd /d %~dp0server && npm run dev"
timeout /t 2 > nul
start "React Dev Server" cmd /k "cd /d %~dp0client && npm run dev"

pause
