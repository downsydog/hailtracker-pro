import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { LeaderboardPage } from './leaderboard'

// Use vi.hoisted for proper mock hoisting
const { mockGetLeaderboard, mockGetLeaderboardStats, mockGetAchievements } = vi.hoisted(() => ({
  mockGetLeaderboard: vi.fn(),
  mockGetLeaderboardStats: vi.fn(),
  mockGetAchievements: vi.fn(),
}))

// Mock the API module
vi.mock('@/api/elite-sales', () => ({
  getLeaderboard: mockGetLeaderboard,
  getLeaderboardStats: mockGetLeaderboardStats,
  getAchievements: mockGetAchievements,
}))

const mockLeaderboardData = {
  leaderboard: [
    {
      id: 1,
      first_name: 'Mike',
      last_name: 'Johnson',
      leads_today: 8,
      hot_leads_today: 3,
      points: 150,
    },
    {
      id: 2,
      first_name: 'Sarah',
      last_name: 'Williams',
      leads_today: 6,
      hot_leads_today: 2,
      points: 120,
    },
    {
      id: 3,
      first_name: 'Tom',
      last_name: 'Davis',
      leads_today: 5,
      hot_leads_today: 1,
      points: 100,
    },
    {
      id: 4,
      first_name: 'Lisa',
      last_name: 'Brown',
      leads_today: 3,
      hot_leads_today: 0,
      points: 75,
    },
  ],
}

const mockStatsData = {
  today: { leads: 22, hot_leads: 6 },
  this_week: { leads: 85 },
}

const mockAchievementsData = {
  achievements: [
    {
      id: 1,
      salesperson_id: 1,
      achievement_type: 'FIRST_LEAD',
      points: 10,
      earned_at: '2024-01-15T12:00:00Z',
    },
    {
      id: 2,
      salesperson_id: 1,
      achievement_type: 'HOT_STREAK',
      points: 50,
      earned_at: '2024-01-18T16:00:00Z',
    },
  ],
  total_points: 60,
}

const mockEmptyLeaderboard = {
  leaderboard: [],
}

const mockEmptyAchievements = {
  achievements: [],
  total_points: 0,
}

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
    mockGetLeaderboard.mockResolvedValue(mockLeaderboardData)
    mockGetLeaderboardStats.mockResolvedValue(mockStatsData)
    mockGetAchievements.mockResolvedValue(mockAchievementsData)
  })

  describe('Page Rendering', () => {
    it('renders the page title', () => {
      renderWithProviders(<LeaderboardPage />)

      expect(screen.getByText('Leaderboard')).toBeInTheDocument()
    })

    it('renders the page description', () => {
      renderWithProviders(<LeaderboardPage />)

      expect(screen.getByText('Real-time team rankings and achievements')).toBeInTheDocument()
    })

    it('displays Your Rank badge when user is in leaderboard', async () => {
      renderWithProviders(<LeaderboardPage />)

      await waitFor(() => {
        expect(screen.getByText(/Your Rank: #1/)).toBeInTheDocument()
      })
    })
  })

  describe('Team Stats Cards', () => {
    it('displays Today\'s Leads stat card', async () => {
      renderWithProviders(<LeaderboardPage />)

      expect(screen.getByText("Today's Leads")).toBeInTheDocument()

      await waitFor(() => {
        expect(screen.getByText('22')).toBeInTheDocument()
      })
    })

    it('displays Hot Leads Today stat card', async () => {
      renderWithProviders(<LeaderboardPage />)

      expect(screen.getByText('Hot Leads Today')).toBeInTheDocument()

      await waitFor(() => {
        expect(screen.getByText('6')).toBeInTheDocument()
      })
    })

    it('displays This Week stat card', async () => {
      renderWithProviders(<LeaderboardPage />)

      expect(screen.getByText('This Week')).toBeInTheDocument()

      await waitFor(() => {
        expect(screen.getByText('85')).toBeInTheDocument()
      })
    })

    it('displays Active Team stat card', async () => {
      renderWithProviders(<LeaderboardPage />)

      expect(screen.getByText('Active Team')).toBeInTheDocument()

      // Wait for leaderboard data to load first
      await waitFor(() => {
        expect(screen.getByText('Mike Johnson')).toBeInTheDocument()
      })

      // 4 team members in mock data - find the stat card specifically
      const activeTeamValues = screen.getAllByText('4')
      expect(activeTeamValues.length).toBeGreaterThanOrEqual(1)
    })
  })

  describe('Rankings Section', () => {
    it('displays Rankings header', async () => {
      renderWithProviders(<LeaderboardPage />)

      await waitFor(() => {
        expect(screen.getByText('Rankings')).toBeInTheDocument()
      })
    })

    it('displays leaderboard entries', async () => {
      renderWithProviders(<LeaderboardPage />)

      await waitFor(() => {
        expect(screen.getByText('Mike Johnson')).toBeInTheDocument()
      })

      expect(screen.getByText('Sarah Williams')).toBeInTheDocument()
      expect(screen.getByText('Tom Davis')).toBeInTheDocument()
      expect(screen.getByText('Lisa Brown')).toBeInTheDocument()
    })

    it('shows points for each salesperson', async () => {
      renderWithProviders(<LeaderboardPage />)

      await waitFor(() => {
        expect(screen.getByText('150')).toBeInTheDocument()
      })

      expect(screen.getByText('120')).toBeInTheDocument()
      expect(screen.getByText('100')).toBeInTheDocument()
      expect(screen.getByText('75')).toBeInTheDocument()
    })

    it('shows leads count for each entry', async () => {
      renderWithProviders(<LeaderboardPage />)

      await waitFor(() => {
        expect(screen.getByText('8 leads')).toBeInTheDocument()
      })

      expect(screen.getByText('6 leads')).toBeInTheDocument()
      expect(screen.getByText('5 leads')).toBeInTheDocument()
      expect(screen.getByText('3 leads')).toBeInTheDocument()
    })

    it('shows hot leads count for each entry', async () => {
      renderWithProviders(<LeaderboardPage />)

      await waitFor(() => {
        expect(screen.getByText('3 hot')).toBeInTheDocument()
      })

      expect(screen.getByText('2 hot')).toBeInTheDocument()
      expect(screen.getByText('1 hot')).toBeInTheDocument()
      expect(screen.getByText('0 hot')).toBeInTheDocument()
    })

    it('shows "You" badge for current user', async () => {
      renderWithProviders(<LeaderboardPage />)

      await waitFor(() => {
        expect(screen.getByText('You')).toBeInTheDocument()
      })
    })

    it('shows "points" label under each score', async () => {
      renderWithProviders(<LeaderboardPage />)

      await waitFor(() => {
        const pointsLabels = screen.getAllByText('points')
        expect(pointsLabels.length).toBe(4)
      })
    })
  })

  describe('Period Tabs', () => {
    it('displays Today tab', () => {
      renderWithProviders(<LeaderboardPage />)

      expect(screen.getByText('Today')).toBeInTheDocument()
    })

    it('displays Week tab', () => {
      renderWithProviders(<LeaderboardPage />)

      expect(screen.getByText('Week')).toBeInTheDocument()
    })

    it('displays Month tab', () => {
      renderWithProviders(<LeaderboardPage />)

      expect(screen.getByText('Month')).toBeInTheDocument()
    })

    it('switches period when clicking Week tab', async () => {
      const user = userEvent.setup()
      renderWithProviders(<LeaderboardPage />)

      const weekTab = screen.getByText('Week')
      await user.click(weekTab)

      // API should be called with THIS_WEEK period
      await waitFor(() => {
        expect(mockGetLeaderboard).toHaveBeenCalledWith('THIS_WEEK')
      })
    })

    it('switches period when clicking Month tab', async () => {
      const user = userEvent.setup()
      renderWithProviders(<LeaderboardPage />)

      const monthTab = screen.getByText('Month')
      await user.click(monthTab)

      await waitFor(() => {
        expect(mockGetLeaderboard).toHaveBeenCalledWith('THIS_MONTH')
      })
    })
  })

  describe('Loading State', () => {
    it('shows loading message while fetching', async () => {
      mockGetLeaderboard.mockImplementation(() => new Promise(() => {})) // Never resolves
      renderWithProviders(<LeaderboardPage />)

      expect(screen.getByText('Loading...')).toBeInTheDocument()
    })
  })

  describe('Empty State', () => {
    it('shows empty message when no leaderboard entries', async () => {
      mockGetLeaderboard.mockResolvedValue(mockEmptyLeaderboard)
      renderWithProviders(<LeaderboardPage />)

      await waitFor(() => {
        expect(screen.getByText('No activity yet for this period')).toBeInTheDocument()
      })
    })

    it('does not show Your Rank badge when user not in leaderboard', async () => {
      mockGetLeaderboard.mockResolvedValue(mockEmptyLeaderboard)
      renderWithProviders(<LeaderboardPage />)

      await waitFor(() => {
        expect(screen.getByText('No activity yet for this period')).toBeInTheDocument()
      })

      expect(screen.queryByText(/Your Rank:/)).not.toBeInTheDocument()
    })
  })

  describe('Your Achievements Section', () => {
    it('displays Your Achievements header', async () => {
      renderWithProviders(<LeaderboardPage />)

      await waitFor(() => {
        expect(screen.getByText('Your Achievements')).toBeInTheDocument()
      })
    })

    it('displays total points', async () => {
      renderWithProviders(<LeaderboardPage />)

      await waitFor(() => {
        expect(screen.getByText('60')).toBeInTheDocument()
      })

      expect(screen.getByText('Total Points')).toBeInTheDocument()
    })

    it('displays achievement types', async () => {
      renderWithProviders(<LeaderboardPage />)

      await waitFor(() => {
        expect(screen.getByText('FIRST_LEAD')).toBeInTheDocument()
      })

      expect(screen.getByText('HOT_STREAK')).toBeInTheDocument()
    })

    it('shows empty achievements message when none', async () => {
      mockGetAchievements.mockResolvedValue(mockEmptyAchievements)
      renderWithProviders(<LeaderboardPage />)

      await waitFor(() => {
        expect(screen.getByText('No achievements yet')).toBeInTheDocument()
      })

      expect(screen.getByText('Start canvassing to earn badges!')).toBeInTheDocument()
    })
  })

  describe('Achievement Badges Section', () => {
    it('displays Achievement Badges header', () => {
      renderWithProviders(<LeaderboardPage />)

      expect(screen.getByText('Achievement Badges')).toBeInTheDocument()
    })

    it('shows First Lead badge', () => {
      renderWithProviders(<LeaderboardPage />)

      expect(screen.getByText('First Lead')).toBeInTheDocument()
      expect(screen.getByText('Capture your first lead')).toBeInTheDocument()
    })

    it('shows Hot Streak badge', () => {
      renderWithProviders(<LeaderboardPage />)

      expect(screen.getByText('Hot Streak')).toBeInTheDocument()
      expect(screen.getByText('5 hot leads in a day')).toBeInTheDocument()
    })

    it('shows Road Warrior badge', () => {
      renderWithProviders(<LeaderboardPage />)

      expect(screen.getByText('Road Warrior')).toBeInTheDocument()
      expect(screen.getByText('Complete 100 stops')).toBeInTheDocument()
    })

    it('shows Top Performer badge', () => {
      renderWithProviders(<LeaderboardPage />)

      expect(screen.getByText('Top Performer')).toBeInTheDocument()
      expect(screen.getByText('Rank #1 for a day')).toBeInTheDocument()
    })

    it('shows Consistent badge', () => {
      renderWithProviders(<LeaderboardPage />)

      expect(screen.getByText('Consistent')).toBeInTheDocument()
      expect(screen.getByText('Active 5 days straight')).toBeInTheDocument()
    })

    it('shows Intel Master badge', () => {
      renderWithProviders(<LeaderboardPage />)

      expect(screen.getByText('Intel Master')).toBeInTheDocument()
      expect(screen.getByText('Log 10 competitors')).toBeInTheDocument()
    })
  })

  describe('Rank Icons and Styling', () => {
    it('displays rank 1 with gold styling', async () => {
      renderWithProviders(<LeaderboardPage />)

      await waitFor(() => {
        expect(screen.getByText('Mike Johnson')).toBeInTheDocument()
      })

      // First place entry should have gold background class
      const entries = document.querySelectorAll('.bg-gradient-to-r')
      expect(entries.length).toBeGreaterThan(0)
    })

    it('displays all 4 ranked entries', async () => {
      renderWithProviders(<LeaderboardPage />)

      await waitFor(() => {
        expect(screen.getByText('Mike Johnson')).toBeInTheDocument()
        expect(screen.getByText('Sarah Williams')).toBeInTheDocument()
        expect(screen.getByText('Tom Davis')).toBeInTheDocument()
        expect(screen.getByText('Lisa Brown')).toBeInTheDocument()
      })
    })
  })
})
