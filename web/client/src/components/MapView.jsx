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

  const [popupBiz, setPopupBiz] = useState(null)
  const [popupPos, setPopupPos] = useState({ x: 0, y: 0, below: false })

  useEffect(() => { popupBizRef.current = popupBiz }, [popupBiz])

  /* ── 위경도 → 픽셀 변환 + 방향 결정 ───────────────────────── */
  const computePopupPos = useCallback(() => {
    if (!mapInstance.current || !popupLatLonRef.current) return
    const { lat, lon } = popupLatLonRef.current
    const proj  = mapInstance.current.getProjection()
    const point = proj.containerPointFromCoords(
      new window.kakao.maps.LatLng(lat, lon)
    )
    // 핀이 지도 상단 280px 이내면 팝업을 아래쪽으로 표시
    const below = point.y < 280
    setPopupPos({ x: point.x, y: point.y, below })
  }, [])

  function closePopup() {
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
      // 줌 변경 시 팝업 위치 즉시 재계산
      window.kakao.maps.event.addListener(mapInstance.current, 'zoom_changed', computePopupPos)
      // 드래그 종료 시 팝업 위치 재계산
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
          setPopupBiz(null)
          popupLatLonRef.current = null
          return
        }
        content.style.transform = 'scale(1.2)'
        setTimeout(() => { content.style.transform = 'scale(1)' }, 150)

        // 위경도 저장 후 픽셀 위치 계산
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
          className={popupPos.below ? styles.popupWrapBelow : styles.popupWrap}
          style={{ left: popupPos.x, top: popupPos.y }}
        >
          <MapPopup
            biz={popupBiz}
            onClose={closePopup}
            onViewDetail={(bizId) => navigate(`/business/${bizId}`)}
            below={popupPos.below}
          />
        </div>
      )}
    </div>
  )
}
