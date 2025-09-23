import React from 'react'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { WorkflowTimeline } from '../WorkflowTimeline'
import * as assessApi from '@/lib/assess-api'
import { WorkflowDetail } from '@/lib/assess-schemas'

// Mock the assess-api module
jest.mock('@/lib/assess-api')
const mockFetchWorkflowDetail = assessApi.fetchWorkflowDetail as jest.MockedFunction<typeof assessApi.fetchWorkflowDetail>
const mockRetryWorkflow = assessApi.retryWorkflow as jest.MockedFunction<typeof assessApi.retryWorkflow>

// Mock workflow data
const mockWorkflowInProgress: WorkflowDetail = {
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
  step_execution_log: [
    {
      step: 'validate_input',
      status: 'completed',
      started_at: '2025-01-15T10:30:00Z',
      completed_at: '2025-01-15T10:31:00Z',
      error_message: null,
      duration_seconds: 60,
    },
    {
      step: 'fetch_certification',
      status: 'completed',
      started_at: '2025-01-15T10:31:00Z',
      completed_at: '2025-01-15T10:32:00Z',
      error_message: null,
      duration_seconds: 60,
    },
    {
      step: 'setup_knowledge_base',
      status: 'completed',
      started_at: '2025-01-15T10:32:00Z',
      completed_at: '2025-01-15T10:34:00Z',
      error_message: null,
      duration_seconds: 120,
    },
    {
      step: 'generate_questions',
      status: 'in_progress',
      started_at: '2025-01-15T10:34:00Z',
      completed_at: null,
      error_message: null,
      duration_seconds: null,
    },
  ],
}

const mockWorkflowFailed: WorkflowDetail = {
  ...mockWorkflowInProgress,
  execution_status: 'failed',
  current_step: 'validate_questions',
  progress: 25,
  error_message: 'Question validation failed due to insufficient context',
  step_execution_log: [
    ...mockWorkflowInProgress.step_execution_log!.slice(0, 3),
    {
      step: 'generate_questions',
      status: 'completed',
      started_at: '2025-01-15T10:34:00Z',
      completed_at: '2025-01-15T10:36:00Z',
      error_message: null,
      duration_seconds: 120,
    },
    {
      step: 'validate_questions',
      status: 'failed',
      started_at: '2025-01-15T10:36:00Z',
      completed_at: null,
      error_message: 'Question validation failed due to insufficient context',
      duration_seconds: null,
    },
  ],
}

const mockWorkflowCompleted: WorkflowDetail = {
  ...mockWorkflowInProgress,
  execution_status: 'completed',
  current_step: 'finalize_workflow',
  progress: 100,
  completed_at: '2025-01-15T10:45:00Z',
}

describe('WorkflowTimeline', () => {
  beforeEach(() => {
    jest.clearAllMocks()
    jest.useFakeTimers()
  })

  afterEach(() => {
    jest.runOnlyPendingTimers()
    jest.useRealTimers()
  })

  it('renders loading state initially', async () => {
    mockFetchWorkflowDetail.mockImplementation(() => new Promise(() => {})) // Never resolves

    render(<WorkflowTimeline workflowId="test-workflow-id" />)

    expect(screen.getByText('Loading workflow...')).toBeInTheDocument()
    expect(screen.getByTestId('loading-spinner')).toBeInTheDocument()
  })

  it('renders workflow timeline successfully', async () => {
    mockFetchWorkflowDetail.mockResolvedValue(mockWorkflowInProgress)

    render(<WorkflowTimeline workflowId="test-workflow-id" />)

    await waitFor(() => {
      expect(screen.getByText('Workflow Timeline')).toBeInTheDocument()
      expect(screen.getByText('in_progress')).toBeInTheDocument()
      expect(screen.getByText('45%')).toBeInTheDocument()
    })

    // Check that all workflow steps are displayed
    expect(screen.getByText('Validate Input')).toBeInTheDocument()
    expect(screen.getByText('Load Certification')).toBeInTheDocument()
    expect(screen.getByText('Setup Knowledge Base')).toBeInTheDocument()
    expect(screen.getByText('Generate Questions')).toBeInTheDocument()
    expect(screen.getByText('Validate Questions')).toBeInTheDocument()
  })

  it('handles API error state', async () => {
    const errorMessage = 'Failed to fetch workflow'
    mockFetchWorkflowDetail.mockRejectedValue(new Error(errorMessage))

    render(<WorkflowTimeline workflowId="test-workflow-id" />)

    await waitFor(() => {
      expect(screen.getByText(errorMessage)).toBeInTheDocument()
      expect(screen.getByText('Try Again')).toBeInTheDocument()
    })
  })

  it('shows workflow not found state', async () => {
    mockFetchWorkflowDetail.mockResolvedValue(null as unknown as WorkflowDetail)

    render(<WorkflowTimeline workflowId="test-workflow-id" />)

    await waitFor(() => {
      expect(screen.getByText('Workflow not found')).toBeInTheDocument()
    })
  })

  it('displays step statuses correctly', async () => {
    mockFetchWorkflowDetail.mockResolvedValue(mockWorkflowInProgress)

    render(<WorkflowTimeline workflowId="test-workflow-id" />)

    await waitFor(() => {
      // Check completed steps have check icons
      const completedSteps = screen.getAllByTestId('completed-step-icon')
      expect(completedSteps).toHaveLength(3)

      // Check in-progress step has spinning icon
      const inProgressIcon = screen.getByTestId('in-progress-step-icon')
      expect(inProgressIcon).toBeInTheDocument()
      expect(inProgressIcon).toHaveClass('animate-spin')
    })
  })

  it('displays step durations for completed steps', async () => {
    mockFetchWorkflowDetail.mockResolvedValue(mockWorkflowInProgress)

    render(<WorkflowTimeline workflowId="test-workflow-id" />)

    await waitFor(() => {
      expect(screen.getByText('60s')).toBeInTheDocument() // validate_input duration
      expect(screen.getByText('120s')).toBeInTheDocument() // setup_knowledge_base duration
    })
  })

  it('shows retry button for failed workflows', async () => {
    mockFetchWorkflowDetail.mockResolvedValue(mockWorkflowFailed)

    render(<WorkflowTimeline workflowId="test-workflow-id" />)

    await waitFor(() => {
      expect(screen.getByText('Retry Workflow')).toBeInTheDocument()
      expect(screen.getByText('failed')).toBeInTheDocument()
    })
  })

  it('handles retry workflow action', async () => {
    mockFetchWorkflowDetail.mockResolvedValue(mockWorkflowFailed)
    mockRetryWorkflow.mockResolvedValue(mockWorkflowInProgress)
    const onRetry = jest.fn()
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime })

    render(<WorkflowTimeline workflowId="test-workflow-id" onRetry={onRetry} />)

    await waitFor(() => {
      expect(screen.getByText('Retry Workflow')).toBeInTheDocument()
    })

    const retryButton = screen.getByText('Retry Workflow')
    await user.click(retryButton)

    expect(screen.getByText('Retrying...')).toBeInTheDocument()

    await waitFor(() => {
      expect(mockRetryWorkflow).toHaveBeenCalledWith('test-workflow-id')
      expect(onRetry).toHaveBeenCalled()
    })
  })

  it('displays error details section for failed workflows', async () => {
    mockFetchWorkflowDetail.mockResolvedValue(mockWorkflowFailed)

    render(<WorkflowTimeline workflowId="test-workflow-id" />)

    await waitFor(() => {
      expect(screen.getByText('Error Details')).toBeInTheDocument()
      expect(screen.getByText('Question validation failed due to insufficient context')).toBeInTheDocument()
    })
  })

  it('polls for updates every 2 seconds when workflow is in progress', async () => {
    mockFetchWorkflowDetail.mockResolvedValue(mockWorkflowInProgress)

    render(<WorkflowTimeline workflowId="test-workflow-id" />)

    await waitFor(() => {
      expect(mockFetchWorkflowDetail).toHaveBeenCalledTimes(1)
    })

    // Advance timers by 2 seconds
    jest.advanceTimersByTime(2000)

    await waitFor(() => {
      expect(mockFetchWorkflowDetail).toHaveBeenCalledTimes(2)
    })

    // Advance another 2 seconds
    jest.advanceTimersByTime(2000)

    await waitFor(() => {
      expect(mockFetchWorkflowDetail).toHaveBeenCalledTimes(3)
    })
  })

  it('stops polling when workflow is completed', async () => {
    mockFetchWorkflowDetail
      .mockResolvedValueOnce(mockWorkflowInProgress)
      .mockResolvedValue(mockWorkflowCompleted)

    render(<WorkflowTimeline workflowId="test-workflow-id" />)

    await waitFor(() => {
      expect(mockFetchWorkflowDetail).toHaveBeenCalledTimes(1)
    })

    // Advance timers by 2 seconds
    jest.advanceTimersByTime(2000)

    await waitFor(() => {
      expect(mockFetchWorkflowDetail).toHaveBeenCalledTimes(2)
      expect(screen.getByText('completed')).toBeInTheDocument()
    })

    // Advance another 2 seconds - should not poll again for completed workflow
    jest.advanceTimersByTime(2000)

    // Should still be 2 calls since polling stops for completed workflows
    expect(mockFetchWorkflowDetail).toHaveBeenCalledTimes(2)
  })

  it('highlights current step correctly', async () => {
    mockFetchWorkflowDetail.mockResolvedValue(mockWorkflowInProgress)

    render(<WorkflowTimeline workflowId="test-workflow-id" />)

    await waitFor(() => {
      const currentStepElement = screen.getByText('Generate Questions').closest('div')
      expect(currentStepElement).toHaveClass('bg-blue-50', 'border-blue-200')
    })
  })

  it('shows different colors for different step states', async () => {
    mockFetchWorkflowDetail.mockResolvedValue(mockWorkflowFailed)

    render(<WorkflowTimeline workflowId="test-workflow-id" />)

    await waitFor(() => {
      // Completed steps should have green background
      const completedStep = screen.getByText('Generate Questions').closest('div')
      expect(completedStep).toHaveClass('bg-green-50', 'border-green-200')

      // Failed step should have red background
      const failedStep = screen.getByText('Validate Questions').closest('div')
      expect(failedStep).toHaveClass('bg-red-50', 'border-red-200')
    })
  })

  it('handles step error messages correctly', async () => {
    mockFetchWorkflowDetail.mockResolvedValue(mockWorkflowFailed)

    render(<WorkflowTimeline workflowId="test-workflow-id" />)

    await waitFor(() => {
      // Should show step-specific error message instead of default description
      expect(screen.getByText('Question validation failed due to insufficient context')).toBeInTheDocument()
    })
  })

  it('handles retry error gracefully', async () => {
    mockFetchWorkflowDetail.mockResolvedValue(mockWorkflowFailed)
    mockRetryWorkflow.mockRejectedValue(new Error('Retry failed'))
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime })

    render(<WorkflowTimeline workflowId="test-workflow-id" />)

    await waitFor(() => {
      expect(screen.getByText('Retry Workflow')).toBeInTheDocument()
    })

    const retryButton = screen.getByText('Retry Workflow')
    await user.click(retryButton)

    await waitFor(() => {
      expect(screen.getByText('Failed to retry workflow')).toBeInTheDocument()
    })
  })

  it('renders progress bar when progress is available', async () => {
    mockFetchWorkflowDetail.mockResolvedValue(mockWorkflowInProgress)

    render(<WorkflowTimeline workflowId="test-workflow-id" />)

    await waitFor(() => {
      expect(screen.getByText('Progress')).toBeInTheDocument()
      expect(screen.getByRole('progressbar')).toBeInTheDocument()
    })
  })

  it('calls onRetry callback after successful retry', async () => {
    mockFetchWorkflowDetail.mockResolvedValue(mockWorkflowFailed)
    mockRetryWorkflow.mockResolvedValue(mockWorkflowInProgress)
    const onRetry = jest.fn()
    const user = userEvent.setup({ advanceTimers: jest.advanceTimersByTime })

    render(<WorkflowTimeline workflowId="test-workflow-id" onRetry={onRetry} />)

    await waitFor(() => {
      expect(screen.getByText('Retry Workflow')).toBeInTheDocument()
    })

    const retryButton = screen.getByText('Retry Workflow')
    await user.click(retryButton)

    await waitFor(() => {
      expect(onRetry).toHaveBeenCalled()
    })
  })
})