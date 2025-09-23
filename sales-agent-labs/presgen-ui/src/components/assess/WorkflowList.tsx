'use client'

import { useState, useEffect } from 'react'
import { Search, Filter, ChevronDown, RefreshCw, Calendar, User } from 'lucide-react'
import { cn } from '@/lib/utils'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { WorkflowDetail } from '@/lib/assess-schemas'
import { fetchWorkflows } from '@/lib/assess-api'
import { WorkflowTimeline } from './WorkflowTimeline'

interface WorkflowListProps {
  className?: string
  onWorkflowSelect?: (workflow: WorkflowDetail) => void
}

const STATUS_FILTERS = [
  { value: '', label: 'All Workflows' },
  { value: 'pending', label: 'Pending' },
  { value: 'in_progress', label: 'In Progress' },
  { value: 'completed', label: 'Completed' },
  { value: 'failed', label: 'Failed' },
  { value: 'awaiting_completion', label: 'Awaiting Completion' },
]

function getStatusColor(status: string) {
  switch (status) {
    case 'completed':
      return 'bg-green-100 text-green-800 border-green-200'
    case 'failed':
      return 'bg-red-100 text-red-800 border-red-200'
    case 'in_progress':
      return 'bg-blue-100 text-blue-800 border-blue-200'
    case 'awaiting_completion':
      return 'bg-yellow-100 text-yellow-800 border-yellow-200'
    default:
      return 'bg-gray-100 text-gray-600 border-gray-200'
  }
}

function formatDate(dateString: string) {
  return new Date(dateString).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

export function WorkflowList({ className, onWorkflowSelect }: WorkflowListProps) {
  const [workflows, setWorkflows] = useState<WorkflowDetail[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [searchTerm, setSearchTerm] = useState('')
  const [statusFilter, setStatusFilter] = useState('')
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(null)

  const fetchData = async () => {
    try {
      setError(null)
      const data = await fetchWorkflows({
        status_filter: statusFilter || undefined,
        limit: 50,
      })
      setWorkflows(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch workflows')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [statusFilter]) // fetchData is stable function

  useEffect(() => {
    // Poll for updates every 30 seconds
    const interval = setInterval(fetchData, 30000)
    return () => clearInterval(interval)
  }, [statusFilter]) // fetchData is stable function

  const filteredWorkflows = workflows.filter(workflow => {
    if (!searchTerm) return true

    const search = searchTerm.toLowerCase()
    const title = workflow.parameters?.title as string || ''

    return (
      title.toLowerCase().includes(search) ||
      workflow.id.toLowerCase().includes(search) ||
      workflow.user_id.toLowerCase().includes(search) ||
      workflow.current_step.toLowerCase().includes(search)
    )
  })

  const handleWorkflowClick = (workflow: WorkflowDetail) => {
    setSelectedWorkflow(workflow.id)
    onWorkflowSelect?.(workflow)
  }

  if (selectedWorkflow) {
    return (
      <div className={className}>
        <div className="mb-4">
          <Button
            variant="outline"
            size="sm"
            onClick={() => setSelectedWorkflow(null)}
          >
            ← Back to List
          </Button>
        </div>
        <WorkflowTimeline
          workflowId={selectedWorkflow}
          onRetry={() => {
            fetchData() // Refresh the list when a workflow is retried
          }}
        />
      </div>
    )
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Recent Workflows</CardTitle>
          <Button variant="outline" size="sm" onClick={fetchData} disabled={loading}>
            <RefreshCw className={cn("h-4 w-4", loading && "animate-spin")} />
          </Button>
        </div>

        <div className="flex flex-col sm:flex-row gap-2">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-muted-foreground" />
            <Input
              placeholder="Search workflows..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="pl-9"
            />
          </div>

          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="outline" size="sm">
                <Filter className="h-4 w-4 mr-2" />
                {STATUS_FILTERS.find(f => f.value === statusFilter)?.label || 'All Workflows'}
                <ChevronDown className="h-4 w-4 ml-2" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              {STATUS_FILTERS.map((filter) => (
                <DropdownMenuItem
                  key={filter.value}
                  onClick={() => setStatusFilter(filter.value)}
                >
                  {filter.label}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </CardHeader>

      <CardContent>
        {loading && workflows.length === 0 ? (
          <div className="flex items-center justify-center py-8">
            <div className="text-center space-y-2">
              <RefreshCw className="h-6 w-6 animate-spin mx-auto text-muted-foreground" data-testid="loading-spinner" />
              <p className="text-sm text-muted-foreground">Loading workflows...</p>
            </div>
          </div>
        ) : error ? (
          <div className="flex items-center justify-center py-8">
            <div className="text-center space-y-2">
              <p className="text-sm text-red-600">{error}</p>
              <Button variant="outline" size="sm" onClick={fetchData}>
                Try Again
              </Button>
            </div>
          </div>
        ) : filteredWorkflows.length === 0 ? (
          <div className="flex items-center justify-center py-8">
            <p className="text-sm text-muted-foreground">
              {searchTerm ? 'No workflows match your search.' : 'No workflows found.'}
            </p>
          </div>
        ) : (
          <div className="space-y-3">
            {filteredWorkflows.map((workflow) => {
              const title = workflow.parameters?.title as string || 'Untitled Assessment'
              const isInProgress = workflow.execution_status === 'in_progress'

              return (
                <div
                  key={workflow.id}
                  onClick={() => handleWorkflowClick(workflow)}
                  className="p-4 border rounded-lg hover:bg-gray-50 cursor-pointer transition-colors"
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center space-x-2 mb-2">
                        <h3 className="font-medium text-sm truncate">{title}</h3>
                        <Badge
                          variant="outline"
                          className={cn("text-xs", getStatusColor(workflow.execution_status))}
                        >
                          {workflow.execution_status}
                        </Badge>
                      </div>

                      <div className="flex items-center space-x-4 text-xs text-muted-foreground">
                        <div className="flex items-center space-x-1">
                          <User className="h-3 w-3" />
                          <span>{workflow.user_id}</span>
                        </div>
                        <div className="flex items-center space-x-1">
                          <Calendar className="h-3 w-3" />
                          <span>{formatDate(workflow.created_at)}</span>
                        </div>
                      </div>

                      <div className="mt-2">
                        <div className="flex items-center justify-between text-xs">
                          <span className="text-muted-foreground">
                            Current: {workflow.current_step.replace(/_/g, ' ')}
                          </span>
                          {workflow.progress > 0 && (
                            <span className="text-muted-foreground">{workflow.progress}%</span>
                          )}
                        </div>
                        {workflow.progress > 0 && (
                          <div className="w-full bg-gray-200 rounded-full h-1.5 mt-1">
                            <div
                              className={cn(
                                "h-1.5 rounded-full transition-all duration-300",
                                isInProgress ? "bg-blue-600" : "bg-green-600"
                              )}
                              style={{ width: `${workflow.progress}%` }}
                            />
                          </div>
                        )}
                      </div>
                    </div>

                    {isInProgress && (
                      <RefreshCw className="h-4 w-4 text-blue-600 animate-spin ml-2 flex-shrink-0" />
                    )}
                  </div>

                  {workflow.error_message && (
                    <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
                      {workflow.error_message}
                    </div>
                  )}
                </div>
              )
            })}
          </div>
        )}
      </CardContent>
    </Card>
  )
}