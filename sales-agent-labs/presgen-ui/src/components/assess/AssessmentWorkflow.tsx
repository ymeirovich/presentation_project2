'use client'

import { useState } from 'react'
import { AssessmentForm } from './AssessmentForm'
import { WorkflowList } from './WorkflowList'
import { GapAnalysisDashboard } from './GapAnalysisDashboard'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'
import { WorkflowDetail } from '@/lib/assess-schemas'

interface AssessmentWorkflowProps {
  className?: string
}

export function AssessmentWorkflow({ className }: AssessmentWorkflowProps) {
  const [selectedWorkflow, setSelectedWorkflow] = useState<WorkflowDetail | null>(null)
  const [showGapAnalysis, setShowGapAnalysis] = useState(false)

  const handleWorkflowSelect = (workflow: WorkflowDetail) => {
    setSelectedWorkflow(workflow)
    // Show gap analysis if workflow is completed
    if (workflow.execution_status === 'completed') {
      setShowGapAnalysis(true)
    }
  }

  const handleBackToWorkflows = () => {
    setSelectedWorkflow(null)
    setShowGapAnalysis(false)
  }

  if (showGapAnalysis && selectedWorkflow) {
    return (
      <div className={className}>
        <GapAnalysisDashboard
          workflowId={selectedWorkflow.id}
          onBack={handleBackToWorkflows}
        />
      </div>
    )
  }

  return (
    <div className={cn('grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]', className)}>
      <div className="space-y-6">
        <AssessmentForm />
      </div>

      <aside className="space-y-6">
        <WorkflowList onWorkflowSelect={handleWorkflowSelect} />

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Gap Analysis & Assets</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>
              Complete an assessment workflow to access detailed gap analysis, domain performance
              charts, Bloom's taxonomy breakdown, and personalized remediation assets.
            </p>
            <div className="flex flex-wrap gap-1 mt-2">
              <span className="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded">
                📊 Performance Charts
              </span>
              <span className="text-xs bg-green-50 text-green-700 px-2 py-1 rounded">
                📚 Study Plans
              </span>
              <span className="text-xs bg-orange-50 text-orange-700 px-2 py-1 rounded">
                📈 Gap Analysis
              </span>
            </div>
          </CardContent>
        </Card>
      </aside>
    </div>
  )
}
