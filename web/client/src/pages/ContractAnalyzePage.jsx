import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import styles from './ContractAnalyzePage.module.css'

export default function ContractAnalyzePage() {
  const navigate = useNavigate()
  const { requireLogin } = useAuth()

  useEffect(() => {
    if (!requireLogin('/contract')) navigate('/')
  }, []) // eslint-disable-line

  const [file,    setFile]    = useState(null)
  const [imgUrl,  setImgUrl]  = useState(null)
  const [result,  setResult]  = useState(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState(null)

  const isImage = file?.type?.startsWith('image/')

  /* 이미지 미리보기 URL */
  useEffect(() => {
    if (!file || !isImage) { setImgUrl(null); return }
    const url = URL.createObjectURL(file)
    setImgUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file, isImage])

  /* 분석 실행 */
  async function handleAnalyze() {
    if (!file) return
    setLoading(true)
    setError(null)
    setResult(null)
    try {
      const fd = new FormData()
      fd.append('file', file)
      const res  = await fetch('/api/skills/analyze-contract', { method: 'POST', body: fd })
      const data = await res.json()
      if (data.error) throw new Error(data.error)
      setResult(data)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  function handleReset() {
    setFile(null)
    setResult(null)
    setError(null)
  }

  const RISK_LABEL = { SAFE: '✅ 안전', LOW: '⚠️ 주의', MEDIUM: '🟠 위험', HIGH: '🔴 심각' }
  const RISK_DESC  = {
    SAFE:   '위반 항목이 없습니다.',
    LOW:    '경미한 위반 1건이 감지되었습니다.',
    MEDIUM: '위반 항목 2개 이상이 감지되었습니다.',
    HIGH:   '심각한 위반이 감지되었습니다.',
  }

  return (
    <div className={styles.page}>
      {/* 상단 바 */}
      <div className={styles.topBar}>
        <button className={styles.backBtn} onClick={() => navigate('/')}>← 메인으로</button>
        <span className={styles.topTitle}>📄 근로계약서 분석</span>
      </div>

      <div className={styles.body}>

        {/* ── 왼쪽: 업로드 / 결과 ── */}
        <div className={styles.left}>

          {/* 업로드 영역 (결과 전에만 표시) */}
          {!result && (
            <>
              <div
                className={`${styles.uploadZone} ${file ? styles.hasFile : ''}`}
                onClick={() => document.getElementById('cFile').click()}
              >
                <div className={styles.uploadIcon}>{file ? '✅' : '📁'}</div>
                {file ? (
                  <>
                    <div style={{ fontWeight: 600 }}>{file.name}</div>
                    <div className={styles.uploadHint}>{(file.size / 1024).toFixed(1)} KB</div>
                  </>
                ) : (
                  <>
                    <div>클릭하거나 파일을 드래그 앤 드롭</div>
                    <div className={styles.uploadHint}>PDF, JPEG, PNG, HWP 지원</div>
                  </>
                )}
              </div>
              <input
                id="cFile" type="file"
                accept=".pdf,.jpg,.jpeg,.png,.bmp,.tiff,.heic,.docx,.hwp,.hwpx"
                style={{ display: 'none' }}
                onChange={e => { setFile(e.target.files[0]); setError(null) }}
              />

              {error && <div className={styles.errorBox}>❌ {error}</div>}

              <button
                className="btn-primary full-width"
                style={{ padding: '13px', fontSize: 15, marginTop: 8 }}
                onClick={handleAnalyze}
                disabled={!file || loading}
              >
                {loading ? '⏳ AI 분석 중...' : '분석 시작'}
              </button>
            </>
          )}

          {/* 결과 (분석 완료 후) */}
          {result && (
            <>
              <div className={`${styles.riskBanner} ${styles[result.risk_level]}`}>
                {RISK_LABEL[result.risk_level]} — {RISK_DESC[result.risk_level]}
              </div>

              <div className={styles.infoGrid}>
                {[
                  ['사업장',       result.extracted_info?.business_name],
                  ['시급',         result.extracted_info?.hourly_wage
                                    ? `${result.extracted_info.hourly_wage.toLocaleString()}원` : '-'],
                  ['일일 근무시간', result.extracted_info?.daily_work_hours
                                    ? `${result.extracted_info.daily_work_hours}시간` : '-'],
                  ['휴게시간',      result.extracted_info?.break_time_minutes
                                    ? `${result.extracted_info.break_time_minutes}분` : '-'],
                  ['급여일',        result.extracted_info?.pay_date || '-'],
                  ['주휴수당 명시', result.extracted_info?.weekly_holiday_pay_mentioned ? '✅ 있음' : '❌ 없음'],
                ].map(([label, val]) => (
                  <div key={label} className={styles.infoItem}>
                    <div className={styles.infoLabel}>{label}</div>
                    <div className={styles.infoValue}>{val || '-'}</div>
                  </div>
                ))}
              </div>

              <h4 className={styles.subTitle}>법적 준수 여부</h4>
              <div className={styles.complianceGrid}>
                {Object.entries(result.compliance_check || {}).map(([k, v]) => (
                  <div key={k} className={styles.compItem}>
                    {v === true ? '✅' : v === false ? '❌' : '❓'}
                    <span>{k.replace(/_/g, ' ')}</span>
                  </div>
                ))}
              </div>

              {result.confirmed_violations?.length > 0 && (
                <>
                  <h4 className={styles.subTitleWarn}>확인된 위반사항</h4>
                  <ul className={styles.list}>
                    {result.confirmed_violations.map((v, i) => <li key={i}>{v}</li>)}
                  </ul>
                </>
              )}
              {result.needs_verification?.length > 0 && (
                <>
                  <h4 className={styles.subTitleInfo}>실제 근무 후 확인 필요</h4>
                  <ul className={styles.list}>
                    {result.needs_verification.map((v, i) => <li key={i}>{v}</li>)}
                  </ul>
                </>
              )}

              <button
                className="btn-outline full-width"
                style={{ marginTop: 20, padding: '10px' }}
                onClick={handleReset}
              >
                🔄 다른 계약서 분석하기
              </button>
            </>
          )}
        </div>

        {/* ── 오른쪽: 이미지 미리보기 ── */}
        <div className={styles.right}>
          {imgUrl && isImage ? (
            <div className={styles.imageWrap}>
              <img
                src={imgUrl}
                alt="계약서 미리보기"
                className={styles.contractImg}
              />
            </div>
          ) : (
            <div className={styles.noPreview}>
              {file && !isImage
                ? '📄 이미지 파일(JPG·PNG)만 미리보기를 지원합니다.\nPDF 결과는 왼쪽에서 확인하세요.'
                : '계약서 이미지를 업로드하면\n여기에 미리보기가 표시됩니다.'}
            </div>
          )}
        </div>

      </div>
    </div>
  )
}
