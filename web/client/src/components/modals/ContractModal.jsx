import { useState, useRef, useEffect, useCallback } from 'react'
import styles from './ContractModal.module.css'

export default function ContractModal({ onClose }) {
  const [file,    setFile]    = useState(null)
  const [imgUrl,  setImgUrl]  = useState(null)
  const [result,  setResult]  = useState(null)
  const [loading, setLoading] = useState(false)
  const [error,   setError]   = useState(null)

  const imgRef    = useRef(null)
  const canvasRef = useRef(null)

  /* 파일 선택 시 미리보기 URL 생성 */
  useEffect(() => {
    if (!file) { setImgUrl(null); return }
    const url = URL.createObjectURL(file)
    setImgUrl(url)
    return () => URL.revokeObjectURL(url)
  }, [file])

  /* 위반 좌표 → Canvas 드로잉 */
  const drawOverlay = useCallback(() => {
    const img    = imgRef.current
    const canvas = canvasRef.current
    if (!img || !canvas || !result?.violation_regions?.length) return

    const pageInfo = result.pages?.[0] || { width: img.naturalWidth, height: img.naturalHeight }
    const scaleX   = img.clientWidth  / (pageInfo.width  || img.naturalWidth)
    const scaleY   = img.clientHeight / (pageInfo.height || img.naturalHeight)

    canvas.width  = img.clientWidth
    canvas.height = img.clientHeight

    const ctx = canvas.getContext('2d')
    ctx.clearRect(0, 0, canvas.width, canvas.height)

    result.violation_regions.forEach(region => {
      const coords = region.coordinates
      if (!coords?.length) return

      const hex   = region.color
      const r = parseInt(hex.slice(1, 3), 16)
      const g = parseInt(hex.slice(3, 5), 16)
      const b = parseInt(hex.slice(5, 7), 16)

      /* 반투명 채우기 */
      ctx.fillStyle   = `rgba(${r},${g},${b},0.25)`
      ctx.strokeStyle = `rgba(${r},${g},${b},0.9)`
      ctx.lineWidth   = 2

      ctx.beginPath()
      coords.forEach(({ x, y }, i) => {
        i === 0
          ? ctx.moveTo(x * scaleX, y * scaleY)
          : ctx.lineTo(x * scaleX, y * scaleY)
      })
      ctx.closePath()
      ctx.fill()
      ctx.stroke()

      /* 라벨 */
      const xs   = coords.map(c => c.x * scaleX)
      const ys   = coords.map(c => c.y * scaleY)
      const minX = Math.min(...xs)
      const minY = Math.min(...ys)

      const label = region.label
      ctx.font         = 'bold 11px sans-serif'
      const tw         = ctx.measureText(label).width
      ctx.fillStyle    = `rgba(${r},${g},${b},0.9)`
      ctx.fillRect(minX, minY - 16, tw + 8, 16)
      ctx.fillStyle    = '#fff'
      ctx.fillText(label, minX + 4, minY - 4)
    })
  }, [result])

  useEffect(() => {
    if (!result?.violation_regions?.length || !imgUrl) return
    const img = imgRef.current
    if (!img) return
    if (img.complete) drawOverlay()
    else img.onload = drawOverlay
  }, [result, imgUrl, drawOverlay])

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

  const RISK_LABEL = { SAFE: '✅ 안전', LOW: '⚠️ 주의', MEDIUM: '🟠 위험', HIGH: '🔴 심각' }
  const RISK_DESC  = {
    SAFE:   '위반 항목이 없습니다.',
    LOW:    '경미한 위반 1건이 감지되었습니다.',
    MEDIUM: '위반 항목 2개 이상이 감지되었습니다.',
    HIGH:   '심각한 위반이 감지되었습니다.',
  }

  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal large">
        <button className="modal-close" onClick={onClose}>✕</button>
        <h2 className="modal-title">📄 근로계약서 분석</h2>
        <p className="modal-subtitle">계약서 이미지 또는 PDF를 업로드하면 AI가 핵심 항목을 분석합니다.</p>

        {/* 업로드 영역 */}
        <div
          className={`${styles.uploadZone} ${file ? styles.hasFile : ''}`}
          onClick={() => document.getElementById('contractFile').click()}
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
          id="contractFile" type="file"
          accept=".pdf,.jpg,.jpeg,.png,.bmp,.tiff,.heic,.docx,.hwp,.hwpx"
          style={{ display: 'none' }}
          onChange={e => { setFile(e.target.files[0]); setResult(null); setError(null) }}
        />

        {/* 이미지 미리보기 + Canvas 오버레이 */}
        {imgUrl && (
          <div className={styles.imageWrap}>
            <img
              ref={imgRef}
              src={imgUrl}
              alt="계약서 미리보기"
              className={styles.contractImg}
              onLoad={drawOverlay}
            />
            <canvas ref={canvasRef} className={styles.overlay} />
            {result?.violation_regions?.length > 0 && (
              <div className={styles.legendBox}>
                {[...new Map(result.violation_regions.map(r => [r.label, r])).values()].map(r => (
                  <span key={r.label} className={styles.legendItem}>
                    <span className={styles.legendDot} style={{ background: r.color }} />
                    {r.label}
                  </span>
                ))}
              </div>
            )}
          </div>
        )}

        {/* 오류 */}
        {error && (
          <div style={{ background:'#fee2e2', color:'#991b1b', borderRadius:10, padding:'10px 14px', marginBottom:12, fontSize:13 }}>
            ❌ {error}
          </div>
        )}

        {/* 분석 결과 */}
        {result && (
          <div className={styles.result}>
            <div className={`${styles.riskBanner} ${styles[result.risk_level]}`}>
              {RISK_LABEL[result.risk_level]} — {RISK_DESC[result.risk_level]}
            </div>

            <div className={styles.infoGrid}>
              {[
                ['사업장',      result.extracted_info?.business_name],
                ['시급',        result.extracted_info?.hourly_wage ? `${result.extracted_info.hourly_wage.toLocaleString()}원` : '-'],
                ['일일 근무시간', result.extracted_info?.daily_work_hours ? `${result.extracted_info.daily_work_hours}시간` : '-'],
                ['휴게시간',     result.extracted_info?.break_time_minutes ? `${result.extracted_info.break_time_minutes}분` : '-'],
                ['급여일',       result.extracted_info?.pay_date || '-'],
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
          </div>
        )}

        <button
          className="btn-primary full-width"
          style={{ marginTop: 16, padding: 12, fontSize: 15 }}
          onClick={handleAnalyze}
          disabled={!file || loading}
        >
          {loading ? '⏳ AI 분석 중...' : '분석 시작'}
        </button>
      </div>
    </div>
  )
}
