import React, { createContext, useContext, useState, useEffect, useCallback } from 'react'
import { authAPI } from '../services/api'

const AuthContext = createContext(null)

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(() => {
    try {
      const stored = localStorage.getItem('brightloop_user')
      return stored ? JSON.parse(stored) : null
    } catch {
      return null
    }
  })
  const [token, setToken] = useState(() => localStorage.getItem('brightloop_token') || null)
  const [isLoading, setIsLoading] = useState(true)

  // Verify and sync profile on app load if token exists
  useEffect(() => {
    const initAuth = async () => {
      const savedToken = localStorage.getItem('brightloop_token')
      if (savedToken) {
        try {
          const res = await authAPI.getMe()
          const userData = res.user || res.data || res
          setUser(userData)
          localStorage.setItem('brightloop_user', JSON.stringify(userData))
        } catch (err) {
          // If token expired/invalid, clear session
          console.warn('Session verification failed, logging out:', err.message)
          localStorage.removeItem('brightloop_token')
          localStorage.removeItem('brightloop_user')
          setToken(null)
          setUser(null)
        }
      }
      setIsLoading(false)
    }

    initAuth()
  }, [])

  const login = useCallback(async (email, password) => {
    setIsLoading(true)
    try {
      const res = await authAPI.login({ email, password })
      // Expected response structure: { token, user } or { data: { token, user } }
      const authToken = res.token || res.data?.token
      const authUser = res.user || res.data?.user || res.data

      if (!authToken) {
        throw new Error('Authentication succeeded but no token was received.')
      }

      setToken(authToken)
      setUser(authUser)
      localStorage.setItem('brightloop_token', authToken)
      localStorage.setItem('brightloop_user', JSON.stringify(authUser))

      return authUser
    } finally {
      setIsLoading(false)
    }
  }, [])

  const register = useCallback(async (userData) => {
    setIsLoading(true)
    try {
      const res = await authAPI.register(userData)
      const authToken = res.token || res.data?.token
      const authUser = res.user || res.data?.user || res.data

      if (authToken) {
        setToken(authToken)
        setUser(authUser)
        localStorage.setItem('brightloop_token', authToken)
        localStorage.setItem('brightloop_user', JSON.stringify(authUser))
      }

      return authUser || res
    } finally {
      setIsLoading(false)
    }
  }, [])

  const logout = useCallback(async () => {
    try {
      await authAPI.logout()
    } catch {
      // Ignore network errors on logout
    } finally {
      setToken(null)
      setUser(null)
      localStorage.removeItem('brightloop_token')
      localStorage.removeItem('brightloop_user')
    }
  }, [])

  const updateUser = useCallback((updatedUserData) => {
    setUser((prev) => {
      const merged = { ...prev, ...updatedUserData }
      localStorage.setItem('brightloop_user', JSON.stringify(merged))
      return merged
    })
  }, [])

  const value = {
    user,
    token,
    isLoading,
    isAuthenticated: Boolean(token && user),
    login,
    register,
    logout,
    updateUser,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export const useAuth = () => {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

export default AuthContext
