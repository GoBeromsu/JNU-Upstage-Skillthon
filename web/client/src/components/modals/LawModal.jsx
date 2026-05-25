import styles from './LawModal.module.css'

const LAW_ITEMS = [
  { icon: '💰', title: '최저시급', desc: '2026년 기준 시간당 10,030원 이상. 수습기간이라도 1년 미만 계약이면 삭감 불가.' },
  { icon: '📝', title: '근로계약서', desc: '반드시 서면으로 작성·교부. 미교부 시 500만원 이하 벌금.' },
  { icon: '☕', title: '휴게시간', desc: '4시간 근무 시 30분 이상, 8시간 근무 시 1시간 이상 보장 의무.' },
  { icon: '🏖️', title: '주휴수당', desc: '주 15시간 이상 개근 시 하루치 임금 추가 지급. 주 5일 기준 시급×8시간.' },
  { icon: '⏰', title: '초과근무 수당', desc: '1일 8시간, 주 40시간 초과 시 통상임금의 50% 가산 지급.' },
  { icon: '📅', title: '임금 지급', desc: '매월 1회 이상 정해진 날 지급. 지연 시 연 20% 지연이자 청구 가능.' },
]

export default function LawModal({ onClose }) {
  return (
    <div className="modal-overlay" onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="modal large">
        <button className="modal-close" onClick={onClose}>✕</button>
        <h2 className="modal-title">⚖️ 알바생을 위한 근로기준법 핵심 안내</h2>
        <p className="modal-subtitle">알아두면 내 권리를 지킬 수 있어요.</p>
        <div className={styles.grid}>
          {LAW_ITEMS.map(item => (
            <div key={item.title} className={styles.card}>
              <div className={styles.icon}>{item.icon}</div>
              <h4 className={styles.title}>{item.title}</h4>
              <p className={styles.desc}>{item.desc}</p>
            </div>
          ))}
        </div>
        <div className={styles.footer}>
          <a href="https://www.moel.go.kr" target="_blank" rel="noreferrer" className="btn-outline">
            고용노동부 바로가기
          </a>
          <a href="tel:1350" className="btn-outline">📞 노동부 상담 1350</a>
        </div>
      </div>
    </div>
  )
}
