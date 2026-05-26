import { useEffect, useRef, useState, useCallback } from 'react'
import { useNavigate } from 'react-router-dom'
import { COLOR_MAP } from '../utils/constants'
import { useAuth }   from '../contexts/AuthContext'
import { useMapCtx } from '../contexts/MapContext'
import MapPopup from './MapPopup'
import styles from './MapView.module.css'

export default function MapView({ businesses, onSelectBiz }) {
  const navigate  = useNavigate()
  const { requireLogin } = useAuth()
  const { registerPanTo, registerHighlight } = useMapCtx()

  const mapRef         = useRef(null)
  const mapInstance    = useRef(null)
  const overlaysRef    = useRef([])
  const contentMapRef  = useRef({})
  const popupBizRef    = useRef(null)
  const popupLatLonRef = useRef(null)   // { lat, lon } — 줌/이동 시 재계산용
  const popupWrapRef   = useRef(null)   // 팝업 DOM — 실제 높이 측정용
  const activePinRef   = useRef(null)   // 현재 열린 팝업의 핀 DOM — z-index 관리용

  const [popupBiz, setPopupBiz] = useState(null)
  const [popupPos, setPopupPos] = useState({ x: 0, y: 0, below: false, arrowOffset: 0 })

  useEffect(() => { popupBizRef.current = popupBiz }, [popupBiz])

  /* ── 위경도 → 픽셀 변환 + 방향/클램핑 결정 ─────────────────── */
  // ※ useEffect 의존성 배열에 사용되므로 반드시 useEffect보다 먼저 선언
  const computePopupPos = useCallback(() => {
    if (!mapInstance.current || !popupLatLonRef.current) return
    const { lat, lon } = popupLatLonRef.current
    const proj  = mapInstance.current.getProjection()
    const point = proj.containerPointFromCoords(
      new window.kakao.maps.LatLng(lat, lon)
    )

    const containerW = mapRef.current?.offsetWidth  ?? 800
    const containerH = mapRef.current?.offsetHeight ?? 600
    const POPUP_W    = 440
    const MARGIN     = 10
    const halfW      = POPUP_W / 2 + MARGIN

    // 팝업 실제 높이 or 보수적 기본값
    const popupH = popupWrapRef.current?.offsetHeight ?? 600

    // ① 상하 방향 결정
    const below = point.y < popupH + 30

    // ② x 클램핑 — 팝업이 좌/우로 벗어나지 않도록
    const clampedX    = Math.max(halfW, Math.min(point.x, containerW - halfW))
    const arrowOffset = point.x - clampedX   // 화살표를 실제 핀 위치로 보정

    // ③ y 클램핑 — 팝업 아래 방향일 때 하단 초과 방지
    const maxY     = below ? containerH - popupH - 30 : containerH
    const clampedY = Math.min(point.y, maxY)

    setPopupPos({ x: clampedX, y: clampedY, below, arrowOffset })
  }, [])

  // 팝업 렌더 후 실측 높이로 재보정
  useEffect(() => {
    if (!popupWrapRef.current || !popupBiz) return
    computePopupPos()
  }, [popupBiz, computePopupPos]) // eslint-disable-line

  function closePopup() {
    // 이전 활성 핀 z-index 복원
    if (activePinRef.current) {
      activePinRef.current.style.zIndex = ''
      activePinRef.current = null
    }
    setPopupBiz(null)
    popupLatLonRef.current = null
  }

  /* ── 카카오맵 초기화 ─────────────────────────────────────── */
  useEffect(() => {
    function initMap() {
      if (!mapRef.current || mapInstance.current) return
      mapInstance.current = new window.kakao.maps.Map(mapRef.current, {
        center: new window.kakao.maps.LatLng(35.1767, 126.9095),
        level: 4,
      })

      registerPanTo((lat, lon) => {
        mapInstance.current?.panTo(new window.kakao.maps.LatLng(lat, lon))
      })

      registerHighlight((bizId) => {
        Object.values(contentMapRef.current).forEach(el => {
          el.style.transform = 'scale(1)'
          el.style.zIndex    = '1'
          el.style.boxShadow = '0 2px 10px rgba(0,0,0,0.25)'
        })
        const el = contentMapRef.current[bizId]
        if (el) {
          el.style.transform = 'scale(1.3)'
          el.style.zIndex    = '5'
          el.style.boxShadow = '0 4px 18px rgba(0,0,0,0.40)'
          setTimeout(() => { el.style.transform = 'scale(1.1)' }, 250)
        }
      })

      window.kakao.maps.event.addListener(mapInstance.current, 'click', closePopup)
      window.kakao.maps.event.addListener(mapInstance.current, 'zoom_changed', computePopupPos)
      window.kakao.maps.event.addListener(mapInstance.current, 'dragend', computePopupPos)
    }

    if (window.kakao) {
      window.kakao.maps.load(initMap)
    } else {
      const timer = setInterval(() => {
        if (window.kakao) { clearInterval(timer); window.kakao.maps.load(initMap) }
      }, 50)
      setTimeout(() => clearInterval(timer), 10000)
    }
  }, [computePopupPos]) // eslint-disable-line

  /* ── 마커 렌더링 ─────────────────────────────────────────── */
  useEffect(() => {
    if (!mapInstance.current || !businesses.length) return

    overlaysRef.current.forEach(o => o.setMap(null))
    overlaysRef.current   = []
    contentMapRef.current = {}

    businesses.forEach(biz => {
      const hex       = COLOR_MAP[biz.color] || '#3b82f6'
      const textColor = biz.color === 'yellow' ? '#1e293b' : '#fff'

      const content = document.createElement('div')
      content.style.cssText = `
        background:${hex}; border:3px solid #fff; border-radius:50%;
        width:40px; height:40px;
        display:flex; align-items:center; justify-content:center;
        box-shadow:0 2px 10px rgba(0,0,0,0.25); cursor:pointer;
        font-size:11px; font-weight:800; color:${textColor};
        transition:transform .15s; user-select:none;
      `
      content.textContent = biz.cleanScore
      contentMapRef.current[biz.businessId] = content

      content.addEventListener('click', (e) => {
        e.stopPropagation()
        if (popupBizRef.current?.businessId === biz.businessId) {
          closePopup()
          return
        }
        // 이전 핀 z-index 복원
        if (activePinRef.current) activePinRef.current.style.zIndex = ''
        // 클릭된 핀을 팝업(z:20)보다 위로
        content.style.zIndex = '30'
        activePinRef.current = content

        content.style.transform = 'scale(1.2)'
        setTimeout(() => { content.style.transform = 'scale(1)' }, 150)

        popupLatLonRef.current = { lat: biz.lat, lon: biz.lon }
        computePopupPos()
        setPopupBiz(biz)
        onSelectBiz?.(biz)
      })
      content.addEventListener('mouseenter', () => { content.style.transform = 'scale(1.1)' })
      content.addEventListener('mouseleave', () => { content.style.transform = 'scale(1)' })

      const overlay = new window.kakao.maps.CustomOverlay({
        position: new window.kakao.maps.LatLng(biz.lat, biz.lon),
        content, yAnchor: 0.5, xAnchor: 0.5, zIndex: 1,
      })
      overlay.setMap(mapInstance.current)
      overlaysRef.current.push(overlay)
    })
  }, [businesses, computePopupPos]) // eslint-disable-line

  /* ── 후기 쓰기 FAB ───────────────────────────────────────── */
  function handleWriteReview() {
    if (!requireLogin('/write')) return
    navigate('/write')
  }

  return (
    <div className={styles.container}>
      <div ref={mapRef} className={styles.map} />

      {/* 범례 */}
      <div className={styles.legend}>
        {[
          { color: 'green',  label: '80+ 우수' },
          { color: 'yellow', label: '60+ 보통' },
          { color: 'orange', label: '40+ 주의' },
          { color: 'red',    label: '40미만 위험' },
        ].map(({ color, label }) => (
          <div key={color} className={styles.legendItem}>
            <span className={styles.dot} style={{ background: COLOR_MAP[color] }} />
            {label}
          </div>
        ))}
      </div>

      {/* 후기 쓰기 FAB */}
      <button className={styles.writeBtn} onClick={handleWriteReview}>
        ✏️ 후기 쓰기
      </button>

      {/* 팝업 — 방향에 따라 위/아래 클래스 분기 */}
      {popupBiz && (
        <div
          ref={popupWrapRef}
          className={popupPos.below ? styles.popupWrapBelow : styles.popupWrap}
          style={{ left: popupPos.x, top: popupPos.y }}
        >
          <MapPopup
            biz={popupBiz}
            onClose={closePopup}
            onViewDetail={(bizId) => navigate(`/business/${bizId}`)}
            below={popupPos.below}
            arrowOffset={popupPos.arrowOffset ?? 0}
          />
        </div>
      )}
    </div>
  )
}
