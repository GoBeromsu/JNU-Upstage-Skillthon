import { useEffect, useRef, useState } from 'react'
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

  const mapRef        = useRef(null)
  const mapInstance   = useRef(null)
  const overlaysRef   = useRef([])
  const contentMapRef = useRef({})   // businessId → content div (highlight용)
  const popupBizRef   = useRef(null) // stale-closure 방지

  const [popupBiz, setPopupBiz] = useState(null)
  const [popupPos, setPopupPos] = useState({ x: 0, y: 0 })

  useEffect(() => { popupBizRef.current = popupBiz }, [popupBiz])

  function closePopup() { setPopupBiz(null) }

  /* ── 카카오맵 초기화 ─────────────────────────────────────── */
  useEffect(() => {
    function initMap() {
      if (!mapRef.current || mapInstance.current) return
      mapInstance.current = new window.kakao.maps.Map(mapRef.current, {
        center: new window.kakao.maps.LatLng(35.1767, 126.9095),
        level: 4,
      })

      // MapContext에 panTo 등록
      registerPanTo((lat, lon) => {
        mapInstance.current?.panTo(new window.kakao.maps.LatLng(lat, lon))
      })

      // MapContext에 highlight 등록
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

      // 지도 클릭 시 팝업 닫기
      window.kakao.maps.event.addListener(mapInstance.current, 'click', closePopup)
    }

    if (window.kakao) {
      window.kakao.maps.load(initMap)
    } else {
      const timer = setInterval(() => {
        if (window.kakao) { clearInterval(timer); window.kakao.maps.load(initMap) }
      }, 50)
      setTimeout(() => clearInterval(timer), 10000)
    }
  }, []) // eslint-disable-line

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
        const rect          = content.getBoundingClientRect()
        const containerRect = mapRef.current.getBoundingClientRect()
        const x = rect.left - containerRect.left + rect.width / 2
        const y = rect.top  - containerRect.top

        if (popupBizRef.current?.businessId === biz.businessId) {
          setPopupBiz(null); return
        }
        content.style.transform = 'scale(1.2)'
        setTimeout(() => { content.style.transform = 'scale(1)' }, 150)
        setPopupPos({ x, y })
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
  }, [businesses]) // eslint-disable-line

  /* ── 후기 쓰기 FAB (진입점 A) ───────────────────────────── */
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

      {/* 후기 쓰기 FAB — 지도 좌측 상단 */}
      <button className={styles.writeBtn} onClick={handleWriteReview}>
        ✏️ 후기 쓰기
      </button>

      {/* 팝업 — React 트리 직접 렌더링 */}
      {popupBiz && (
        <div className={styles.popupWrap} style={{ left: popupPos.x, top: popupPos.y }}>
          <MapPopup
            biz={popupBiz}
            onClose={closePopup}
            onViewDetail={(bizId) => navigate(`/business/${bizId}`)}
          />
        </div>
      )}
    </div>
  )
}
