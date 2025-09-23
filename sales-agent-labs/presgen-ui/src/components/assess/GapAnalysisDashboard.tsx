'use client'

import React, { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, AlertTriangle, CheckCircle, BarChart3, PieChart } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { BloomTaxonomyChart } from './BloomTaxonomyChart'
import { DomainPerformanceChart } from './DomainPerformanceChart'
import { RemediationAssetsTable } from './RemediationAssetsTable'
import { GapAnalysisResult } from '@/lib/assess-schemas'
import { fetchGapAnalysis } from '@/lib/assess-api'

interface GapAnalysisDashboardProps {
  workflowId: string
  className?: string
  onBack?: () => void
}

export function GapAnalysisDashboard({
  workflowId,
  className,
  onBack
}: GapAnalysisDashboardProps) {
  const [gapAnalysis, setGapAnalysis] = useState<GapAnalysisResult | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const fetchData = async () => {
    try {
      setError(null)
      const data = await fetchGapAnalysis(workflowId)
      setGapAnalysis(data)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch gap analysis')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [workflowId])

  if (loading) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="text-base">Gap Analysis Dashboard</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="text-center space-y-2">
              <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mx-auto" />
              <p className="text-sm text-muted-foreground">Loading gap analysis...</p>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (error) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="text-base">Gap Analysis Dashboard</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <div className="text-center space-y-2">
              <AlertTriangle className="h-8 w-8 text-red-600 mx-auto" />
              <p className="text-sm text-red-600">{error}</p>
              <Button variant="outline" size="sm" onClick={fetchData}>
                Try Again
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>
    )
  }

  if (!gapAnalysis) {
    return (
      <Card className={className}>
        <CardHeader>
          <CardTitle className="text-base">Gap Analysis Dashboard</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-center py-8">
            <p className="text-sm text-muted-foreground">No gap analysis data available</p>
          </div>
        </CardContent>
      </Card>
    )
  }

  const getOverallPerformanceIcon = () => {
    if (gapAnalysis.overall_score >= 80) {
      return <CheckCircle className="h-5 w-5 text-green-600" />
    } else if (gapAnalysis.overall_score >= 60) {
      return <TrendingUp className="h-5 w-5 text-yellow-600" />
    } else {
      return <TrendingDown className="h-5 w-5 text-red-600" />
    }
  }

  const getConfidenceIndicator = () => {
    const confidenceDiff = gapAnalysis.overall_confidence - gapAnalysis.overall_score
    if (Math.abs(confidenceDiff) <= 10) {
      return { text: 'Well Calibrated', color: 'text-green-600', icon: CheckCircle }
    } else if (confidenceDiff > 10) {
      return { text: 'Overconfident', color: 'text-orange-600', icon: AlertTriangle }
    } else {
      return { text: 'Underconfident', color: 'text-blue-600', icon: TrendingDown }
    }
  }

  const confidenceIndicator = getConfidenceIndicator()
  const ConfidenceIcon = confidenceIndicator.icon

  const criticalGaps = gapAnalysis.learning_gaps.filter(gap => gap.gap_severity === 'critical')
  const highGaps = gapAnalysis.learning_gaps.filter(gap => gap.gap_severity === 'high')

  return (
    <div className={className}>
      {onBack && (
        <div className="mb-4">
          <Button variant="outline" size="sm" onClick={onBack}>
            ← Back to Workflows
          </Button>
        </div>
      )}

      {/* Overall Performance Summary */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-base">Assessment Performance Summary</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            <div className="text-center">
              <div className="flex items-center justify-center mb-2">
                {getOverallPerformanceIcon()}
                <span className="ml-2 text-2xl font-bold">
                  {gapAnalysis.overall_score.toFixed(1)}%
                </span>
              </div>
              <div className="text-sm text-muted-foreground">Overall Score</div>
            </div>

            <div className="text-center">
              <div className="flex items-center justify-center mb-2">
                <ConfidenceIcon className={`h-5 w-5 ${confidenceIndicator.color}`} />
                <span className="ml-2 text-2xl font-bold">
                  {gapAnalysis.overall_confidence.toFixed(1)}%
                </span>
              </div>
              <div className="text-sm text-muted-foreground">Confidence</div>
              <div className={`text-xs ${confidenceIndicator.color}`}>
                {confidenceIndicator.text}
              </div>
            </div>

            <div className="text-center">
              <div className="text-2xl font-bold text-red-600 mb-2">
                {criticalGaps.length}
              </div>
              <div className="text-sm text-muted-foreground">Critical Gaps</div>
            </div>

            <div className="text-center">
              <div className="text-2xl font-bold text-orange-600 mb-2">
                {gapAnalysis.recommended_study_plan.total_estimated_hours.toFixed(1)}h
              </div>
              <div className="text-sm text-muted-foreground">Study Time</div>
            </div>
          </div>

          {gapAnalysis.overconfidence_indicator && (
            <div className="mt-4 p-3 bg-orange-50 border border-orange-200 rounded-lg">
              <div className="flex items-center space-x-2 text-orange-800">
                <AlertTriangle className="h-4 w-4" />
                <span className="text-sm font-medium">
                  Overconfidence detected. Consider reviewing areas where confidence exceeds performance.
                </span>
              </div>
            </div>
          )}

          {criticalGaps.length > 0 && (
            <div className="mt-4 p-3 bg-red-50 border border-red-200 rounded-lg">
              <div className="flex items-center space-x-2 text-red-800">
                <AlertTriangle className="h-4 w-4" />
                <span className="text-sm font-medium">
                  {criticalGaps.length} critical learning gap{criticalGaps.length > 1 ? 's' : ''} identified.
                  Priority domains: {criticalGaps.map(g => g.domain).join(', ')}
                </span>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Charts and Analysis */}
      <Tabs defaultValue="performance" className="space-y-4">
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="performance">Domain Performance</TabsTrigger>
          <TabsTrigger value="bloom">Bloom's Taxonomy</TabsTrigger>
          <TabsTrigger value="assets">Study Plan</TabsTrigger>
        </TabsList>

        <TabsContent value="performance" className="space-y-4">
          <DomainPerformanceChart data={gapAnalysis.domain_performance} chartType="bar" />
          <DomainPerformanceChart
            data={gapAnalysis.domain_performance}
            chartType="scatter"
            className="mt-4"
          />
        </TabsContent>

        <TabsContent value="bloom" className="space-y-4">
          <BloomTaxonomyChart data={gapAnalysis.bloom_taxonomy_breakdown} chartType="bar" />
          <BloomTaxonomyChart
            data={gapAnalysis.bloom_taxonomy_breakdown}
            chartType="pie"
            className="mt-4"
          />
        </TabsContent>

        <TabsContent value="assets">
          <RemediationAssetsTable
            workflowId={workflowId}
            gaps={gapAnalysis.learning_gaps}
          />
        </TabsContent>
      </Tabs>

      {/* Study Plan Summary */}
      <Card className="mt-6">
        <CardHeader>
          <CardTitle className="text-base">Recommended Study Sequence</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="space-y-3">
            <div className="flex flex-wrap gap-2">
              <span className="text-sm font-medium">Priority Domains:</span>
              {gapAnalysis.recommended_study_plan.priority_domains.map((domain, index) => (
                <Badge key={index} variant="outline">
                  {domain}
                </Badge>
              ))}
            </div>

            <div className="flex flex-wrap gap-2">
              <span className="text-sm font-medium">Study Sequence:</span>
              {gapAnalysis.recommended_study_plan.study_sequence.map((topic, index) => (
                <Badge key={index} variant="secondary" className="text-xs">
                  {index + 1}. {topic}
                </Badge>
              ))}
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  )
}