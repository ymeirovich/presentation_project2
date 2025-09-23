import React from 'react'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { WorkflowList } from '../WorkflowList'
import * as assessApi from '@/lib/assess-api'
import { WorkflowDetail } from '@/lib/assess-schemas'

// Mock the assess-api module
jest.mock('@/lib/assess-api')
const mockFetchWorkflows = assessApi.fetchWorkflows as jest.MockedFunction<typeof assessApi.fetchWorkflows>

// Mock workflow data
const mockWorkflows: WorkflowDetail[] = [
  {
    id: '123e4567-e89b-12d3-a456-426614174000',
    user_id: 'test-user-1',
    certification_profile_id: '987fcdeb-51a2-43d7-8765-ba9876543210',
    current_step: 'generate_questions',
    execution_status: 'in_progress',
    workflow_type: 'assessment_generation',
    parameters: {
      title: 'AWS Solutions Architect Assessment',
      difficulty: 'intermediate',
      question_count: 20,
    },
    progress: 45,
    created_at: '2025-01-15T10:30:00Z',
    updated_at: '2025-01-15T10:35:00Z',
    estimated_completion_at: '2025-01-15T11:00:00Z',
    completed_at: null,
    resume_token: null,
    error_message: null,
  },
  {
    id: '456e7890-e89b-12d3-a456-426614174001',
    user_id: 'test-user-2',
    certification_profile_id: '123fcdeb-51a2-43d7-8765-ba9876543211',
    current_step: 'finalize_workflow',
    execution_status: 'completed',
    workflow_type: 'assessment_generation',
    parameters: {
      title: 'Microsoft Azure Fundamentals',
      difficulty: 'beginner',
      question_count: 15,
    },
    progress: 100,
    created_at: '2025-01-15T09:00:00Z',
    updated_at: '2025-01-15T09:30:00Z',
    estimated_completion_at: null,
    completed_at: '2025-01-15T09:30:00Z',
    resume_token: null,
    error_message: null,
  },
  {
    id: '789e0123-e89b-12d3-a456-426614174002',
    user_id: 'test-user-3',
    certification_profile_id: '456fcdeb-51a2-43d7-8765-ba9876543212',
    current_step: 'validate_questions',
    execution_status: 'failed',
    workflow_type: 'assessment_generation',
    parameters: {
      title: 'Google Cloud Professional',
      difficulty: 'advanced',
      question_count: 30,
    },
    progress: 25,
    created_at: '2025-01-15T08:00:00Z',
    updated_at: '2025-01-15T08:15:00Z',
    estimated_completion_at: null,
    completed_at: null,
    resume_token: null,
    error_message: 'Failed to validate generated questions',
  },
]

describe('WorkflowList', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    jest.useFakeTimers()
  })

  afterEach(() => {
    jest.runOnlyPendingTimers()
    jest.useRealTimers()
  })

  it('renders loading state initially', async () => {
    mockFetchWorkflows.mockImplementation(() => new Promise(() => {})) // Never resolves

    render(<WorkflowList />)

    expect(screen.getByText('Loading workflows...')).toBeInTheDocument()
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument()
  })

  it('renders workflow list successfully', async () => {
    mockFetchWorkflows.mockResolvedValue(mockWorkflows)

    render(<WorkflowList />)

    await waitFor(() => {
      expect(screen.getByText('AWS Solutions Architect Assessment')).toBeInTheDocument()
      expect(screen.getByText('Microsoft Azure Fundamentals')).toBeInTheDocument()
      expect(screen.getByText('Google Cloud Professional')).toBeInTheDocument()
    })

    // Check status badges
    expect(screen.getByText('in_progress')).toBeInTheDocument()
    expect(screen.getByText('completed')).toBeInTheDocument()
    expect(screen.getByText('failed')).toBeInTheDocument()

    // Check progress indicators
    expect(screen.getByText('45%')).toBeInTheDocument()
    expect(screen.getByText('100%')).toBeInTheDocument()
    expect(screen.getByText('25%')).toBeInTheDocument()
  })

  it('handles API error state', async () => {
    const errorMessage = 'Failed to fetch workflows'
    mockFetchWorkflows.mockRejectedValue(new Error(errorMessage))

    render(<WorkflowList />)

    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument()
      expect(screen.getByText('Try Again')).toBeInTheDocument()
    })
  })

  it('shows empty state when no workflows found', async () => {
    mockFetchWorkflows.mockResolvedValue([])

    render(<WorkflowList />)

    await waitFor(() => {
      expect(screen.getByText('No workflows found.')).toBeInTheDocument()
    })
  })

  it('filters workflows by search term', async () => {
    mockFetchWorkflows.mockResolvedValue(mockWorkflows)
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime })

    render(<WorkflowList />)

    await waitFor(() => {
      expect(screen.getByText('AWS Solutions Architect Assessment')).toBeInTheDocument()
    })

    const searchInput = screen.getByPlaceholderText('Search workflows...')
    await user.type(searchInput, 'aws')

    // Should show only AWS workflow
    expect(screen.getByText('AWS Solutions Architect Assessment')).toBeInTheDocument()
    expect(screen.queryByText('Microsoft Azure Fundamentals')).not.toBeInTheDocument()
    expect(screen.queryByText('Google Cloud Professional')).not.toBeInTheDocument()
  })

  it('shows filtered empty state when search has no results', async () => {
    mockFetchWorkflows.mockResolvedValue(mockWorkflows)
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime })

    render(<WorkflowList />)

    await waitFor(() => {
      expect(screen.getByText('AWS Solutions Architect Assessment')).toBeInTheDocument()
    })

    const searchInput = screen.getByPlaceholderText('Search workflows...')
    await user.type(searchInput, 'nonexistent')

    expect(screen.getByText('No workflows match your search.')).toBeInTheDocument()
  })

  it('filters workflows by status', async () => {
    mockFetchWorkflows.mockResolvedValue(mockWorkflows)
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime })

    render(<WorkflowList />)

    await waitFor(() => {
      expect(screen.getByText('AWS Solutions Architect Assessment')).toBeInTheDocument()
    })

    // Click on filter dropdown
    const filterButton = screen.getByRole('button', { name: /All Workflows/ })
    await user.click(filterButton)

    // Select "Completed" filter
    const completedOption = screen.getByRole('menuitem', { name: 'Completed' })
    await user.click(completedOption)

    // Should refetch with status filter
    await waitFor(() => {
      expect(mockFetchWorkflows).toHaveBeenCalledWith({
        status_filter: 'completed',
        limit: 50,
      })
    })
  })

  it('handles workflow selection', async () => {
    mockFetchWorkflows.mockResolvedValue(mockWorkflows)
    const onWorkflowSelect = jest.fn()
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime })

    render(<WorkflowList onWorkflowSelect={onWorkflowSelect} />)

    await waitFor(() => {
      expect(screen.getByText('AWS Solutions Architect Assessment')).toBeInTheDocument()
    })

    const workflowCard = screen.getByText('AWS Solutions Architect Assessment').closest('div')
    await user.click(workflowCard!)

    expect(onWorkflowSelect).toHaveBeenCalledWith(mockWorkflows[0])
  })

  it('shows workflow timeline when workflow is selected', async () => {
    mockFetchWorkflows.mockResolvedValue(mockWorkflows)
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime })

    render(<WorkflowList />)

    await waitFor(() => {
      expect(screen.getByText('AWS Solutions Architect Assessment')).toBeInTheDocument()
    })

    const workflowCard = screen.getByText('AWS Solutions Architect Assessment').closest('div')
    await user.click(workflowCard!)

    // Should show back button and timeline
    expect(screen.getByText('← Back to List')).toBeInTheDocument()
    expect(screen.getByText('Workflow Timeline')).toBeInTheDocument()
  })

  it('refreshes workflows when refresh button is clicked', async () => {
    mockFetchWorkflows.mockResolvedValue(mockWorkflows)
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime })

    render(<WorkflowList />)

    await waitFor(() => {
      expect(screen.getByText('AWS Solutions Architect Assessment')).toBeInTheDocument()
    })

    const refreshButton = screen.getByRole('button', { name: '' }) // Refresh icon button
    await user.click(refreshButton)

    // Should call fetchWorkflows again
    expect(mockFetchWorkflows).toHaveBeenCalledTimes(2)
  })

  it('polls for updates every 30 seconds', async () => {
    mockFetchWorkflows.mockResolvedValue(mockWorkflows)

    render(<WorkflowList />)

    await waitFor(() => {
      expect(mockFetchWorkflows).toHaveBeenCalledTimes(1)
    })

    // Advance timers by 30 seconds
    jest.advanceTimersByTime(30000)

    await waitFor(() => {
      expect(mockFetchWorkflows).toHaveBeenCalledTimes(2)
    })

    // Advance another 30 seconds
    jest.advanceTimersByTime(30000)

    await waitFor(() => {
      expect(mockFetchWorkflows).toHaveBeenCalledTimes(3)
    })
  })

  it('displays error messages for failed workflows', async () => {
    mockFetchWorkflows.mockResolvedValue(mockWorkflows)

    render(<WorkflowList />)

    await waitFor(() => {
      expect(screen.getByText('Failed to validate generated questions')).toBeInTheDocument()
    })
  })

  it('shows spinning icon for in-progress workflows', async () => {
    mockFetchWorkflows.mockResolvedValue(mockWorkflows)

    render(<WorkflowList />)

    await waitFor(() => {
      const inProgressWorkflow = screen.getByText('AWS Solutions Architect Assessment').closest('div')
      const spinningIcon = inProgressWorkflow?.querySelector('.animate-spin')
      expect(spinningIcon).toBeInTheDocument()
    })
  })

  it('handles retry from timeline view', async () => {
    mockFetchWorkflows.mockResolvedValue(mockWorkflows)
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime })

    render(<WorkflowList />)

    await waitFor(() => {
      expect(screen.getByText('Google Cloud Professional')).toBeInTheDocument()
    })

    // Click on failed workflow
    const failedWorkflowCard = screen.getByText('Google Cloud Professional').closest('div')
    await user.click(failedWorkflowCard!)

    // Should show timeline view
    expect(screen.getByText('Workflow Timeline')).toBeInTheDocument()

    // Mock the retry callback
    const timelineComponent = screen.getByTestId('workflow-timeline') // We'll need to add this data-testid
    fireEvent.click(timelineComponent) // Simulate retry action

    // Should refresh the workflow list
    await waitFor(() => {
      expect(mockFetchWorkflows).toHaveBeenCalledTimes(2)
    })
  })
})