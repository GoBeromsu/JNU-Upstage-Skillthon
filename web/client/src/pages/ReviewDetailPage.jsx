import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { CRITERIA_KEYS, COLOR_MAP } from '../utils/constants'
import { useAuth } from '../contexts/AuthContext'
import styles from './ReviewDetailPage.module.css'

export default function ReviewDetailPage() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { requireLogin } = useAuth()
  const [biz, setBiz] = useState(null)
  const [loading, setLoading] = useState(true)

  function handleWriteReview() {
    if (!requireLogin(`/business/${id}/write`)) return
    navigate(`/business/${id}/write`)
  }

  useEffect(() => {
    fetch(`/api/businesses/${encodeURIComponent(id)}`)
      .then(r => r.json())
      .then(data => { setBiz(data); setLoading(false) })
      .catch(() => setLoading(false))
  }, [id])

  if (loading) return (
    <div className={styles.loadingWrap}>
      <div className="loading-spinner" style={{ borderTopColor: '#3b82f6', borderColor: '#e2e8f0' }} />
      <p>불러오는 중...</p>
    </div>
  )

  if (!biz || biz.error) return (
    <div className={styles.loadingWrap}>
      <p>사업장 정보를 찾을 수 없습니다.</p>
      <button className="btn-primary" onClick={() => navigate('/')} style={{ marginTop: 12 }}>
        지도로 돌아가기
      </button>
    </div>
  )

  const hex = COLOR_MAP[biz.color] || '#3b82f6'
  const scoreLabel = { green: '우수', yellow: '보통', orange: '주의', red: '위험' }

  return (
    <div className={styles.page}>
      {/* 상단 네비 */}
      <div className={styles.topBar}>
        <button className={styles.backBtn} onClick={() => navigate('/')}>
          ← 지도로 돌아가기
        </button>
      </div>

      <div className={styles.content}>
        {/* 사업장 헤더 */}
        <div className={styles.header}>
          <div className={styles.scoreCircle} style={{ background: hex }}>
            <span className={styles.scoreNum}>{biz.cleanScore}</span>
            <span className={styles.scoreLabel}>클린점수</span>
          </div>
          <div className={styles.headerInfo}>
            <h1 className={styles.bizName}>{biz.name}</h1>
            <p className={styles.bizMeta}>{biz.area} · {biz.industry} · 후기 {biz.reviewCount}개</p>
            <div style={{ display: 'flex', gap: 6, flexWrap: 'wrap', marginTop: 8 }}>
              {biz.highlights?.map(h => <span key={h} className="tag ok">✓ {h}</span>)}
              {biz.cautions?.map(c => <span key={c} className="tag warn">⚠ {c}</span>)}
            </div>
          </div>
        </div>

        {/* O/X 준수 현황 */}
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>📊 항목별 준수 현황</h2>
          <div className={styles.oxGrid}>
            {CRITERIA_KEYS.map(k => {
              const s = biz.oxStats?.[k]
              if (!s) return null
              const pass = s.violationRate < 30
              return (
                <div key={k} className={`${styles.oxCard} ${pass ? styles.oxPass : styles.oxFail}`}>
                  <div className={styles.oxIcon}>{pass ? '✅' : '❌'}</div>
                  <div className={styles.oxName}>{k}</div>
                  <div className={styles.oxBar}>
                    <div
                      className={styles.oxFill}
                      style={{
                        width: `${100 - s.violationRate}%`,
                        background: pass ? '#22c55e' : '#ef4444',
                      }}
                    />
                  </div>
                  <div className={styles.oxStat}>
                    <span style={{ color: '#16a34a' }}>{s.ok}명 준수</span>
                    {' / '}
                    <span style={{ color: '#dc2626' }}>{s.violation}명 위반</span>
                    {' ('}위반율 {s.violationRate}%{')'}
                  </div>
                </div>
              )
            })}
          </div>
        </section>

        {/* 후기 목록 */}
        <section className={styles.section}>
          <div className={styles.reviewHeader}>
            <h2 className={styles.sectionTitle}>💬 후기 목록</h2>
            <button
              className="btn-primary"
              onClick={handleWriteReview}
              style={{ padding: '7px 16px', fontSize: 13 }}
            >
              ✏️ 후기 남기기
            </button>
          </div>

          {biz.reviews?.length ? (
            <div className={styles.reviewList}>
              {biz.reviews.map((r, i) => {
                const violations = Object.entries(r.criteria_flags || {})
                  .filter(([, v]) => v).map(([k]) => k)
                return (
                  <div key={r.id || i} className={styles.reviewCard}>
                    <p className={styles.reviewText}>{r.text || '(내용 없음)'}</p>
                    {violations.length > 0 && (
                      <div className={styles.reviewTags}>
                        {violations.map(v => (
                          <span key={v} className="tag warn" style={{ fontSize: 11 }}>⚠ {v}</span>
                        ))}
                      </div>
                    )}
                    <span className={styles.reviewDate}>{r.date}</span>
                  </div>
                )
              })}
            </div>
          ) : (
            <div className={styles.emptyReview}>
              <p>아직 작성된 후기가 없습니다.</p>
              <button
                className="btn-primary"
                onClick={handleWriteReview}
                style={{ marginTop: 12 }}
              >
                첫 번째 후기 작성하기
              </button>
            </div>
          )}
        </section>
      </div>
    </div>
  )
}
