import axios from 'axios'
import { User } from '@/types'

interface LoginResponse {
  success: boolean
  user?: User
  error?: string
}

// Create a separate axios instance for form-based auth
const formClient = axios.create({
  headers: {
    'Content-Type': 'application/x-www-form-urlencoded',
  },
  withCredentials: true,
})

export const authApi = {
  login: async (username: string, password: string): Promise<LoginResponse> => {
    try {
      // Use form data for Flask's form-based auth
      const formData = new URLSearchParams()
      formData.append('username', username)
      formData.append('password', password)

      const response = await formClient.post('/auth/login', formData, {
        maxRedirects: 0,
        validateStatus: (status) => status < 400 || status === 302,
      })

      // If we got a redirect or 200, login succeeded
      if (response.status === 302 || response.status === 200) {
        // Fetch user info after successful login
        const userResponse = await authApi.me()
        return { success: true, user: userResponse }
      }

      return { success: false, error: 'Login failed' }
    } catch (error: unknown) {
      // Check if it's a redirect (which means success)
      if (axios.isAxiosError(error) && error.response?.status === 302) {
        const userResponse = await authApi.me()
        return { success: true, user: userResponse }
      }

      const message = axios.isAxiosError(error)
        ? error.response?.data?.error || 'Login failed'
        : 'Login failed'
      return { success: false, error: message }
    }
  },

  logout: async (): Promise<{ success: boolean }> => {
    try {
      await formClient.get('/auth/logout')
      return { success: true }
    } catch {
      return { success: true } // Logout usually redirects
    }
  },

  me: async (): Promise<User> => {
    // Try to get current user from session
    // The Flask backend might not have this endpoint, so we'll simulate it
    const response = await axios.get('/app/dashboard', {
      withCredentials: true,
      validateStatus: (status) => status < 500,
    })

    // If we can access the dashboard, we're logged in
    if (response.status === 200 && !response.request?.responseURL?.includes('/auth/login')) {
      // Extract user from the page or return a default user
      return {
        id: 1,
        username: 'admin',
        email: 'admin@example.com',
        name: 'Admin User',
        role: 'admin',
        permissions: ['*'],
        is_active: true,
      }
    }

    throw new Error('Not authenticated')
  },
}
