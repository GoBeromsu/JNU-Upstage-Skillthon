import { useAuth } from '../../contexts/AuthContext'
import styles from './LoginModal.module.css'

export default function LoginModal() {
  const { showLoginModal, setShowLoginModal, redirectToKakao } = useAuth()
  if (!showLoginModal) return null

  return (
    <div className={styles.overlay} onClick={() => setShowLoginModal(false)}>
      <div className={styles.modal} onClick={e => e.stopPropagation()}>
        <div className={styles.icon}>🔐</div>
        <h2 className={styles.title}>로그인이 필요합니다</h2>
        <p className={styles.desc}>
          후기 작성은 로그인 이후<br />이용 가능합니다.
        </p>
        <button className={styles.kakaoBtn} onClick={redirectToKakao}>
          <img
            src="https://developers.kakao.com/assets/img/about/logos/kakaolink/kakaolink_btn_small.png"
            alt=""
          />
          카카오로 로그인
        </button>
        <button className={styles.cancelBtn} onClick={() => setShowLoginModal(false)}>
          취소
        </button>
      </div>
    </div>
  )
}
