import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import api from '../services/api'

interface User {
  id: number
  username: string
  email: string
  role: 'store_manager' | 'regional_manager' | 'admin'
  store_id?: number
}

interface AuthState {
  user: User | null
  token: string | null
  isAuthenticated: boolean
  login: (username: string, password: string) => Promise<void>
  logout: () => void
  setUser: (user: User) => void
  setToken: (token: string) => void
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      token: null,
      isAuthenticated: false,
      login: async (username: string, password: string) => {
        try {
          const formData = new URLSearchParams()
          formData.append('username', username)
          formData.append('password', password)
          
          const response = await api.post('/api/v1/auth/login', formData, {
            headers: {
              'Content-Type': 'application/x-www-form-urlencoded',
            },
          })
          const { access_token } = response.data
          
          // Set token first so it's available for the next request
          set({ token: access_token, isAuthenticated: true })
          
          // Fetch user info
          const userResponse = await api.get('/api/v1/auth/me')
          set({ user: userResponse.data })
        } catch (error: any) {
          throw new Error(error.response?.data?.detail || 'Login failed')
        }
      },
      logout: () => {
        set({
          user: null,
          token: null,
          isAuthenticated: false,
        })
      },
      setUser: (user: User) => set({ user }),
      setToken: (token: string) => set({ token, isAuthenticated: !!token }),
    }),
    {
      name: 'auth-storage',
    }
  )
)

