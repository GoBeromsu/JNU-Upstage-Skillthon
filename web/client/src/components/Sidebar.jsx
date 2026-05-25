import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth }   from '../contexts/AuthContext'
import { useMapCtx } from '../contexts/MapContext'
import styles from './Sidebar.module.css'

/* ── 사업장 카드 ─────────────────────────────────────────── */
function BizCard({ biz, rank, onClick }) {
  const rankClass = rank === 1 ? styles.gold : rank === 2 ? styles.silver : rank === 3 ? styles.bronze : ''
  return (
    <div className={styles.card} onClick={() => onClick(biz)}>
      <div className={styles.cardTop}>
        {rank && <div className={`${styles.rankBadge} ${rankClass}`}>{rank}</div>}
        <div className={styles.cardInfo}>
          <div className={styles.cardName}>{biz.name}</div>
          <div className={styles.cardMeta}>{biz.area} · {biz.industry} · 리뷰 {biz.reviewCount}개</div>
        </div>
        <span className={`score-badge ${biz.color}`}>{biz.cleanScore}점</span>
      </div>
      {(biz.highlights?.length > 0 || biz.cautions?.length > 0) && (
        <div className={styles.cardTags}>
          {biz.highlights?.slice(0, 2).map(h => <span key={h} className="tag ok">✓ {h}</span>)}
          {biz.cautions?.slice(0, 1).map(c  => <span key={c}  className="tag warn">⚠ {c}</span>)}
        </div>
      )}
    </div>
  )
}

/* ── 메인 사이드바 ────────────────────────────────────────── */
export default function Sidebar({ ranking, onSelectBiz }) {
  const navigate = useNavigate()
  const { requireLogin }      = useAuth()
  const { panTo, highlight }  = useMapCtx()

  const [query,        setQuery]        = useState('')
  const [searchResult, setSearchResult] = useState(null)   // null = 랭킹 모드
  const [loading,      setLoading]      = useState(false)

  /* ── 검색 ─────────────────────────────────────────────── */
  async function handleSearch() {
    if (!query.trim()) return
    setLoading(true)
    try {
      const res    = await fetch('/api/skills/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query }),
      })
      const result = await res.json()
      setSearchResult(result)

      // 첫 번째 결과로 지도 이동 + 핀 강조
      const first = result.results?.[0] ?? result.recommendations?.[0]
      if (first?.lat && first?.lon) {
        panTo(first.lat, first.lon)
        highlight(first.businessId)
      }
    } finally {
      setLoading(false)
    }
  }

  /* ── 검색 초기화 ──────────────────────────────────────── */
  function handleReset() {
    setQuery('')
    setSearchResult(null)
  }

  /* ── 카드 클릭: 지도 동기화 → 후기 상세 페이지 이동 ─── */
  function handleCardClick(biz) {
    onSelectBiz?.(biz)
    if (biz.lat && biz.lon) {
      panTo(biz.lat, biz.lon)
      highlight(biz.businessId)
    }
    navigate(`/business/${biz.businessId}`)
  }

  const isSearchMode = searchResult !== null
  const items = isSearchMode
    ? (searchResult?.results ?? searchResult?.recommendations ?? [])
    : ranking

  const isEmpty = items.length === 0

  return (
    <aside className={styles.sidebar}>
      {/* 검색창 */}
      <div className={styles.searchBox}>
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && handleSearch()}
          placeholder="🔍 업체명, 상권, 조건 검색..."
          className={styles.searchInput}
        />
        <button className="btn-primary" onClick={handleSearch} disabled={loading}>
          {loading ? '…' : '검색'}
        </button>
      </div>

      {/* 리스트 헤더 */}
      <div className={styles.listHeader}>
        {isSearchMode ? (
          <>
            <span className={styles.listTitle}>검색 결과</span>
            <button className={styles.resetBtn} onClick={handleReset}>← 랭킹으로</button>
          </>
        ) : (
          <span className={styles.listTitle}>🏆 클린 랭킹</span>
        )}
      </div>

      {/* 리스트 */}
      <div className={styles.list}>
        {isSearchMode && searchResult?.summary && (
          <div className={styles.summary}>{searchResult.summary}</div>
        )}

        {isEmpty ? (
          <div className={styles.emptyState}>
            {isSearchMode ? (
              <>
                <p>아직 등록된 후기가 없습니다.<br />첫 번째 후기를 작성해 주세요.</p>
                <button
                  className="btn-primary"
                  style={{ marginTop: 14 }}
                  onClick={() => {
                    if (!requireLogin('/write')) return
                    navigate('/write')
                  }}
                >
                  ✏️ 후기 작성하기
                </button>
              </>
            ) : (
              <p>등록된 사업장이 없습니다.</p>
            )}
          </div>
        ) : (
          items.map(b => (
            <BizCard
              key={b.businessId || b.name}
              biz={b}
              rank={!isSearchMode ? b.rank : null}
              onClick={handleCardClick}
            />
          ))
        )}
      </div>
    </aside>
  )
}
