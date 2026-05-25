import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import styles from './Header.module.css'

export default function Header({ onLawOpen, onContractOpen }) {
  const { isLoggedIn, user, isAdmin, logout, redirectToKakao } = useAuth()
  const navigate = useNavigate()

  return (
    <header className={styles.header}>
      <div className={styles.left}>
        <span className={styles.logoIcon}>🗺️</span>
        <span className={styles.logoText}>전남대 클린알바맵</span>
      </div>
      <div className={styles.right}>
        <button className="btn-ghost" onClick={onLawOpen}>근로기준법 안내</button>
        <button className="btn-ghost" onClick={onContractOpen}>📄 계약서 분석</button>
        {isLoggedIn ? (
          <div className={styles.userArea}>
            {isAdmin && (
              <button className={styles.adminBtn} onClick={() => navigate('/admin')}>
                🛠️ 관리자
              </button>
            )}
            <div className={styles.profileCircle}>
              {user?.profileImage
                ? <img src={user.profileImage} alt={user.nickname} style={{ width: '100%', height: '100%', borderRadius: '50%', objectFit: 'cover' }} />
                : (user?.nickname?.[0] || '나')}
            </div>
            <span className={styles.nickname}>{user?.nickname || '전남대생'}</span>
            <button className={styles.logoutBtn} onClick={logout}>로그아웃</button>
          </div>
        ) : (
          <button className="btn-primary" onClick={redirectToKakao}>
            <img
              src="https://developers.kakao.com/assets/img/about/logos/kakaolink/kakaolink_btn_small.png"
              alt="" style={{ width: 16, height: 16, verticalAlign: 'middle', marginRight: 4 }}
            />
            카카오 로그인
          </button>
        )}
      </div>
    </header>
  )
}
