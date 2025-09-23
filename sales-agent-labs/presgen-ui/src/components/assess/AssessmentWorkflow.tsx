'use client'

import { AssessmentForm } from './AssessmentForm'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { cn } from '@/lib/utils'

interface AssessmentWorkflowProps {
  className?: string
}

export function AssessmentWorkflow({ className }: AssessmentWorkflowProps) {
  return (
    <div className={cn('grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]', className)}>
      <div className="space-y-6">
        <AssessmentForm />
      </div>

      <aside className="space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Recent Workflows</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>
              Workflow history, status timelines, and retry controls will surface here in
              Phase&nbsp;3 of the UI rollout. For now, submitted assessments can be tracked via
              the backend API or observability dashboards.
            </p>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle className="text-base">Gap Analysis Preview</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2 text-sm text-muted-foreground">
            <p>
              Gap dashboards, remediation exports, and generated assets panels are planned for
              upcoming sprints. The current form focuses on kicking off assessment workflows.
            </p>
          </CardContent>
        </Card>
      </aside>
    </div>
  )
}
