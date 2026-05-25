import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { CRITERIA_KEYS } from '../utils/constants'
import { useAuth } from '../contexts/AuthContext'
import AlertModal from '../components/modals/AlertModal'
import styles from './WriteReviewPage.module.css'

export default function WriteReviewPage() {
  const { id }       = useParams()           // 없으면 undefined (진입점 A)
  const navigate     = useNavigate()
  const { isLoggedIn, requireLogin } = useAuth()

  /* ── 진입점 A: 장소 검색 상태 ─────────────────────────── */
  const [placeQuery,   setPlaceQuery]   = useState('')
  const [placeResults, setPlaceResults] = useState([])
  const [selectedBiz,  setSelectedBiz]  = useState(null)  // 진입점 B·C: API에서 로드

  /* ── 폼 상태 ──────────────────────────────────────────── */
  const [flags,          setFlags]          = useState(() => Object.fromEntries(CRITERIA_KEYS.map(k => [k, false])))
  const [coworkerCount,  setCoworkerCount]  = useState('')
  const [reviewText,     setReviewText]     = useState('')
  const [purifyResult,   setPurifyResult]   = useState(null)
  const [selectedOption, setSelectedOption] = useState(null)
  const [proofFiles,     setProofFiles]     = useState([])
  const [loading,        setLoading]        = useState(false)
  const [purifyLoading,  setPurifyLoading]  = useState(false)
  const [bizLoading,     setBizLoading]     = useState(!!id)
  const [alertModal,     setAlertModal]     = useState({ open: false, icon: '', title: '', message: '', onClose: null })

  function showAlert({ icon = '✅', title = '', message = '', onClose = null } = {}) {
    setAlertModal({ open: true, icon, title, message, onClose })
  }
  function closeAlert() {
    const cb = alertModal.onClose
    setAlertModal(m => ({ ...m, open: false }))
    cb?.()
  }

  /* ── 비로그인 Guard ────────────────────────────────────── */
  useEffect(() => {
    if (!requireLogin(id ? `/business/${id}/write` : '/write')) {
      navigate('/')
    }
  }, []) // eslint-disable-line

  /* ── 진입점 B·C: 사업장 정보 자동 로드 ──────────────── */
  useEffect(() => {
    if (!id) return
    fetch(`/api/businesses/${encodeURIComponent(id)}`)
      .then(r => r.json())
      .then(data => { if (!data.error) setSelectedBiz(data) })
      .catch(() => {})
      .finally(() => setBizLoading(false))
  }, [id])

  /* ── 카카오 SDK 초기화 (MapView 없이 이 페이지 직접 방문 시 대비) ── */
  useEffect(() => {
    if (window.kakao?.maps?.services) return   // 이미 로드됨
    if (!window.kakao) return                  // SDK 스크립트 자체가 없음
    window.kakao.maps.load(() => {})           // autoload=false 해제
  }, [])

  /* ── 진입점 A: 카카오 장소 검색 ─────────────────────── */
  function searchKakaoPlaces() {
    if (!placeQuery.trim()) return
    if (!window.kakao?.maps?.services) {
      showAlert({ icon: '⏳', title: '잠시만요', message: '카카오 지도 서비스를 불러오는 중입니다.\n잠시 후 다시 시도해주세요.' })
      return
    }
    const ps = new window.kakao.maps.services.Places()
    ps.keywordSearch(
      placeQuery + ' 광주 북구',
      (results, status) => {
        if (status === window.kakao.maps.services.Status.OK) {
          setPlaceResults(results.slice(0, 5))
        } else {
          setPlaceResults([])
        }
      },
      { location: new window.kakao.maps.LatLng(35.1767, 126.9095), radius: 3000 }
    )
  }

  function selectPlace(place) {
    setSelectedBiz({
      businessId:  place.id,
      name:        place.place_name,
      area:        place.address_name,
      industry:    place.category_group_name || '기타',
      cleanScore:  null,
      color:       'green',
      reviewCount: 0,
    })
    setPlaceResults([])
    setPlaceQuery('')
  }

  /* ── AI 순화 ──────────────────────────────────────────── */
  async function handlePurify() {
    if (!reviewText.trim()) return showAlert({ icon: '✏️', title: '내용을 입력해주세요', message: '후기 내용을 먼저 입력해주세요.' })
    setPurifyLoading(true)
    try {
      const res  = await fetch('/api/skills/purify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reviewText }),
      })
      const data = await res.json()
      if (data.error) throw new Error(data.error)
      setPurifyResult(data)
      setSelectedOption(null)
    } catch (e) {
      showAlert({ icon: '❌', title: '오류', message: '순화 처리 중 오류가 발생했습니다:\n' + e.message })
    } finally {
      setPurifyLoading(false)
    }
  }

  /* ── 제출 ──────────────────────────────────────────────── */
  async function handleSubmit() {
    if (!selectedBiz) return showAlert({ icon: '🏢', title: '사업장을 선택해주세요', message: '후기를 남길 사업장을 먼저 선택해주세요.' })
    setLoading(true)
    try {
      const fd = new FormData()
      fd.append('businessId',    selectedBiz.businessId)
      fd.append('businessName',  selectedBiz.name || '')
      fd.append('area',          selectedBiz.area || '')
      fd.append('industry',      selectedBiz.industry || '')
      fd.append('criteriaFlags', JSON.stringify(flags))
      fd.append('reviewText',    reviewText)
      fd.append('purifiedText',  selectedOption || '')
      fd.append('coworkerCount', coworkerCount)
      proofFiles.forEach(f => fd.append('proofFiles', f))

      const res  = await fetch('/api/reviews', { method: 'POST', body: fd })
      const data = await res.json()
      if (data.error) throw new Error(data.error)

      showAlert({
        icon: '✅',
        title: '제출 완료!',
        message: '관리자에 의해 검수중입니다.\n검수 완료 후 지도에 반영됩니다.',
        onClose: () => navigate(id ? `/business/${id}` : '/'),
      })
    } catch (e) {
      showAlert({ icon: '❌', title: '제출 오류', message: e.message })
    } finally {
      setLoading(false)
    }
  }

  if (bizLoading) {
    return (
      <div style={{ display:'flex', alignItems:'center', justifyContent:'center', height:'100vh' }}>
        <p>사업장 정보를 불러오는 중...</p>
      </div>
    )
  }

  return (
    <div className={styles.page}>
      <AlertModal
        open={alertModal.open}
        icon={alertModal.icon}
        title={alertModal.title}
        message={alertModal.message}
        onClose={closeAlert}
      />

      {/* 상단 바 */}
      <div className={styles.topBar}>
        <button className={styles.backBtn} onClick={() => navigate(id ? `/business/${id}` : '/')}>
          ← {id ? '후기 목록으로' : '메인으로'}
        </button>
        <span className={styles.topTitle}>후기 작성</span>
      </div>

      <div className={styles.content}>

        {/* ── 진입점 A: 사업장 검색 ── */}
        {!id && (
          <section className={styles.section}>
            <h2 className={styles.sectionTitle}>🏢 사업장 선택 <span style={{ color: 'var(--red)' }}>*필수</span></h2>
            <p className={styles.sectionDesc}>후기를 남길 사업장을 검색하세요.</p>

            {selectedBiz ? (
              <div className={styles.selectedPlace}>
                <div>
                  <div style={{ fontWeight: 700 }}>{selectedBiz.name}</div>
                  <div style={{ fontSize: 12, color: 'var(--text-sub)', marginTop: 2 }}>{selectedBiz.area}</div>
                </div>
                <button
                  className="btn-outline"
                  style={{ fontSize: 12, padding: '4px 10px' }}
                  onClick={() => setSelectedBiz(null)}
                >변경</button>
              </div>
            ) : (
              <>
                <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                  <input
                    className={styles.placeInput}
                    value={placeQuery}
                    onChange={e => setPlaceQuery(e.target.value)}
                    onKeyDown={e => e.key === 'Enter' && searchKakaoPlaces()}
                    placeholder="사업장 이름 검색 (예: 파스쿠찌 후문)"
                  />
                  <button className="btn-primary" onClick={searchKakaoPlaces}>검색</button>
                </div>
                {placeResults.length > 0 && (
                  <div className={styles.placeList}>
                    {placeResults.map(p => (
                      <div key={p.id} className={styles.placeItem} onClick={() => selectPlace(p)}>
                        <div style={{ fontWeight: 600, fontSize: 14 }}>{p.place_name}</div>
                        <div style={{ fontSize: 12, color: 'var(--text-sub)' }}>{p.address_name}</div>
                      </div>
                    ))}
                  </div>
                )}
              </>
            )}
          </section>
        )}

        {/* ── 진입점 B·C: 사업장 카드 자동 표시 ── */}
        {id && selectedBiz && (
          <div className={styles.bizCard}>
            {selectedBiz.cleanScore !== null && (
              <span className={`score-badge ${selectedBiz.color}`}>{selectedBiz.cleanScore}점</span>
            )}
            <div>
              <div className={styles.bizName}>{selectedBiz.name}</div>
              <div className={styles.bizMeta}>{selectedBiz.area} · {selectedBiz.industry}</div>
            </div>
          </div>
        )}

        {/* 체크리스트 */}
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>📋 근로기준법 준수 체크리스트 <span style={{ color: 'var(--red)' }}>*필수</span></h2>
          <p className={styles.sectionDesc}>위반한 항목을 체크해주세요 (체크 = 위반)</p>
          <div className={styles.checklist}>
            {CRITERIA_KEYS.map(k => (
              <label key={k} className={`${styles.checkItem} ${flags[k] ? styles.checked : ''}`}>
                <input
                  type="checkbox"
                  checked={flags[k]}
                  onChange={e => setFlags(p => ({ ...p, [k]: e.target.checked }))}
                />
                <span>{k}</span>
              </label>
            ))}
          </div>
        </section>

        {/* 동시간대 업무자 수 */}
        <section className={styles.section}>
          <div className="form-row">
            <label>동시간대 업무자 수
              <span style={{ color: 'var(--red)', fontWeight: 600 }}> *필수</span>
            </label>
            <select value={coworkerCount} onChange={e => setCoworkerCount(e.target.value)}>
              <option value="">선택 안 함</option>
              <option value="1인 근무">1인 근무</option>
              <option value="2~3명">2~3명</option>
              <option value="4~5명">4~5명</option>
              <option value="6명 이상">6명 이상</option>
            </select>
          </div>
        </section>

        {/* 근로 인증 자료 */}
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>
            📎 근로 인증 자료 <span style={{ color: 'var(--red)' }}>*필수</span>
          </h2>
          <p className={styles.sectionDesc}>근로계약서, 급여 입금 내역, 보험 내역 등</p>
          <input
            type="file" multiple accept="image/*,.pdf"
            onChange={e => setProofFiles(Array.from(e.target.files))}
            className={styles.fileInput}
          />
          {proofFiles.length > 0 && (
            <div className={styles.fileList}>
              {proofFiles.map(f => <span key={f.name} className="tag info">📎 {f.name}</span>)}
            </div>
          )}
        </section>

        {/* 주관식 후기 */}
        <section className={styles.section}>
          <h2 className={styles.sectionTitle}>
            💬 주관식 후기 <span style={{ color: 'var(--text-sub)', fontWeight: 400 }}>(선택)</span>
          </h2>
          <p className={styles.sectionDesc}>자유롭게 작성하면 AI가 법적 위험 표현을 순화해드립니다.</p>
          <textarea
            rows={4} value={reviewText}
            onChange={e => setReviewText(e.target.value)}
            placeholder="근무 경험을 자유롭게 작성해주세요..."
          />
          <button
            className="btn-outline full-width"
            style={{ marginTop: 8 }}
            onClick={handlePurify}
            disabled={purifyLoading}
          >
            {purifyLoading ? '⏳ AI 분석 중...' : '✨ AI 후기 순화'}
          </button>

          {purifyResult && (
            <div className={styles.purifyBox}>
              <div className={styles.purifyHeader}>
                <span className={`risk-badge ${purifyResult.risk_assessment?.risk_level}`}>
                  {purifyResult.risk_assessment?.risk_level}
                </span>
                <span className={styles.purifyIssues}>
                  {purifyResult.risk_assessment?.detected_issues?.join(' · ')}
                </span>
              </div>
              <p style={{ fontSize: 13, color: 'var(--text-sub)', marginBottom: 8 }}>
                아래 3가지 버전 중 하나를 선택해주세요:
              </p>
              {purifyResult.purified_options?.map(opt => (
                <div
                  key={opt.option_id}
                  className={`${styles.purifyOption} ${selectedOption === opt.text ? styles.selected : ''}`}
                  onClick={() => setSelectedOption(opt.text)}
                >
                  <div className={styles.optStyle}>{opt.style}</div>
                  <div className={styles.optText}>{opt.text}</div>
                </div>
              ))}
            </div>
          )}
        </section>

        {/* 제출 */}
        <div className={styles.submitArea}>
          <button
            className="btn-primary full-width"
            style={{ padding: '14px', fontSize: 16 }}
            onClick={handleSubmit}
            disabled={loading || !selectedBiz}
          >
            {loading ? '제출 중...' : '후기 제출하기'}
          </button>
          <p style={{ fontSize: 12, color: 'var(--text-sub)', textAlign: 'center', marginTop: 8 }}>
            관리자 검수 후 지도에 반영됩니다.
          </p>
        </div>
      </div>
    </div>
  )
}
