import { useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'

export default function KakaoCallback() {
  const [params]  = useSearchParams()
  const navigate  = useNavigate()
  const { login } = useAuth()
  const [error, setError] = useState(null)
  const called = useRef(false)   // React StrictMode 이중 실행 방지

  useEffect(() => {
    if (called.current) return   // 두 번째 호출 무시
    called.current = true

    const code  = params.get('code')
    const kakaoError = params.get('error')

    if (kakaoError) {
      setError(`카카오 오류: ${params.get('error_description') || kakaoError}`)
      return
    }
    if (!code) {
      navigate('/', { replace: true })
      return
    }

    fetch('/api/auth/kakao', {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ code }),
    })
      .then(r => r.json())
      .then(data => {
        if (data.error) throw new Error(data.error)
        login(data.user)
        const returnTo = sessionStorage.getItem('loginReturnTo') || '/'
        sessionStorage.removeItem('loginReturnTo')
        navigate(returnTo, { replace: true })
      })
      .catch(e => {
        console.error('로그인 실패:', e)
        setError(e.message)
      })
  }, []) // eslint-disable-line

  if (error) {
    return (
      <div style={{
        display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center',
        height: '100vh', gap: 16, padding: 24,
      }}>
        <p style={{ fontSize: 18, fontWeight: 700, color: '#ef4444' }}>로그인 실패</p>
        <p style={{ fontSize: 14, color: '#64748b', textAlign: 'center' }}>{error}</p>
        <button
          className="btn-primary"
          onClick={() => navigate('/', { replace: true })}
        >메인으로 돌아가기</button>
      </div>
    )
  }

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      alignItems: 'center', justifyContent: 'center',
      height: '100vh', gap: 16, color: '#64748b',
    }}>
      <div className="loading-spinner"
        style={{ borderTopColor: '#FEE500', borderColor: '#e2e8f0', width: 40, height: 40 }}
      />
      <p style={{ fontSize: 16, fontWeight: 600 }}>카카오 로그인 중...</p>
    </div>
  )
}
