import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter } from 'react-router-dom'
import { ScriptsPage } from './scripts'

// Use vi.hoisted for proper mock hoisting
const { mockGetScript, mockLogObjection } = vi.hoisted(() => ({
  mockGetScript: vi.fn(),
  mockLogObjection: vi.fn(),
}))

// Mock the API module
vi.mock('@/api/elite-sales', () => ({
  getScript: mockGetScript,
  logObjection: mockLogObjection,
}))

const mockScriptData = {
  script: {
    category: 'DOOR_APPROACH',
    opening: 'Hi there! My name is [Name] with HailTracker Pro.',
    response: 'I understand your concern. Let me explain how we can help.',
    key_points: ['Make eye contact', 'Stand back from door', 'Have clipboard ready'],
    tips: ['Best times are 4-7pm weekdays', 'Avoid meal times'],
  },
}

const mockScriptWithResponseOnly = {
  script: {
    category: 'OBJECTION_PRICE',
    opening: null,
    response: 'I completely understand the price concern.',
    key_points: [],
    tips: [],
  },
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

describe('ScriptsPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    mockGetScript.mockResolvedValue(mockScriptData)
    mockLogObjection.mockResolvedValue({ success: true })
  })

  describe('Page Rendering', () => {
    it('renders the page title', () => {
      renderWithProviders(<ScriptsPage />)

      expect(screen.getByText('Smart Scripts')).toBeInTheDocument()
    })

    it('renders the page description', () => {
      renderWithProviders(<ScriptsPage />)

      expect(screen.getByText('Sales scripts and objection handling guides')).toBeInTheDocument()
    })

    it('renders the Categories header', () => {
      renderWithProviders(<ScriptsPage />)

      expect(screen.getByText('Categories')).toBeInTheDocument()
    })
  })

  describe('Script Categories', () => {
    it('displays all script categories', () => {
      renderWithProviders(<ScriptsPage />)

      expect(screen.getAllByText('Door Approach').length).toBeGreaterThan(0)
      expect(screen.getAllByText('Price Objection').length).toBeGreaterThan(0)
      expect(screen.getAllByText('Time Objection').length).toBeGreaterThan(0)
      expect(screen.getAllByText('Insurance Objection').length).toBeGreaterThan(0)
      expect(screen.getAllByText('Closing').length).toBeGreaterThan(0)
    })

    it('displays category descriptions', () => {
      renderWithProviders(<ScriptsPage />)

      expect(screen.getByText('Opening scripts for initial contact')).toBeInTheDocument()
      expect(screen.getByText('Handling price concerns')).toBeInTheDocument()
      expect(screen.getByText("When they say 'not now'")).toBeInTheDocument()
      expect(screen.getByText('Insurance-related concerns')).toBeInTheDocument()
      expect(screen.getByText('Scripts to close the appointment')).toBeInTheDocument()
    })

    it('switches category when clicking sidebar item', async () => {
      const user = userEvent.setup()
      renderWithProviders(<ScriptsPage />)

      const priceCategory = screen.getByText('Price Objection')
      await user.click(priceCategory)

      // API should be called with new category
      await waitFor(() => {
        expect(mockGetScript).toHaveBeenCalledWith('OBJECTION_PRICE')
      })
    })

    it('calls getScript for each category when selected', async () => {
      const user = userEvent.setup()
      renderWithProviders(<ScriptsPage />)

      // Initially Door Approach is selected
      await waitFor(() => {
        expect(mockGetScript).toHaveBeenCalledWith('DOOR_APPROACH')
      })

      // Click Time Objection
      await user.click(screen.getByText('Time Objection'))
      await waitFor(() => {
        expect(mockGetScript).toHaveBeenCalledWith('OBJECTION_TIME')
      })

      // Click Insurance Objection
      await user.click(screen.getByText('Insurance Objection'))
      await waitFor(() => {
        expect(mockGetScript).toHaveBeenCalledWith('OBJECTION_INSURANCE')
      })

      // Click Closing
      await user.click(screen.getByText('Closing'))
      await waitFor(() => {
        expect(mockGetScript).toHaveBeenCalledWith('CLOSE_APPOINTMENT')
      })
    })
  })

  describe('Script Content', () => {
    it('displays opening section when available', async () => {
      renderWithProviders(<ScriptsPage />)

      await waitFor(() => {
        expect(screen.getByText('Opening')).toBeInTheDocument()
      })

      expect(screen.getByText(/Hi there! My name is/)).toBeInTheDocument()
    })

    it('displays response section when available', async () => {
      renderWithProviders(<ScriptsPage />)

      await waitFor(() => {
        expect(screen.getByText('Response')).toBeInTheDocument()
      })

      expect(screen.getByText(/I understand your concern/)).toBeInTheDocument()
    })

    it('displays key points when available', async () => {
      renderWithProviders(<ScriptsPage />)

      await waitFor(() => {
        expect(screen.getByText('Key Points')).toBeInTheDocument()
      })

      expect(screen.getByText('Make eye contact')).toBeInTheDocument()
      expect(screen.getByText('Stand back from door')).toBeInTheDocument()
      expect(screen.getByText('Have clipboard ready')).toBeInTheDocument()
    })

    it('displays pro tips when available', async () => {
      renderWithProviders(<ScriptsPage />)

      await waitFor(() => {
        expect(screen.getByText('Pro Tips')).toBeInTheDocument()
      })

      expect(screen.getByText(/Best times are 4-7pm/)).toBeInTheDocument()
      expect(screen.getByText(/Avoid meal times/)).toBeInTheDocument()
    })

    it('shows numbered key points', async () => {
      renderWithProviders(<ScriptsPage />)

      await waitFor(() => {
        expect(screen.getByText('1')).toBeInTheDocument()
        expect(screen.getByText('2')).toBeInTheDocument()
        expect(screen.getByText('3')).toBeInTheDocument()
      })
    })
  })

  describe('Loading State', () => {
    it('shows loading message while fetching script', async () => {
      mockGetScript.mockImplementation(() => new Promise(() => {})) // Never resolves
      renderWithProviders(<ScriptsPage />)

      expect(screen.getByText('Loading script...')).toBeInTheDocument()
    })
  })

  describe('No Script State', () => {
    it('shows no script message when script is null', async () => {
      mockGetScript.mockResolvedValue({ script: null })
      renderWithProviders(<ScriptsPage />)

      await waitFor(() => {
        expect(screen.getByText('No script available for this category')).toBeInTheDocument()
      })
    })
  })

  describe('Copy to Clipboard', () => {
    it('has copy buttons for script sections', async () => {
      renderWithProviders(<ScriptsPage />)

      await waitFor(() => {
        expect(screen.getByText('Opening')).toBeInTheDocument()
      })

      // Should have multiple copy buttons
      const buttons = screen.getAllByRole('button')
      expect(buttons.length).toBeGreaterThan(3)
    })

    it('has copy button next to opening section', async () => {
      renderWithProviders(<ScriptsPage />)

      await waitFor(() => {
        expect(screen.getByText('Opening')).toBeInTheDocument()
      })

      // The opening section should have a copy button (ghost variant with icon only)
      const openingHeader = screen.getByText('Opening')
      const flexContainer = openingHeader.parentElement
      expect(flexContainer).toBeInTheDocument()

      // There should be a sibling button in the same flex container
      const siblingButton = flexContainer?.querySelector('button')
      expect(siblingButton).toBeInTheDocument()
    })
  })

  describe('Quick Reference Cards', () => {
    it('displays price objection quick response card', () => {
      renderWithProviders(<ScriptsPage />)

      expect(screen.getByText('Price Objection Quick Response')).toBeInTheDocument()
      expect(screen.getByText(/I completely understand. Many of my customers/)).toBeInTheDocument()
    })

    it('displays time objection quick response card', () => {
      renderWithProviders(<ScriptsPage />)

      expect(screen.getByText('Time Objection Quick Response')).toBeInTheDocument()
      expect(screen.getByText(/I understand you're busy/)).toBeInTheDocument()
    })

    it('displays insurance quick response card', () => {
      renderWithProviders(<ScriptsPage />)

      expect(screen.getByText('Insurance Quick Response')).toBeInTheDocument()
      expect(screen.getByText(/Great question! Most comprehensive insurance/)).toBeInTheDocument()
    })

    it('has copy buttons on quick reference cards', () => {
      renderWithProviders(<ScriptsPage />)

      // There should be Copy buttons with text "Copy"
      const copyButtons = screen.getAllByRole('button', { name: /copy/i })
      expect(copyButtons.length).toBeGreaterThanOrEqual(3)
    })

    it('clicking copy button changes to copied state', async () => {
      const user = userEvent.setup()
      renderWithProviders(<ScriptsPage />)

      // Wait for page to render
      await waitFor(() => {
        expect(screen.getByText('Price Objection Quick Response')).toBeInTheDocument()
      })

      // Find Copy buttons (they have "Copy" text)
      const copyButtons = screen.getAllByRole('button', { name: /copy/i })
      expect(copyButtons.length).toBeGreaterThan(0)

      // Click the first Copy button
      await user.click(copyButtons[0])

      // After clicking, the button should show "Copied!" state
      await waitFor(() => {
        expect(screen.getByText('Copied!')).toBeInTheDocument()
      })
    })
  })

  describe('Log Outcome Button', () => {
    it('has a Log Outcome button', () => {
      renderWithProviders(<ScriptsPage />)

      expect(screen.getByText('Log Outcome')).toBeInTheDocument()
    })

    it('opens log outcome dialog when clicking button', async () => {
      const user = userEvent.setup()
      renderWithProviders(<ScriptsPage />)

      const logButton = screen.getByText('Log Outcome')
      await user.click(logButton)

      await waitFor(() => {
        expect(screen.getByText('Log Objection Outcome')).toBeInTheDocument()
      })
    })
  })

  describe('Log Outcome Dialog', () => {
    it('shows dialog title and description', async () => {
      const user = userEvent.setup()
      renderWithProviders(<ScriptsPage />)

      await user.click(screen.getByText('Log Outcome'))

      await waitFor(() => {
        expect(screen.getByText('Log Objection Outcome')).toBeInTheDocument()
        expect(screen.getByText('How did the conversation go after using the script?')).toBeInTheDocument()
      })
    })

    it('shows outcome options (Converted, Follow Up, Lost)', async () => {
      const user = userEvent.setup()
      renderWithProviders(<ScriptsPage />)

      await user.click(screen.getByText('Log Outcome'))

      await waitFor(() => {
        expect(screen.getByText('Converted')).toBeInTheDocument()
        expect(screen.getByText('Follow Up')).toBeInTheDocument()
        expect(screen.getByText('Lost')).toBeInTheDocument()
      })
    })

    it('has Cancel button in dialog', async () => {
      const user = userEvent.setup()
      renderWithProviders(<ScriptsPage />)

      await user.click(screen.getByText('Log Outcome'))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: /cancel/i })).toBeInTheDocument()
      })
    })

    it('has Log Outcome submit button in dialog', async () => {
      const user = userEvent.setup()
      renderWithProviders(<ScriptsPage />)

      await user.click(screen.getByText('Log Outcome'))

      await waitFor(() => {
        // There should be two "Log Outcome" texts - one button that opens dialog and one submit button
        const logButtons = screen.getAllByText('Log Outcome')
        expect(logButtons.length).toBe(2)
      })
    })

    it('closes dialog when Cancel is clicked', async () => {
      const user = userEvent.setup()
      renderWithProviders(<ScriptsPage />)

      await user.click(screen.getByText('Log Outcome'))

      await waitFor(() => {
        expect(screen.getByText('Log Objection Outcome')).toBeInTheDocument()
      })

      await user.click(screen.getByRole('button', { name: /cancel/i }))

      await waitFor(() => {
        expect(screen.queryByText('Log Objection Outcome')).not.toBeInTheDocument()
      })
    })

    it('allows selecting Converted outcome', async () => {
      const user = userEvent.setup()
      renderWithProviders(<ScriptsPage />)

      await user.click(screen.getByText('Log Outcome'))

      await waitFor(() => {
        expect(screen.getByText('Converted')).toBeInTheDocument()
      })

      await user.click(screen.getByText('Converted'))

      // Button should be selected (styled differently)
      const convertedButton = screen.getByText('Converted').closest('button')
      expect(convertedButton).toBeInTheDocument()
    })

    it('allows selecting Follow Up outcome', async () => {
      const user = userEvent.setup()
      renderWithProviders(<ScriptsPage />)

      await user.click(screen.getByText('Log Outcome'))

      await waitFor(() => {
        expect(screen.getByText('Follow Up')).toBeInTheDocument()
      })

      await user.click(screen.getByText('Follow Up'))

      const followUpButton = screen.getByText('Follow Up').closest('button')
      expect(followUpButton).toBeInTheDocument()
    })

    it('allows selecting Lost outcome', async () => {
      const user = userEvent.setup()
      renderWithProviders(<ScriptsPage />)

      await user.click(screen.getByText('Log Outcome'))

      await waitFor(() => {
        expect(screen.getByText('Lost')).toBeInTheDocument()
      })

      await user.click(screen.getByText('Lost'))

      const lostButton = screen.getByText('Lost').closest('button')
      expect(lostButton).toBeInTheDocument()
    })

    it('calls logObjection when submitting with outcome selected', async () => {
      const user = userEvent.setup()
      renderWithProviders(<ScriptsPage />)

      await user.click(screen.getByText('Log Outcome'))

      await waitFor(() => {
        expect(screen.getByText('Converted')).toBeInTheDocument()
      })

      // Select an outcome
      await user.click(screen.getByText('Converted'))

      // Click the submit button (second "Log Outcome")
      const logButtons = screen.getAllByText('Log Outcome')
      const submitButton = logButtons[logButtons.length - 1]
      await user.click(submitButton)

      await waitFor(() => {
        expect(mockLogObjection).toHaveBeenCalledWith({
          salesperson_id: 1,
          objection_type: 'DOOR_APPROACH',
          response_used: 'Standard script',
          outcome: 'CONVERTED',
        })
      })
    })

    it('calls logObjection with FOLLOW_UP outcome', async () => {
      const user = userEvent.setup()
      renderWithProviders(<ScriptsPage />)

      await user.click(screen.getByText('Log Outcome'))

      await waitFor(() => {
        expect(screen.getByText('Follow Up')).toBeInTheDocument()
      })

      await user.click(screen.getByText('Follow Up'))

      const logButtons = screen.getAllByText('Log Outcome')
      await user.click(logButtons[logButtons.length - 1])

      await waitFor(() => {
        expect(mockLogObjection).toHaveBeenCalledWith(
          expect.objectContaining({ outcome: 'FOLLOW_UP' })
        )
      })
    })

    it('calls logObjection with LOST outcome', async () => {
      const user = userEvent.setup()
      renderWithProviders(<ScriptsPage />)

      await user.click(screen.getByText('Log Outcome'))

      await waitFor(() => {
        expect(screen.getByText('Lost')).toBeInTheDocument()
      })

      await user.click(screen.getByText('Lost'))

      const logButtons = screen.getAllByText('Log Outcome')
      await user.click(logButtons[logButtons.length - 1])

      await waitFor(() => {
        expect(mockLogObjection).toHaveBeenCalledWith(
          expect.objectContaining({ outcome: 'LOST' })
        )
      })
    })

    it('closes dialog after successful submission', async () => {
      const user = userEvent.setup()
      renderWithProviders(<ScriptsPage />)

      await user.click(screen.getByText('Log Outcome'))

      await waitFor(() => {
        expect(screen.getByText('Converted')).toBeInTheDocument()
      })

      await user.click(screen.getByText('Converted'))

      const logButtons = screen.getAllByText('Log Outcome')
      await user.click(logButtons[logButtons.length - 1])

      await waitFor(() => {
        expect(screen.queryByText('Log Objection Outcome')).not.toBeInTheDocument()
      })
    })
  })

  describe('Script Content with Response Only', () => {
    it('displays response section without opening', async () => {
      mockGetScript.mockResolvedValue(mockScriptWithResponseOnly)
      renderWithProviders(<ScriptsPage />)

      await waitFor(() => {
        expect(screen.getByText('Response')).toBeInTheDocument()
      })

      expect(screen.getByText(/I completely understand the price concern/)).toBeInTheDocument()
      // Opening should not be present
      expect(screen.queryByText('Opening')).not.toBeInTheDocument()
    })

    it('does not show key points section when empty', async () => {
      mockGetScript.mockResolvedValue(mockScriptWithResponseOnly)
      renderWithProviders(<ScriptsPage />)

      await waitFor(() => {
        expect(screen.getByText('Response')).toBeInTheDocument()
      })

      expect(screen.queryByText('Key Points')).not.toBeInTheDocument()
    })

    it('does not show pro tips section when empty', async () => {
      mockGetScript.mockResolvedValue(mockScriptWithResponseOnly)
      renderWithProviders(<ScriptsPage />)

      await waitFor(() => {
        expect(screen.getByText('Response')).toBeInTheDocument()
      })

      expect(screen.queryByText('Pro Tips')).not.toBeInTheDocument()
    })
  })
})
