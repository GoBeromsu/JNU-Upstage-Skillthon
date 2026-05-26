import { CRITERIA_KEYS, COLOR_MAP } from '../utils/constants'
import styles from './MapPopup.module.css'

export default function MapPopup({ biz, onClose, onViewDetail, below = false, arrowOffset = 0 }) {
  if (!biz) return null

  const hex = COLOR_MAP[biz.color] || '#3b82f6'
  const passCount = CRITERIA_KEYS.filter(k => (biz.oxStats?.[k]?.violationRate ?? 0) < 30).length
  const violateCount = CRITERIA_KEYS.length - passCount

  const scoreLabel = { green: '우수', yellow: '보통', orange: '주의', red: '위험' }

  return (
    <div className={styles.popup}>
      <button className={styles.closeBtn} onClick={onClose}>✕</button>

      {/* 헤더 */}
      <div className={styles.header}>
        <div className={styles.scoreCircle} style={{ background: hex }}>
          <span className={styles.scoreNum}>{biz.cleanScore}</span>
          <span className={styles.scoreUnit}>점</span>
        </div>
        <div className={styles.bizInfo}>
          <div className={styles.bizName}>{biz.name}</div>
          <div className={styles.bizMeta}>{biz.area} · {biz.industry}</div>
          <span className={styles.scoreBadge} style={{ background: hex, color: biz.color === 'yellow' ? '#1e293b' : '#fff' }}>
            {scoreLabel[biz.color] || ''}
          </span>
        </div>
      </div>

      {/* 준수 요약 */}
      <div className={styles.summary}>
        <span className={styles.summaryGreen}>✅ {passCount}항목 준수</span>
        <span className={styles.summarySep}>|</span>
        <span className={styles.summaryRed}>❌ {violateCount}항목 위반</span>
        <span className={styles.summarySep}>|</span>
        <span className={styles.summaryGray}>📝 후기 {biz.reviewCount}개</span>
      </div>

      {/* O/X 미니 바 */}
      <div className={styles.oxList}>
        {CRITERIA_KEYS.map(k => {
          const stat = biz.oxStats?.[k]
          const rate = stat?.violationRate ?? 0
          const pass = rate < 30
          return (
            <div key={k} className={styles.oxItem}>
              <span className={pass ? styles.oxOk : styles.oxFail}>{pass ? '✓' : '✗'}</span>
              <span className={styles.oxLabel}>{k}</span>
              <span className={styles.oxRate} style={{ color: pass ? '#16a34a' : '#dc2626' }}>
                {rate}%
              </span>
            </div>
          )
        })}
      </div>

      {/* 하이라이트 태그 */}
      {(biz.highlights?.length > 0 || biz.cautions?.length > 0) && (
        <div className={styles.tags}>
          {biz.highlights?.slice(0, 2).map(h => (
            <span key={h} className="tag ok">✓ {h}</span>
          ))}
          {biz.cautions?.slice(0, 2).map(c => (
            <span key={c} className="tag warn">⚠ {c}</span>
          ))}
        </div>
      )}

      {/* 자주 올라오는 공고 내역 */}
      {biz.jobPostings?.length > 0 && (
        <div className={styles.jobSection}>
          <div className={styles.jobTitle}>📋 자주 올라오는 공고</div>
          <div className={styles.jobList}>
            {biz.jobPostings.map((jp, i) => (
              <div key={i} className={styles.jobItem}>
                <div className={styles.jobName}>{jp.title}</div>
                <div className={styles.jobMeta}>{jp.pay} · {jp.schedule}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* 버튼 영역 */}
      <div className={styles.actions}>
        <button
          className={styles.detailBtn}
          onClick={() => onViewDetail(biz.businessId)}
        >
          후기 자세히 보기 →
        </button>
      </div>

      {/* 화살표 — 방향 + 좌우 클램핑 보정 */}
      <div
        className={below ? styles.arrowTop : styles.arrow}
        style={{ left: `calc(50% + ${arrowOffset}px)` }}
      />
    </div>
  )
}
