import { CRITERIA_KEYS } from '../../utils/constants'
import styles from './DetailModal.module.css'

const COLOR_HEX = { green: '#22c55e', yellow: '#eab308', orange: '#f97316', red: '#ef4444' }

export default function DetailModal({ biz, onClose, onWriteReview }) {
  if (!biz) return null
  const hex = COLOR_HEX[biz.color] || '#3b82f6'

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal large">
        <button className="modal-close" onClick={onClose}>✕</button>

        {/* 헤더 */}
        <div className={styles.header}>
          <div className={styles.headerInfo}>
            <h2 className={styles.bizTitle}>{biz.name}</h2>
            <p className={styles.bizMeta}>{biz.area} · {biz.industry} · 리뷰 {biz.reviewCount}개</p>
            <div className={styles.tags}>
              {biz.highlights?.map(h => <span key={h} className="tag ok">✓ {h}</span>)}
              {biz.cautions?.map(c => <span key={c} className="tag warn">⚠ {c}</span>)}
            </div>
          </div>
          <div className={styles.scoreCircle} style={{ background: hex }}>
            <span className={styles.scoreNum}>{biz.cleanScore}</span>
            <span className={styles.scoreLabel}>클린지수</span>
          </div>
        </div>

        {/* O/X 통계 */}
        <h3 className="section-title">📊 항목별 준수 현황</h3>
        <table className={styles.table}>
          <thead>
            <tr><th>항목</th><th>결과</th><th>위반율</th><th>통계</th></tr>
          </thead>
          <tbody>
            {CRITERIA_KEYS.map(k => {
              const s = biz.oxStats?.[k]
              if (!s) return null
              const ok = s.violationRate < 30
              return (
                <tr key={k}>
                  <td>{k}</td>
                  <td className={ok ? styles.okText : styles.warnText}>{ok ? '✅' : '❌'}</td>
                  <td>{s.violationRate}%</td>
                  <td>{s.ok}명 준수 / {s.violation}명 위반</td>
                </tr>
              )
            })}
          </tbody>
        </table>

        {/* 후기 목록 */}
        <h3 className="section-title">💬 후기 목록</h3>
        {biz.reviews?.length ? (
          <div className={styles.reviewList}>
            {biz.reviews.map((r, i) => (
              <div key={i} className={styles.reviewItem}>
                <p>{r.text || '(내용 없음)'}</p>
                <span className={styles.reviewDate}>{r.date}</span>
              </div>
            ))}
          </div>
        ) : (
          <p style={{ color: 'var(--text-sub)', fontSize: 14 }}>아직 작성된 후기가 없습니다.</p>
        )}

        <button className="btn-primary full-width" style={{ marginTop: 20, padding: '12px', fontSize: 15 }}
          onClick={() => { onClose(); onWriteReview() }}>
          ✏️ 이 사업장 후기 작성하기
        </button>
      </div>
    </div>
  )
}
