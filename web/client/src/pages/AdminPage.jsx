import { useState, useEffect, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import styles from './AdminPage.module.css'

const STATUS_LABEL = { pending: '대기', approved: '승인', rejected: '반려' }
const STATUS_CLS   = { pending: styles.badgePending, approved: styles.badgeApproved, rejected: styles.badgeRejected }

const CRITERIA_NAMES = {
  minimum_wage:        '최저시급 준수',
  break_time:          '휴게시간 보장',
  paid_holiday:        '주휴수당 지급',
  written_contract:    '근로계약서 작성',
  four_insurances:     '4대보험 가입',
}

export default function AdminPage() {
  const navigate = useNavigate()
  const { isAdmin, adminHeaders, isLoggedIn } = useAuth()

  const [tab,      setTab]      = useState('pending')   // 'pending' | 'all'
  const [reviews,  setReviews]  = useState([])
  const [loading,  setLoading]  = useState(false)
  const [actionId, setActionId] = useState(null)        // 처리 중인 리뷰 ID
  const [rejectId, setRejectId] = useState(null)        // 반려 입력 중인 리뷰 ID
  const [rejectReason, setRejectReason] = useState('')
  const [toast,    setToast]    = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null)  // 이미지 미리보기

  // 관리자 아닐 경우 메인으로 리다이렉트
  useEffect(() => {
    if (isLoggedIn && !isAdmin) navigate('/')
  }, [isLoggedIn, isAdmin, navigate])

  const fetchReviews = useCallback(async () => {
    if (!isAdmin) return
    setLoading(true)
    try {
      const endpoint = tab === 'pending' ? '/api/admin/pending' : '/api/admin/all'
      const res  = await fetch(endpoint, { headers: adminHeaders() })
      const data = await res.json()
      if (data.error) throw new Error(data.error)
      setReviews(Array.isArray(data) ? data : [])
    } catch (e) {
      showToast('❌ ' + e.message, 'error')
    } finally {
      setLoading(false)
    }
  }, [tab, isAdmin, adminHeaders])

  useEffect(() => { fetchReviews() }, [fetchReviews])

  function showToast(msg, type = 'success') {
    setToast({ msg, type })
    setTimeout(() => setToast(null), 3000)
  }

  async function handleApprove(id) {
    setActionId(id)
    try {
      const res  = await fetch(`/api/admin/approve/${id}`, {
        method: 'POST',
        headers: adminHeaders(),
      })
      const data = await res.json()
      if (data.error) throw new Error(data.error)
      showToast('✅ 승인 완료! 사업장 데이터에 반영되었습니다.')
      fetchReviews()
    } catch (e) {
      showToast('❌ ' + e.message, 'error')
    } finally {
      setActionId(null)
    }
  }

  async function handleReject(id) {
    if (!rejectReason.trim()) { showToast('반려 사유를 입력해주세요.', 'error'); return }
    setActionId(id)
    try {
      const res  = await fetch(`/api/admin/reject/${id}`, {
        method:  'POST',
        headers: adminHeaders(),
        body:    JSON.stringify({ reason: rejectReason }),
      })
      const data = await res.json()
      if (data.error) throw new Error(data.error)
      showToast('🚫 반려 처리되었습니다.')
      setRejectId(null)
      setRejectReason('')
      fetchReviews()
    } catch (e) {
      showToast('❌ ' + e.message, 'error')
    } finally {
      setActionId(null)
    }
  }

  const pendingCount = reviews.filter(r => r.status === 'pending').length

  if (!isAdmin) return null

  return (
    <div className={styles.page}>
      {/* 상단 바 */}
      <div className={styles.topBar}>
        <button className={styles.backBtn} onClick={() => navigate('/')}>← 메인으로</button>
        <span className={styles.topTitle}>🛠️ 관리자 페이지</span>
        <span className={styles.topSub}>후기 검수 및 승인</span>
      </div>

      {/* 탭 */}
      <div className={styles.tabBar}>
        <button
          className={`${styles.tab} ${tab === 'pending' ? styles.tabActive : ''}`}
          onClick={() => setTab('pending')}
        >
          대기 중
          {pendingCount > 0 && <span className={styles.badge}>{pendingCount}</span>}
        </button>
        <button
          className={`${styles.tab} ${tab === 'all' ? styles.tabActive : ''}`}
          onClick={() => setTab('all')}
        >
          전체 내역
        </button>
      </div>

      {/* 목록 */}
      <div className={styles.list}>
        {loading && <div className={styles.empty}>⏳ 불러오는 중...</div>}

        {!loading && reviews.length === 0 && (
          <div className={styles.empty}>
            {tab === 'pending' ? '검수 대기 중인 후기가 없습니다.' : '등록된 후기가 없습니다.'}
          </div>
        )}

        {!loading && reviews.map(r => (
          <div key={r.id} className={styles.card}>
            {/* 카드 헤더 */}
            <div className={styles.cardHeader}>
              <div className={styles.bizName}>{r.business_name}</div>
              <span className={`${styles.statusBadge} ${STATUS_CLS[r.status]}`}>
                {STATUS_LABEL[r.status] || r.status}
              </span>
            </div>

            {/* 메타 정보 */}
            <div className={styles.metaRow}>
              <span>📍 {r.area || '-'}</span>
              <span>🏷️ {r.industry || '-'}</span>
              <span>👥 동시간대 {r.worker_count ?? '-'}명</span>
              <span>🕐 {r.submitted_at}</span>
            </div>

            {/* 체크리스트 */}
            {r.criteriaFlags && Object.keys(r.criteriaFlags).length > 0 && (
              <div className={styles.criteria}>
                {Object.entries(r.criteriaFlags).map(([k, v]) => (
                  <span key={k} className={`${styles.criteriaItem} ${v ? styles.criteriaOk : styles.criteriaNg}`}>
                    {v ? '✅' : '❌'} {CRITERIA_NAMES[k] || k}
                  </span>
                ))}
              </div>
            )}

            {/* 후기 텍스트 */}
            {(r.purified_text || r.review_text) && (
              <div className={styles.reviewText}>
                <span className={styles.reviewLabel}>후기</span>
                {r.purified_text || r.review_text}
              </div>
            )}

            {/* 인증 파일 */}
            {r.proofFiles?.length > 0 && (
              <div className={styles.proofSection}>
                <div className={styles.proofLabel}>📎 인증 자료 ({r.proofFiles.length}개)</div>
                <div className={styles.proofGrid}>
                  {r.proofFiles.map((f, i) => (
                    f.mimetype?.startsWith('image/') ? (
                      <img
                        key={i}
                        src={f.url}
                        alt={f.originalName || `인증${i + 1}`}
                        className={styles.proofImg}
                        onClick={() => setPreviewUrl(f.url)}
                      />
                    ) : (
                      <span key={i} className={styles.proofFile}>
                        📄 {f.originalName || `파일${i + 1}`}
                      </span>
                    )
                  ))}
                </div>
              </div>
            )}

            {/* 반려 사유 (반려된 경우) */}
            {r.status === 'rejected' && r.reject_reason && (
              <div className={styles.rejectReason}>
                🚫 반려 사유: {r.reject_reason}
              </div>
            )}

            {/* 액션 버튼 (대기 중인 경우만) */}
            {r.status === 'pending' && (
              <div className={styles.actions}>
                {rejectId === r.id ? (
                  <div className={styles.rejectForm}>
                    <input
                      className={styles.rejectInput}
                      placeholder="반려 사유를 입력하세요"
                      value={rejectReason}
                      onChange={e => setRejectReason(e.target.value)}
                      onKeyDown={e => e.key === 'Enter' && handleReject(r.id)}
                      autoFocus
                    />
                    <button
                      className={styles.btnRejectConfirm}
                      onClick={() => handleReject(r.id)}
                      disabled={actionId === r.id}
                    >
                      {actionId === r.id ? '처리 중...' : '반려 확정'}
                    </button>
                    <button
                      className={styles.btnCancel}
                      onClick={() => { setRejectId(null); setRejectReason('') }}
                    >
                      취소
                    </button>
                  </div>
                ) : (
                  <>
                    <button
                      className={styles.btnApprove}
                      onClick={() => handleApprove(r.id)}
                      disabled={actionId === r.id}
                    >
                      {actionId === r.id ? '처리 중...' : '✅ 승인'}
                    </button>
                    <button
                      className={styles.btnReject}
                      onClick={() => { setRejectId(r.id); setRejectReason('') }}
                      disabled={actionId === r.id}
                    >
                      🚫 반려
                    </button>
                  </>
                )}
              </div>
            )}
          </div>
        ))}
      </div>

      {/* 토스트 */}
      {toast && (
        <div className={`${styles.toast} ${toast.type === 'error' ? styles.toastError : ''}`}>
          {toast.msg}
        </div>
      )}

      {/* 이미지 미리보기 모달 */}
      {previewUrl && (
        <div className={styles.previewOverlay} onClick={() => setPreviewUrl(null)}>
          <img
            src={previewUrl}
            alt="미리보기"
            className={styles.previewImg}
            onClick={e => e.stopPropagation()}
          />
          <button className={styles.previewClose} onClick={() => setPreviewUrl(null)}>✕</button>
        </div>
      )}
    </div>
  )
}
