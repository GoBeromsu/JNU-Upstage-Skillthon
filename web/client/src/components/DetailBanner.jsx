import styles from './DetailBanner.module.css'

export default function DetailBanner({ biz, onDetail, onReview, onClose }) {
  if (!biz) return null
  return (
    <div className={styles.banner}>
      <div className={styles.inner}>
        <div className={styles.info}>
          <span className={`score-badge ${biz.color}`}>{biz.cleanScore}점</span>
          <div>
            <div className={styles.name}>{biz.name}</div>
            <div className={styles.meta}>{biz.area} · {biz.industry} · 리뷰 {biz.reviewCount}개</div>
          </div>
        </div>
        <div className={styles.actions}>
          <button className="btn-outline" onClick={onDetail}>후기 자세히 보기</button>
          <button className="btn-primary" onClick={onReview}>후기 남기기</button>
        </div>
        <button className={styles.close} onClick={onClose}>✕</button>
      </div>
    </div>
  )
}
