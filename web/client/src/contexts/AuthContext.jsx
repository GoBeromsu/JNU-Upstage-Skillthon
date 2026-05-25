import { createContext, useContext, useState, useEffect, useCallback } from 'react'

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [user,           setUser]           = useState(null)
  const [isLoggedIn,     setIsLoggedIn]     = useState(false)
  const [showLoginModal, setShowLoginModal] = useState(false)

  // 세션 복원
  useEffect(() => {
    try {
      const saved = localStorage.getItem('alba_user')
      if (saved) {
        const u = JSON.parse(saved)
        setUser(u)
        setIsLoggedIn(true)
      }
    } catch {}
  }, [])

  function login(userData) {
    setUser(userData)
    setIsLoggedIn(true)
    localStorage.setItem('alba_user', JSON.stringify(userData))
  }

  function logout() {
    setUser(null)
    setIsLoggedIn(false)
    localStorage.removeItem('alba_user')
  }

  /** 로그인이 필요한 액션 전에 호출. 비로그인이면 모달 띄우고 false 반환 */
  function requireLogin(returnTo = '/') {
    if (isLoggedIn) return true
    sessionStorage.setItem('loginReturnTo', returnTo)
    setShowLoginModal(true)
    return false
  }

  /** 카카오 로그인 페이지로 이동 */
  async function redirectToKakao() {
    try {
      const res = await fetch('/api/auth/kakao-url')
      const data = await res.json()
      if (data.url) {
        window.location.href = data.url
      } else {
        console.error('카카오 URL 없음:', data)
      }
    } catch (e) {
      console.error('카카오 URL 요청 실패:', e)
    }
  }

  /** 관리자 API 헤더 */
  const adminHeaders = useCallback(() => ({
    'Content-Type':   'application/json',
    'x-user-id':      user?.id         || '',
    'x-admin-token':  user?.adminToken  || '',
  }), [user?.id, user?.adminToken])

  const isAdmin = !!(user?.isAdmin && user?.adminToken)

  return (
    <AuthContext.Provider value={{
      user, isLoggedIn, isAdmin,
      login, logout,
      requireLogin,
      showLoginModal, setShowLoginModal,
      redirectToKakao,
      adminHeaders,
    }}>
      {children}
    </AuthContext.Provider>
  )
}

export const useAuth = () => useContext(AuthContext)
