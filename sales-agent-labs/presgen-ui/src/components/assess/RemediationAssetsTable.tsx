'use client'

import React, { useState } from 'react'
import { Download, ExternalLink, Clock, BookOpen, Video, FileText, Wrench } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { LearningGap, GAP_SEVERITY_COLORS } from '@/lib/assess-schemas'
import { exportGapAnalysisReport } from '@/lib/assess-api'
import { toast } from 'sonner'

interface RemediationAssetsTableProps {
  workflowId: string
  gaps: LearningGap[]
  className?: string
}

const getResourceIcon = (type: string) => {
  switch (type) {
    case 'video':
      return <Video className="h-4 w-4" />
    case 'article':
      return <FileText className="h-4 w-4" />
    case 'practice':
      return <Wrench className="h-4 w-4" />
    case 'documentation':
      return <BookOpen className="h-4 w-4" />
    default:
      return <FileText className="h-4 w-4" />
  }
}

const getSeverityColor = (severity: string) => {
  return GAP_SEVERITY_COLORS[severity as keyof typeof GAP_SEVERITY_COLORS] || '#666'
}

export function RemediationAssetsTable({
  workflowId,
  gaps,
  className
}: RemediationAssetsTableProps) {
  const [exporting, setExporting] = useState(false)

  const handleExport = async (format: 'pdf' | 'csv' | 'json') => {
    try {
      setExporting(true)
      const blob = await exportGapAnalysisReport(workflowId, format)

      // Create download link
      const url = window.URL.createObjectURL(blob)
      const link = document.createElement('a')
      link.href = url
      link.download = `gap-analysis-${workflowId}.${format}`
      document.body.appendChild(link)
      link.click()
      document.body.removeChild(link)
      window.URL.revokeObjectURL(url)

      toast.success(`Report exported as ${format.toUpperCase()}`)
    } catch (error) {
      toast.error(`Failed to export report: ${error instanceof Error ? error.message : 'Unknown error'}`)
    } finally {
      setExporting(false)
    }
  }

  const totalStudyHours = gaps.reduce((sum, gap) => sum + gap.recommended_study_hours, 0)
  const totalResources = gaps.reduce((sum, gap) => sum + gap.remediation_resources.length, 0)
  const criticalGaps = gaps.filter(gap => gap.gap_severity === 'critical').length
  const highGaps = gaps.filter(gap => gap.gap_severity === 'high').length

  const prioritizedGaps = [...gaps].sort((a, b) => {
    const severityOrder = { critical: 4, high: 3, medium: 2, low: 1 }
    const aSeverity = severityOrder[a.gap_severity as keyof typeof severityOrder] || 0
    const bSeverity = severityOrder[b.gap_severity as keyof typeof severityOrder] || 0
    return bSeverity - aSeverity
  })

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">Remediation Assets & Study Plan</CardTitle>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport('pdf')}
              disabled={exporting}
            >
              <Download className="h-4 w-4 mr-2" />
              PDF
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport('csv')}
              disabled={exporting}
            >
              <Download className="h-4 w-4 mr-2" />
              CSV
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => handleExport('json')}
              disabled={exporting}
            >
              <Download className="h-4 w-4 mr-2" />
              JSON
            </Button>
          </div>
        </div>

        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 text-sm">
          <div className="text-center">
            <div className="font-semibold text-lg">{totalStudyHours.toFixed(1)}h</div>
            <div className="text-muted-foreground">Total Study Time</div>
          </div>
          <div className="text-center">
            <div className="font-semibold text-lg">{totalResources}</div>
            <div className="text-muted-foreground">Resources</div>
          </div>
          <div className="text-center">
            <div className="font-semibold text-lg text-red-600">{criticalGaps}</div>
            <div className="text-muted-foreground">Critical Gaps</div>
          </div>
          <div className="text-center">
            <div className="font-semibold text-lg text-orange-600">{highGaps}</div>
            <div className="text-muted-foreground">High Priority</div>
          </div>
        </div>
      </CardHeader>

      <CardContent>
        <div className="space-y-6">
          {prioritizedGaps.map((gap, gapIndex) => (
            <div key={gapIndex} className="border rounded-lg p-4">
              <div className="flex items-center justify-between mb-3">
                <div className="flex items-center gap-2">
                  <h3 className="font-medium">{gap.domain}</h3>
                  <Badge
                    variant="outline"
                    style={{
                      borderColor: getSeverityColor(gap.gap_severity),
                      color: getSeverityColor(gap.gap_severity),
                    }}
                  >
                    {gap.gap_severity.toUpperCase()}
                  </Badge>
                </div>
                <div className="flex items-center gap-2 text-sm text-muted-foreground">
                  <Clock className="h-4 w-4" />
                  <span>{gap.recommended_study_hours.toFixed(1)}h</span>
                </div>
              </div>

              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
                <div>
                  <h4 className="text-sm font-medium mb-2">Skills Gap</h4>
                  <div className="w-full bg-gray-200 rounded-full h-2">
                    <div
                      className="h-2 rounded-full"
                      style={{
                        width: `${gap.skill_gap}%`,
                        backgroundColor: getSeverityColor(gap.gap_severity),
                      }}
                    />
                  </div>
                  <div className="text-xs text-muted-foreground mt-1">
                    {gap.skill_gap.toFixed(1)}% gap identified
                  </div>
                </div>

                <div>
                  <h4 className="text-sm font-medium mb-2">Priority Topics</h4>
                  <div className="flex flex-wrap gap-1">
                    {gap.priority_topics.slice(0, 3).map((topic, topicIndex) => (
                      <Badge key={topicIndex} variant="secondary" className="text-xs">
                        {topic}
                      </Badge>
                    ))}
                    {gap.priority_topics.length > 3 && (
                      <Badge variant="secondary" className="text-xs">
                        +{gap.priority_topics.length - 3} more
                      </Badge>
                    )}
                  </div>
                </div>
              </div>

              <div>
                <h4 className="text-sm font-medium mb-2">Recommended Resources</h4>
                <div className="space-y-2">
                  {gap.remediation_resources.map((resource, resourceIndex) => (
                    <div
                      key={resourceIndex}
                      className="flex items-center justify-between p-2 bg-gray-50 rounded border"
                    >
                      <div className="flex items-center gap-2 flex-1 min-w-0">
                        {getResourceIcon(resource.type)}
                        <div className="flex-1 min-w-0">
                          <div className="font-medium text-sm truncate">
                            {resource.title}
                          </div>
                          <div className="text-xs text-muted-foreground capitalize">
                            {resource.type} • {resource.estimated_time_minutes} min
                          </div>
                        </div>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => window.open(resource.url, '_blank')}
                        className="flex-shrink-0"
                      >
                        <ExternalLink className="h-4 w-4" />
                      </Button>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ))}
        </div>

        {gaps.length === 0 && (
          <div className="text-center py-8 text-muted-foreground">
            <BookOpen className="h-12 w-12 mx-auto mb-4 opacity-50" />
            <p>No significant learning gaps identified.</p>
            <p className="text-sm">Great job on your assessment performance!</p>
          </div>
        )}
      </CardContent>
    </Card>
  )
}