import { useState } from 'react'
import { CRITERIA_KEYS, AREAS, INDUSTRIES } from '../../utils/constants'
import styles from './ReviewModal.module.css'

export default function ReviewModal({ biz, onClose, onSubmit }) {
  const [formData, setFormData] = useState({
    businessName: biz?.name || '',
    area: biz?.area || '상대',
    industry: biz?.industry || '카페',
  })
  const [flags, setFlags] = useState(() =>
    Object.fromEntries(CRITERIA_KEYS.map(k => [k, false]))
  )
  const [coworkerCount, setCoworkerCount] = useState('')
  const [reviewText, setReviewText] = useState('')
  const [purifyResult, setPurifyResult] = useState(null)
  const [selectedOption, setSelectedOption] = useState(null)
  const [proofFiles, setProofFiles] = useState([])
  const [loading, setLoading] = useState(false)
  const [purifyLoading, setPurifyLoading] = useState(false)

  async function handlePurify() {
    if (!reviewText.trim()) return alert('후기 내용을 먼저 입력해주세요.')
    setPurifyLoading(true)
    try {
      const res = await fetch('/api/skills/purify', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ reviewText }),
      })
      const data = await res.json()
      if (data.error) throw new Error(data.error)
      setPurifyResult(data)
      setSelectedOption(null)
    } catch (e) {
      alert('순화 처리 중 오류가 발생했습니다: ' + e.message)
    } finally {
      setPurifyLoading(false)
    }
  }

  async function handleSubmit() {
    if (!formData.businessName) return alert('업체명을 입력해주세요.')
    setLoading(true)
    try {
      const fd = new FormData()
      fd.append('businessId', biz?.businessId || `${formData.businessName}_${formData.area}`)
      fd.append('businessName', formData.businessName)
      fd.append('area', formData.area)
      fd.append('industry', formData.industry)
      fd.append('criteriaFlags', JSON.stringify(flags))
      fd.append('reviewText', reviewText)
      fd.append('purifiedText', selectedOption || '')
      fd.append('coworkerCount', coworkerCount)
      proofFiles.forEach(f => fd.append('proofFiles', f))

      const res = await fetch('/api/reviews', { method: 'POST', body: fd })
      const data = await res.json()
      if (data.error) throw new Error(data.error)
      onClose()
      alert('후기가 제출되었습니다! 관리자 검수 후 지도에 반영됩니다.')
    } catch (e) {
      alert('제출 오류: ' + e.message)
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal">
        <button className="modal-close" onClick={onClose}>✕</button>
        <h2 className="modal-title">후기 작성</h2>
        <p className="modal-subtitle">근로기준법 기반 O/X 체크리스트로 작성됩니다.</p>

        {/* 사업장 정보 (기존 선택이 없을 때만) */}
        {!biz && (
          <div className={styles.bizForm}>
            <div className="form-row">
              <label>업체명 *</label>
              <input value={formData.businessName}
                onChange={e => setFormData(p => ({ ...p, businessName: e.target.value }))}
                placeholder="예: 스타벅스 상대점" />
            </div>
            <div className={styles.row2}>
              <div className="form-row" style={{ flex: 1 }}>
                <label>상권</label>
                <select value={formData.area}
                  onChange={e => setFormData(p => ({ ...p, area: e.target.value }))}>
                  {AREAS.map(a => <option key={a}>{a}</option>)}
                </select>
              </div>
              <div className="form-row" style={{ flex: 1 }}>
                <label>업종</label>
                <select value={formData.industry}
                  onChange={e => setFormData(p => ({ ...p, industry: e.target.value }))}>
                  {INDUSTRIES.map(i => <option key={i}>{i}</option>)}
                </select>
              </div>
            </div>
          </div>
        )}
        {biz && (
          <div className={styles.selectedBiz}>
            <span className={`score-badge ${biz.color}`}>{biz.cleanScore}점</span>
            <span><strong>{biz.name}</strong> · {biz.area} · {biz.industry}</span>
          </div>
        )}

        {/* O/X 체크리스트 */}
        <h3 className="section-title">📋 근로기준법 준수 체크리스트</h3>
        <p className="section-desc">위반한 항목을 체크해주세요 (체크 = 위반)</p>
        <div className={styles.checklist}>
          {CRITERIA_KEYS.map(k => (
            <label key={k} className={`${styles.checkItem} ${flags[k] ? styles.checked : ''}`}>
              <input type="checkbox" checked={flags[k]}
                onChange={e => setFlags(p => ({ ...p, [k]: e.target.checked }))} />
              <span>{k}</span>
            </label>
          ))}
        </div>

        {/* 동시간대 업무자 수 */}
        <div className="form-row" style={{ marginTop: 12 }}>
          <label>동시간대 업무자 수 <span style={{ color: 'var(--text-sub)', fontWeight: 400 }}>(선택 / 점수 미반영)</span></label>
          <select value={coworkerCount} onChange={e => setCoworkerCount(e.target.value)}>
            <option value="">선택 안 함</option>
            <option value="1인 근무">1인 근무</option>
            <option value="2~3명">2~3명</option>
            <option value="4~5명">4~5명</option>
            <option value="6명 이상">6명 이상</option>
          </select>
        </div>

        {/* 근로 인증 파일 */}
        <h3 className="section-title">📎 근로 인증 자료 <span style={{ color: 'var(--red)', fontWeight: 600 }}>*필수</span></h3>
        <p className="section-desc">근로계약서, 급여 입금 내역, 보험 내역, 출퇴근 교통 내역 등</p>
        <input type="file" multiple accept="image/*,.pdf"
          onChange={e => setProofFiles(Array.from(e.target.files))}
          className={styles.fileInput} />
        {proofFiles.length > 0 && (
          <div className={styles.fileList}>
            {proofFiles.map(f => <span key={f.name} className="tag info">📎 {f.name}</span>)}
          </div>
        )}

        {/* 주관식 후기 */}
        <h3 className="section-title">💬 주관식 후기 <span style={{ color: 'var(--text-sub)', fontWeight: 400 }}>(선택)</span></h3>
        <p className="section-desc">자유롭게 작성하면 AI가 법적 위험 표현을 안전하게 순화해드립니다.</p>
        <textarea rows={3} value={reviewText} onChange={e => setReviewText(e.target.value)}
          placeholder="근무 경험을 자유롭게 작성해주세요..." />

        <button className="btn-outline full-width" style={{ marginTop: 8 }}
          onClick={handlePurify} disabled={purifyLoading}>
          {purifyLoading ? '⏳ AI 분석 중...' : '✨ AI 후기 순화'}
        </button>

        {/* 순화 결과 */}
        {purifyResult && (
          <div className={styles.purifyResult}>
            <div className={styles.purifyHeader}>
              <span className={`risk-badge ${purifyResult.risk_assessment?.risk_level}`}>
                {purifyResult.risk_assessment?.risk_level}
              </span>
              <span className={styles.purifyIssues}>
                {purifyResult.risk_assessment?.detected_issues?.join(' · ')}
              </span>
            </div>
            <p className={styles.purifyHint}>아래 3가지 버전 중 하나를 선택해주세요:</p>
            {purifyResult.purified_options?.map(opt => (
              <div key={opt.option_id}
                className={`${styles.purifyOption} ${selectedOption === opt.text ? styles.selected : ''}`}
                onClick={() => setSelectedOption(opt.text)}>
                <div className={styles.optStyle}>{opt.style}</div>
                <div className={styles.optText}>{opt.text}</div>
              </div>
            ))}
          </div>
        )}

        <div style={{ marginTop: 24 }}>
          <button className="btn-primary full-width" style={{ padding: '12px', fontSize: 15 }}
            onClick={handleSubmit} disabled={loading}>
            {loading ? '제출 중...' : '후기 제출'}
          </button>
          <p style={{ fontSize: 12, color: 'var(--text-sub)', textAlign: 'center', marginTop: 8 }}>
            관리자 검수 후 지도에 반영됩니다.
          </p>
        </div>
      </div>
    </div>
  )
}
