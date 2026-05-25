import { useState, useEffect } from 'react'
import { Routes, Route, useNavigate } from 'react-router-dom'

import { AuthProvider }  from './contexts/AuthContext'
import { MapProvider }   from './contexts/MapContext'

import Header    from './components/Header'
import MapView   from './components/MapView'
import Sidebar   from './components/Sidebar'
import LoginModal from './components/modals/LoginModal'
import LawModal   from './components/modals/LawModal'

import ReviewDetailPage    from './pages/ReviewDetailPage'
import WriteReviewPage     from './pages/WriteReviewPage'
import KakaoCallback       from './pages/KakaoCallback'
import ContractAnalyzePage from './pages/ContractAnalyzePage'
import AdminPage           from './pages/AdminPage'

import styles from './App.module.css'

/* ── 루트: Provider + 라우터 ─────────────────────────────── */
export default function App() {
  return (
    <AuthProvider>
      <MapProvider>
        <Routes>
          <Route path="/"                    element={<MainMap />} />
          <Route path="/business/:id"        element={<ReviewDetailPage />} />
          <Route path="/business/:id/write"  element={<WriteReviewPage />} />
          <Route path="/write"               element={<WriteReviewPage />} />
          <Route path="/contract"            element={<ContractAnalyzePage />} />
          <Route path="/admin"              element={<AdminPage />} />
          <Route path="/oauth/kakao"         element={<KakaoCallback />} />
        </Routes>
        {/* 전역 로그인 모달 */}
        <LoginModal />
      </MapProvider>
    </AuthProvider>
  )
}

/* ── 메인 지도 페이지 ─────────────────────────────────────── */
function MainMap() {
  const navigate = useNavigate()
  const [businesses, setBusinesses] = useState([])
  const [ranking,    setRanking]    = useState([])
  const [selectedBiz, setSelectedBiz] = useState(null)
  const [modal, setModal] = useState(null) // 'law'

  useEffect(() => { loadData() }, [])

  async function loadData() {
    try {
      const [bizRes, rankRes] = await Promise.all([
        fetch('/api/businesses'),
        fetch('/api/businesses/ranking'),
      ])
      setBusinesses(await bizRes.json())
      setRanking(await rankRes.json())
    } catch (e) {
      console.error('데이터 로드 실패:', e)
    }
  }

  return (
    <div className={styles.app}>
      <Header
        onLawOpen={()      => setModal('law')}
        onContractOpen={() => navigate('/contract')}
      />

      <main className={styles.main}>
        <MapView
          businesses={businesses}
          onSelectBiz={setSelectedBiz}
        />
        <Sidebar
          ranking={ranking}
          onSelectBiz={setSelectedBiz}
        />
      </main>

      {modal === 'law' && <LawModal onClose={() => setModal(null)} />}
    </div>
  )
}
