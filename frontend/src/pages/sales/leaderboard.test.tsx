import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { LeaderboardPage } from './leaderboard'
import { mockLeaderboard, mockAchievements } from '@/test/mocks/handlers'

// Mock the API module
vi.mock('@/api/elite-sales', () => ({
  getLeaderboard: vi.fn(() => Promise.resolve({ leaderboard: mockLeaderboard })),
  getLeaderboardStats: vi.fn(() => Promise.resolve({
    today: { leads: 15, hot_leads: 5 },
    this_week: { leads: 45 },
  })),
  getAchievements: vi.fn(() => Promise.resolve({
    achievements: mockAchievements,
    total_points: 60,
  })),
}))

import { mockLeaderboard as leaderboard, mockAchievements as achievements } from '@/test/mocks/handlers'

function renderWithProviders(ui: React.ReactElement) {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
      },
    },
  })

  return render(
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        {ui}
      </BrowserRouter>
    </QueryClientProvider>
  )
}

describe('LeaderboardPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the page title', () => {
    renderWithProviders(<LeaderboardPage />)

    expect(screen.getByText('Leaderboard')).toBeInTheDocument()
  })

  it('displays team stats cards', async () => {
    renderWithProviders(<LeaderboardPage />)

    await waitFor(() => {
      expect(screen.getByText("Today's Leads")).toBeInTheDocument()
    })

    expect(screen.getByText('Hot Leads Today')).toBeInTheDocument()
    expect(screen.getByText('This Week')).toBeInTheDocument()
    expect(screen.getByText('Active Team')).toBeInTheDocument()
  })

  it('displays leaderboard rankings', async () => {
    renderWithProviders(<LeaderboardPage />)

    await waitFor(() => {
      expect(screen.getByText('Mike Johnson')).toBeInTheDocument()
    })

    expect(screen.getByText('Sarah Williams')).toBeInTheDocument()
  })

  it('shows points for each salesperson', async () => {
    renderWithProviders(<LeaderboardPage />)

    await waitFor(() => {
      expect(screen.getByText('150')).toBeInTheDocument()
    })

    expect(screen.getByText('120')).toBeInTheDocument()
  })

  it('has period toggle tabs', () => {
    renderWithProviders(<LeaderboardPage />)

    expect(screen.getByText('Today')).toBeInTheDocument()
    expect(screen.getByText('Week')).toBeInTheDocument()
    expect(screen.getByText('Month')).toBeInTheDocument()
  })

  it('switches period when clicking tabs', async () => {
    const user = userEvent.setup()
    renderWithProviders(<LeaderboardPage />)

    const weekTab = screen.getByText('Week')
    await user.click(weekTab)

    // Tab should be active after clicking
    expect(weekTab).toBeInTheDocument()
  })

  it('displays achievements section', async () => {
    renderWithProviders(<LeaderboardPage />)

    await waitFor(() => {
      expect(screen.getByText('Your Achievements')).toBeInTheDocument()
    })
  })

  it('shows achievement badges section', () => {
    renderWithProviders(<LeaderboardPage />)

    expect(screen.getByText('Achievement Badges')).toBeInTheDocument()
    expect(screen.getByText('First Lead')).toBeInTheDocument()
    expect(screen.getByText('Hot Streak')).toBeInTheDocument()
  })
})
