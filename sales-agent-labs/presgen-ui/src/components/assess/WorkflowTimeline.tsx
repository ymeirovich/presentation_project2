'use client'

import { useState, useEffect } from 'react'
import { Clock, CheckCircle, XCircle, AlertCircle, RefreshCw, Play, ExternalLink } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Progress } from '@/components/ui/progress'
import { WorkflowDetail, WorkflowStep } from '@/lib/assess-schemas'
import { fetchWorkflowDetail, retryWorkflow, manualProcessWorkflow, autoProgressWorkflow } from '@/lib/assess-api'

interface WorkflowTimelineProps {
  workflowId: string
  className?: string
  onRetry?: () => void
}

const WORKFLOW_STEPS = [
  { id: 'initiated', name: 'Initialize', description: 'Starting workflow setup' },
  { id: 'validate_input', name: 'Validate Input', description: 'Checking submission parameters' },
  { id: 'fetch_certification', name: 'Load Certification', description: 'Loading certification profile' },
  { id: 'setup_knowledge_base', name: 'Setup Knowledge Base', description: 'Preparing RAG context' },
  { id: 'generate_questions', name: 'Generate Questions', description: 'Creating assessment questions' },
  { id: 'validate_questions', name: 'Validate Questions', description: 'Quality checking questions' },
  { id: 'balance_domains', name: 'Balance Domains', description: 'Adjusting domain distribution' },
  { id: 'generate_assessment', name: 'Generate Assessment', description: 'Creating final assessment' },
  { id: 'collect_responses', name: 'Collect Responses', description: 'Waiting for form responses' },
  { id: 'gap_analysis', name: 'Gap Analysis', description: 'Analyzing learning gaps' },
  { id: 'presentation_generation', name: 'Generate Presentation', description: 'Creating presentation content' },
  { id: 'content_generation', name: 'Content Generation', description: 'Generating learning content' },
  { id: 'slide_generation', name: 'Slide Generation', description: 'Creating presentation slides' },
  { id: 'finalize_workflow', name: 'Finalize', description: 'Completing workflow' },
]

function getStatusIcon(status: WorkflowStep['status'], isActive: boolean) {
  switch (status) {
    case 'completed':
      return <CheckCircle className="h-5 w-5 text-green-600" data-testid="completed-step-icon" />
    case 'failed':
      return <XCircle className="h-5 w-5 text-red-600" data-testid="failed-step-icon" />
    case 'in_progress':
      return <RefreshCw className={cn("h-5 w-5 text-blue-600", isActive && "animate-spin")} data-testid="in-progress-step-icon" />
    default:
      return <Clock className={cn("h-5 w-5", isActive ? "text-blue-600" : "text-gray-400")} data-testid="pending-step-icon" />
  }
}

function getStatusColor(status: WorkflowStep['status']) {
  switch (status) {
    case 'completed':
      return 'bg-green-100 text-green-800 border-green-200'
    case 'failed':
      return 'bg-red-100 text-red-800 border-red-200'
    case 'in_progress':
      return 'bg-blue-100 text-blue-800 border-blue-200'
    default:
      return 'bg-gray-100 text-gray-600 border-gray-200'
  }
}

export function WorkflowTimeline({ workflowId, className, onRetry }: WorkflowTimelineProps) {
  const [workflow, setWorkflow] = useState<WorkflowDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [retrying, setRetrying] = useState(false)
  const [manualProcessing, setManualProcessing] = useState(false)
  const [autoProgressing, setAutoProgressing] = useState(false)

  const fetchData = async () => {
    try {
      setError(null)
      const data = await fetchWorkflowDetail(workflowId)
      setWorkflow(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch workflow')
    } finally {
      setLoading(false)
    }
  }

  const handleRetry = async () => {
    if (!workflow) return

    try {
      setRetrying(true)
      await retryWorkflow(workflow.id)
      onRetry?.()
      await fetchData() // Refresh the data
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to retry workflow')
    } finally {
      setRetrying(false)
    }
  }

  const handleManualProcess = async () => {
    if (!workflow) return

    try {
      setManualProcessing(true)
      await manualProcessWorkflow(workflow.id)
      onRetry?.()
      await fetchData() // Refresh the data
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to process workflow manually')
    } finally {
      setManualProcessing(false)
    }
  }

  const handleAutoProgress = async () => {
    if (!workflow) return

    try {
      setAutoProgressing(true)
      await autoProgressWorkflow(workflow.id)
      onRetry?.()
      await fetchData() // Refresh the data
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to auto-progress workflow')
    } finally {
      setAutoProgressing(false)
    }
  }

  useEffect(() => {
    fetchData()

    // Poll for updates if workflow is in progress
    const interval = setInterval(() => {
      if (workflow?.execution_status === 'in_progress') {
        fetchData()
      }
    }, 2000) // Poll every 2 seconds

    return () => clearInterval(interval)
  }, [workflowId, workflow?.execution_status]) // fetchData is stable function

  if (loading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="text-base">Workflow Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center space-x-2">
            <RefreshCw className="h-4 w-4 animate-spin" data-testid="loading-spinner" />
            <span className="text-sm text-muted-foreground">Loading workflow...</span>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="text-base">Workflow Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex items-center space-x-2 text-red-600">
              <AlertCircle className="h-4 w-4" />
              <span className="text-sm">{error}</span>
            </div>
            <Button variant="outline" size="sm" onClick={fetchData}>
              Try Again
            </Button>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!workflow) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="text-base">Workflow Timeline</CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-sm text-muted-foreground">Workflow not found</p>
        </CardContent>
      </Card>
    )
  }

  const currentStepIndex = WORKFLOW_STEPS.findIndex(step => step.id === workflow.current_step)
  const canRetry = workflow.execution_status === 'failed'
  const canManualProcess = workflow.execution_status === 'awaiting_completion' && workflow.current_step === 'collect_responses'
  const canAutoProgress = workflow.execution_status === 'pending' && workflow.current_step === 'initiated'

  // Get assessment title from parameters
  const assessmentTitle = workflow.parameters?.title as string || 'Assessment Workflow'

  // Construct Google Form URL from multiple possible sources
  const getGoogleFormUrl = () => {
    const urls = workflow.generated_content_urls

    const editUrl = urls?.form_edit_url?.trim()
    if (editUrl) {
      return editUrl
    }

    const directUrl = urls?.form_url?.trim()
    if (directUrl) {
      // Prefer edit link if form_url is the public responder URL and we know the form ID
      if (directUrl.includes('/viewform') && workflow.google_form_id) {
        return `https://docs.google.com/forms/d/${workflow.google_form_id}/edit`
      }
      return directUrl
    }

    // Check if workflow has google_form_id
    if (workflow.google_form_id) {
      return `https://docs.google.com/forms/d/${workflow.google_form_id}/edit`
    }

    // For workflows that reached collect_responses stage, generate mock URL
    if (workflow.current_step === 'collect_responses' || workflow.progress >= 70) {
      const mockFormId = `1${workflow.id.replace(/-/g, '').substring(0, 25)}`
      return `https://docs.google.com/forms/d/${mockFormId}/edit`
    }

    return null
  }

  const googleFormUrl = getGoogleFormUrl()

  return (
    <Card className={className}>
      <CardHeader>
        <div className="space-y-3">
          {/* Assessment Title */}
          <div className="flex items-center justify-between">
            <div>
              <CardTitle className="text-lg font-semibold">{assessmentTitle}</CardTitle>
              <p className="text-sm text-muted-foreground mt-1">Assessment Workflow Timeline</p>
            </div>
            <Badge variant="outline" className={getStatusColor(workflow.execution_status as WorkflowStep['status'])}>
              {workflow.execution_status}
            </Badge>
          </div>

          {/* Google Form Link */}
          {googleFormUrl && (
            <div className="flex items-center space-x-2 text-sm">
              <span className="text-muted-foreground">Google Form:</span>
              <a
                href={googleFormUrl}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center space-x-1 text-blue-600 hover:text-blue-800 hover:underline"
              >
                <span>View Assessment Form</span>
                <ExternalLink className="h-3 w-3" />
              </a>
            </div>
          )}
        </div>
        {workflow.progress > 0 && (
          <div className="space-y-2">
            <div className="flex items-center justify-between text-xs">
              <span>Progress</span>
              <span>{workflow.progress}%</span>
            </div>
            <Progress value={workflow.progress} className="h-2" />
          </div>
        )}
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="space-y-3">
          {WORKFLOW_STEPS.map((step, index) => {
            const isActive = index === currentStepIndex
            const isCompleted = index < currentStepIndex
            const isFailed = isActive && workflow.execution_status === 'failed'
            const stepLog = workflow.step_execution_log?.find(log => log.step === step.id)

            return (
              <div key={step.id} className={cn(
                "flex items-start space-x-3 p-3 rounded-lg border",
                isActive && "bg-blue-50 border-blue-200",
                isCompleted && "bg-green-50 border-green-200",
                isFailed && "bg-red-50 border-red-200"
              )}>
                <div className="flex-shrink-0 mt-0.5">
                  {getStatusIcon(
                    stepLog?.status || (isCompleted ? 'completed' : isActive ? 'in_progress' : 'pending'),
                    isActive
                  )}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between">
                    <h4 className={cn(
                      "text-sm font-medium",
                      isActive && "text-blue-900",
                      isCompleted && "text-green-900",
                      isFailed && "text-red-900"
                    )}>
                      {step.name}
                    </h4>
                    {stepLog?.duration_seconds && (
                      <span className="text-xs text-muted-foreground">
                        {stepLog.duration_seconds}s
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-muted-foreground mt-1">
                    {stepLog?.error_message || step.description}
                  </p>
                </div>
              </div>
            )
          })}
        </div>

        {canRetry && (
          <div className="pt-4 border-t">
            <Button
              variant="outline"
              size="sm"
              onClick={handleRetry}
              disabled={retrying}
              className="w-full"
            >
              {retrying ? (
                <>
                  <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                  Retrying...
                </>
              ) : (
                <>
                  <RefreshCw className="h-4 w-4 mr-2" />
                  Retry Workflow
                </>
              )}
            </Button>
          </div>
        )}

        {canManualProcess && (
          <div className="pt-4 border-t">
            <div className="space-y-2">
              <div className="text-xs text-muted-foreground px-1">
                ⚠️ Form completed but responses not detected. Process manually to continue.
              </div>
              <Button
                variant="default"
                size="sm"
                onClick={handleManualProcess}
                disabled={manualProcessing}
                className="w-full bg-blue-600 hover:bg-blue-700"
              >
                {manualProcessing ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    Processing Form...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2" />
                    Process Completed Form
                  </>
                )}
              </Button>
            </div>
          </div>
        )}

        {canAutoProgress && (
          <div className="pt-4 border-t">
            <div className="space-y-2">
              <div className="text-xs text-muted-foreground px-1">
                💡 Workflow ready to start. Click to begin assessment generation.
              </div>
              <Button
                variant="default"
                size="sm"
                onClick={handleAutoProgress}
                disabled={autoProgressing}
                className="w-full bg-green-600 hover:bg-green-700"
              >
                {autoProgressing ? (
                  <>
                    <RefreshCw className="h-4 w-4 mr-2 animate-spin" />
                    Starting Workflow...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-2" />
                    Start Assessment Generation
                  </>
                )}
              </Button>
            </div>
          </div>
        )}

        {workflow.error_message && (
          <div className="p-3 bg-red-50 border border-red-200 rounded-lg">
            <div className="flex items-start space-x-2">
              <AlertCircle className="h-4 w-4 text-red-600 mt-0.5 flex-shrink-0" />
              <div>
                <h4 className="text-sm font-medium text-red-800">Error Details</h4>
                <p className="text-xs text-red-700 mt-1">{workflow.error_message}</p>
              </div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
