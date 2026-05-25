import styles from './AlertModal.module.css'

/**
 * alert() 대체용 커스텀 모달
 * props: open, icon, title, message, onClose
 */
export default function AlertModal({ open, icon = '✅', title, message, onClose }) {
  if (!open) return null

  return (
    <div className={styles.overlay} onClick={onClose}>
      <div className={styles.modal} onClick={e => e.stopPropagation()}>
        {icon && <div className={styles.icon}>{icon}</div>}
        {title   && <h2 className={styles.title}>{title}</h2>}
        {message && (
          <p className={styles.message}>
            {String(message).split('\n').map((line, i) => (
              <span key={i}>{line}<br /></span>
            ))}
          </p>
        )}
        <button className={styles.confirmBtn} onClick={onClose}>확인</button>
      </div>
    </div>
  )
}
