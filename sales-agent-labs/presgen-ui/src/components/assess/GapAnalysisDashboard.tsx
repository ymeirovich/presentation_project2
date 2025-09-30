'use client'

import React, { useState, useEffect } from 'react'
import { TrendingUp, TrendingDown, AlertTriangle, CheckCircle, BarChart3, PieChart, Download, Share, Brain, Target, BookOpen, Zap, Award, FileText, GraduationCap, Play } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Progress } from '@/components/ui/progress'
import { BloomTaxonomyChart } from './BloomTaxonomyChart'
import { DomainPerformanceChart } from './DomainPerformanceChart'
import { RemediationAssetsTable } from './RemediationAssetsTable'
import { GapAnalysisResult, ContentOutlineItem, RecommendedCourse } from '@/lib/assess-schemas'
import {
  fetchGapAnalysis,
  exportGapAnalysisToSheets,
  fetchContentOutlines,
  fetchRecommendedCourses,
  triggerCourseGeneration
} from '@/lib/assess-api'
import { toast } from 'sonner'

interface GapAnalysisDashboardProps {
  workflowId: string
  className?: string
  onBack?: () => void
  onExportToSheets?: () => void
}

export function GapAnalysisDashboard({
  workflowId,
  className,
  onBack,
  onExportToSheets
}: GapAnalysisDashboardProps) {
  const [gapAnalysis, setGapAnalysis] = useState<GapAnalysisResult | null>(null)
  const [contentOutlines, setContentOutlines] = useState<ContentOutlineItem[]>([])
  const [recommendedCourses, setRecommendedCourses] = useState<RecommendedCourse[]>([])
  const [loading, setLoading] = useState(true)
  const [loadingContent, setLoadingContent] = useState(false)
  const [loadingCourses, setLoadingCourses] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [exportingToSheets, setExportingToSheets] = useState(false)
  const [generatingCourses, setGeneratingCourses] = useState<Set<string>>(new Set())

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

  const fetchContentOutlinesData = async () => {
    if (contentOutlines.length > 0) return // Already loaded
    try {
      setLoadingContent(true)
      const data = await fetchContentOutlines(workflowId)
      setContentOutlines(data)
    } catch (err) {
      console.error('Failed to fetch content outlines:', err)
      toast.error('Failed to load content outlines')
    } finally {
      setLoadingContent(false)
    }
  }

  const fetchRecommendedCoursesData = async () => {
    if (recommendedCourses.length > 0) return // Already loaded
    try {
      setLoadingCourses(true)
      const data = await fetchRecommendedCourses(workflowId)
      setRecommendedCourses(data)
    } catch (err) {
      console.error('Failed to fetch recommended courses:', err)
      toast.error('Failed to load recommended courses')
    } finally {
      setLoadingCourses(false)
    }
  }

  const handleGenerateCourse = async (courseId: string) => {
    try {
      setGeneratingCourses(prev => new Set(prev).add(courseId))
      const result = await triggerCourseGeneration(courseId)

      if (result.success) {
        toast.success(`Course generation started: ${result.message}`)
        // Update the course status in state
        setRecommendedCourses(prev =>
          prev.map(course =>
            course.skill_id === courseId
              ? { ...course, generation_status: 'in_progress' }
              : course
          )
        )
      } else {
        toast.error('Failed to start course generation')
      }
    } catch (err) {
      console.error('Failed to trigger course generation:', err)
      toast.error('Failed to start course generation')
    } finally {
      setGeneratingCourses(prev => {
        const next = new Set(prev)
        next.delete(courseId)
        return next
      })
    }
  }

  useEffect(() => {
    fetchData()
  }, [workflowId])

  if (loading) {
    return (
      <div className={className}>
        {/* Header with Back Button */}
        <div className="flex justify-between items-center mb-6">
          <div>
            {onBack && (
              <Button variant="outline" size="sm" onClick={onBack}>
                ← Back to Workflows
              </Button>
            )}
          </div>
        </div>

        <Card>
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
      </div>
    )
  }

  if (error) {
    return (
      <div className={className}>
        {/* Header with Back Button */}
        <div className="flex justify-between items-center mb-6">
          <div>
            {onBack && (
              <Button variant="outline" size="sm" onClick={onBack}>
                ← Back to Workflows
              </Button>
            )}
          </div>
        </div>

        <Card>
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
      </div>
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

  // Handle Google Sheets export
  const handleExportToSheets = async () => {
    try {
      setExportingToSheets(true)
      const exportResult = await exportGapAnalysisToSheets(workflowId)

      if (exportResult.spreadsheet_url) {
        window.open(exportResult.spreadsheet_url, '_blank')
      }

      if (exportResult.success) {
        toast.success('Gap analysis exported to Google Sheets successfully!')
      } else if (exportResult.mock_response) {
        toast.warning(exportResult.message || 'Google Sheets export is running in mock mode. See instructions for enabling Sheets integration.')
      } else {
        toast.error(exportResult.message || 'Google Sheets export did not complete successfully')
      }

      if (exportResult.instructions && exportResult.instructions.length > 0) {
        console.info('Google Sheets export instructions:', exportResult.instructions.join('\n'))
      }

      onExportToSheets?.()
    } catch (error) {
      console.error('Failed to export to Google Sheets:', error)
      toast.error('Failed to export to Google Sheets')
    } finally {
      setExportingToSheets(false)
    }
  }

  // Get enhanced skill gap analysis data (when available)
  const getEnhancedSkillGapData = () => {
    // This would be populated from the enhanced gap analysis backend
    // For now, return mock data structure
    return {
      bloom_taxonomy_analysis: {
        cognitive_depth_assessment: 'developing_depth',
        knowledge_vs_application_ratio: 0.7,
        bloom_level_scores: {
          remember: 0.85,
          understand: 0.78,
          apply: 0.65,
          analyze: 0.55,
          evaluate: 0.45,
          create: 0.35
        }
      },
      learning_style_indicators: {
        best_style: 'scenario_based',
        context_switching_ability: 'good',
        retention_quality: 'strong'
      },
      metacognitive_awareness: {
        metacognitive_maturity_score: 0.68,
        self_assessment_accuracy: 'needs_improvement',
        uncertainty_recognition: 'good'
      },
      transfer_learning_assessment: {
        transfer_learning_score: 0.72,
        cross_domain_connections: 'moderate',
        pattern_recognition: 'strong'
      },
      certification_specific_insights: {
        certification_readiness_score: 73,
        exam_strategy_readiness: 'good',
        industry_context_readiness: 'moderate'
      }
    }
  }

  const enhancedData = getEnhancedSkillGapData()

  return (
    <div className={className}>
      {/* Header with Actions */}
      <div className="flex justify-between items-center mb-6">
        <div>
          {onBack && (
            <Button variant="outline" size="sm" onClick={onBack}>
              ← Back to Workflows
            </Button>
          )}
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleExportToSheets}
            disabled={exportingToSheets}
          >
            {exportingToSheets ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-2" />
                Exporting...
              </>
            ) : (
              <>
                <Download className="h-4 w-4 mr-2" />
                Export to Sheets
              </>
            )}
          </Button>
          <Button variant="outline" size="sm">
            <Share className="h-4 w-4 mr-2" />
            Share Report
          </Button>
        </div>
      </div>

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

      {/* Enhanced 5-Metric Skill Gap Analysis */}
      <Card className="mb-6">
        <CardHeader>
          <CardTitle className="text-base flex items-center gap-2">
            <Brain className="h-5 w-5 text-blue-600" />
            Enhanced Skill Gap Analysis
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 lg:grid-cols-5 gap-4">
            {/* Bloom's Taxonomy */}
            <div className="text-center p-4 border rounded-lg">
              <div className="flex items-center justify-center mb-2">
                <Brain className="h-6 w-6 text-purple-600" />
              </div>
              <div className="text-sm font-medium text-gray-600 mb-1">Cognitive Depth</div>
              <div className="text-lg font-bold capitalize">
                {enhancedData.bloom_taxonomy_analysis.cognitive_depth_assessment.replace('_', ' ')}
              </div>
              <div className="text-xs text-gray-500">
                Knowledge/App: {(enhancedData.bloom_taxonomy_analysis.knowledge_vs_application_ratio * 100).toFixed(0)}%
              </div>
            </div>

            {/* Learning Style */}
            <div className="text-center p-4 border rounded-lg">
              <div className="flex items-center justify-center mb-2">
                <BookOpen className="h-6 w-6 text-green-600" />
              </div>
              <div className="text-sm font-medium text-gray-600 mb-1">Learning Style</div>
              <div className="text-lg font-bold capitalize">
                {enhancedData.learning_style_indicators.best_style.replace('_', ' ')}
              </div>
              <div className="text-xs text-gray-500">
                Context Switch: {enhancedData.learning_style_indicators.context_switching_ability}
              </div>
            </div>

            {/* Metacognitive Awareness */}
            <div className="text-center p-4 border rounded-lg">
              <div className="flex items-center justify-center mb-2">
                <Target className="h-6 w-6 text-blue-600" />
              </div>
              <div className="text-sm font-medium text-gray-600 mb-1">Self-Awareness</div>
              <div className="text-lg font-bold">
                {Math.round(enhancedData.metacognitive_awareness.metacognitive_maturity_score * 100)}%
              </div>
              <div className="text-xs text-gray-500">
                {enhancedData.metacognitive_awareness.self_assessment_accuracy.replace('_', ' ')}
              </div>
            </div>

            {/* Transfer Learning */}
            <div className="text-center p-4 border rounded-lg">
              <div className="flex items-center justify-center mb-2">
                <Zap className="h-6 w-6 text-orange-600" />
              </div>
              <div className="text-sm font-medium text-gray-600 mb-1">Transfer Learning</div>
              <div className="text-lg font-bold">
                {Math.round(enhancedData.transfer_learning_assessment.transfer_learning_score * 100)}%
              </div>
              <div className="text-xs text-gray-500">
                Pattern Recognition: {enhancedData.transfer_learning_assessment.pattern_recognition}
              </div>
            </div>

            {/* Certification Readiness */}
            <div className="text-center p-4 border rounded-lg">
              <div className="flex items-center justify-center mb-2">
                <Award className="h-6 w-6 text-yellow-600" />
              </div>
              <div className="text-sm font-medium text-gray-600 mb-1">Cert Readiness</div>
              <div className="text-lg font-bold">
                {enhancedData.certification_specific_insights.certification_readiness_score}%
              </div>
              <div className="text-xs text-gray-500">
                Exam Strategy: {enhancedData.certification_specific_insights.exam_strategy_readiness}
              </div>
            </div>
          </div>

          {/* Progress bars for detailed metrics */}
          <div className="mt-6 space-y-3">
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>Bloom's Taxonomy Progression</span>
                <span>{Math.round(enhancedData.bloom_taxonomy_analysis.knowledge_vs_application_ratio * 100)}%</span>
              </div>
              <Progress value={enhancedData.bloom_taxonomy_analysis.knowledge_vs_application_ratio * 100} className="h-2" />
            </div>
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>Metacognitive Maturity</span>
                <span>{Math.round(enhancedData.metacognitive_awareness.metacognitive_maturity_score * 100)}%</span>
              </div>
              <Progress value={enhancedData.metacognitive_awareness.metacognitive_maturity_score * 100} className="h-2" />
            </div>
            <div>
              <div className="flex justify-between text-sm mb-1">
                <span>Transfer Learning Ability</span>
                <span>{Math.round(enhancedData.transfer_learning_assessment.transfer_learning_score * 100)}%</span>
              </div>
              <Progress value={enhancedData.transfer_learning_assessment.transfer_learning_score * 100} className="h-2" />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Charts and Analysis */}
      <Tabs defaultValue="performance" className="space-y-4">
        <TabsList className="grid w-full grid-cols-6">
          <TabsTrigger value="performance">Domain Performance</TabsTrigger>
          <TabsTrigger value="bloom">Bloom's Taxonomy</TabsTrigger>
          <TabsTrigger value="enhanced">5-Metric Analysis</TabsTrigger>
          <TabsTrigger value="content-outline" onClick={fetchContentOutlinesData}>
            Content Outline
          </TabsTrigger>
          <TabsTrigger value="courses" onClick={fetchRecommendedCoursesData}>
            Recommended Courses
          </TabsTrigger>
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

        <TabsContent value="enhanced" className="space-y-4">
          {/* Enhanced 5-Metric Detailed Analysis */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* Bloom's Taxonomy Detailed Breakdown */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <Brain className="h-4 w-4" />
                  Bloom's Taxonomy Detailed Analysis
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-3">
                  {Object.entries(enhancedData.bloom_taxonomy_analysis.bloom_level_scores).map(([level, score]) => (
                    <div key={level}>
                      <div className="flex justify-between text-sm mb-1">
                        <span className="capitalize">{level}</span>
                        <span>{Math.round(score * 100)}%</span>
                      </div>
                      <Progress value={score * 100} className="h-2" />
                    </div>
                  ))}
                </div>
              </CardContent>
            </Card>

            {/* Learning & Metacognitive Insights */}
            <Card>
              <CardHeader>
                <CardTitle className="text-sm flex items-center gap-2">
                  <Target className="h-4 w-4" />
                  Learning & Metacognitive Insights
                </CardTitle>
              </CardHeader>
              <CardContent>
                <div className="space-y-4">
                  <div>
                    <h4 className="text-sm font-medium mb-2">Learning Style Strengths</h4>
                    <Badge variant="outline" className="mr-2">
                      {enhancedData.learning_style_indicators.best_style.replace('_', ' ')}
                    </Badge>
                    <Badge variant="secondary">
                      {enhancedData.learning_style_indicators.retention_quality}
                    </Badge>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium mb-2">Self-Assessment Quality</h4>
                    <div className="text-sm text-gray-600">
                      Accuracy: <span className="font-medium">{enhancedData.metacognitive_awareness.self_assessment_accuracy.replace('_', ' ')}</span>
                    </div>
                    <div className="text-sm text-gray-600">
                      Uncertainty Recognition: <span className="font-medium">{enhancedData.metacognitive_awareness.uncertainty_recognition}</span>
                    </div>
                  </div>
                  <div>
                    <h4 className="text-sm font-medium mb-2">Transfer Learning</h4>
                    <div className="text-sm text-gray-600">
                      Cross-Domain: <span className="font-medium">{enhancedData.transfer_learning_assessment.cross_domain_connections}</span>
                    </div>
                    <div className="text-sm text-gray-600">
                      Pattern Recognition: <span className="font-medium">{enhancedData.transfer_learning_assessment.pattern_recognition}</span>
                    </div>
                  </div>
                </div>
              </CardContent>
            </Card>
          </div>

          {/* Certification-Specific Recommendations */}
          <Card>
            <CardHeader>
              <CardTitle className="text-sm flex items-center gap-2">
                <Award className="h-4 w-4" />
                Certification-Specific Recommendations
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <div>
                  <h4 className="text-sm font-medium mb-2">Exam Strategy</h4>
                  <Badge variant={enhancedData.certification_specific_insights.exam_strategy_readiness === 'good' ? 'default' : 'secondary'}>
                    {enhancedData.certification_specific_insights.exam_strategy_readiness}
                  </Badge>
                  <p className="text-xs text-gray-500 mt-1">
                    Time management and question approach
                  </p>
                </div>
                <div>
                  <h4 className="text-sm font-medium mb-2">Industry Context</h4>
                  <Badge variant={enhancedData.certification_specific_insights.industry_context_readiness === 'strong' ? 'default' : 'secondary'}>
                    {enhancedData.certification_specific_insights.industry_context_readiness}
                  </Badge>
                  <p className="text-xs text-gray-500 mt-1">
                    Real-world application readiness
                  </p>
                </div>
                <div>
                  <h4 className="text-sm font-medium mb-2">Overall Readiness</h4>
                  <Badge variant={enhancedData.certification_specific_insights.certification_readiness_score >= 80 ? 'default' : 'secondary'}>
                    {enhancedData.certification_specific_insights.certification_readiness_score}%
                  </Badge>
                  <p className="text-xs text-gray-500 mt-1">
                    Combined readiness score
                  </p>
                </div>
              </div>
            </CardContent>
          </Card>
        </TabsContent>

        <TabsContent value="content-outline" className="space-y-4">
          {loadingContent ? (
            <Card>
              <CardContent className="py-8">
                <div className="flex items-center justify-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
                  <p className="ml-3 text-sm text-muted-foreground">Loading content outlines...</p>
                </div>
              </CardContent>
            </Card>
          ) : contentOutlines.length === 0 ? (
            <Card>
              <CardContent className="py-8">
                <div className="text-center text-muted-foreground">
                  <FileText className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>No content outlines available yet</p>
                  <p className="text-sm mt-1">Content will be generated based on your skill gaps</p>
                </div>
              </CardContent>
            </Card>
          ) : (
            contentOutlines.map((outline) => (
              <Card key={outline.skill_id}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <CardTitle className="text-base flex items-center gap-2">
                        <FileText className="h-4 w-4 text-blue-600" />
                        {outline.skill_name}
                      </CardTitle>
                      <p className="text-sm text-muted-foreground mt-1">{outline.exam_domain}</p>
                    </div>
                    <Badge variant="secondary" className="ml-2">
                      RAG Score: {(outline.rag_retrieval_score * 100).toFixed(0)}%
                    </Badge>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <div>
                      <h4 className="text-sm font-medium mb-2 flex items-center gap-2">
                        <BookOpen className="h-4 w-4" />
                        Exam Guide Section
                      </h4>
                      <p className="text-sm text-gray-600 bg-gray-50 p-3 rounded">
                        {outline.exam_guide_section}
                      </p>
                    </div>

                    {outline.content_items && outline.content_items.length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium mb-2">Learning Resources</h4>
                        <div className="space-y-2">
                          {outline.content_items.map((item: any, idx: number) => (
                            <div key={idx} className="border-l-2 border-blue-600 pl-3 py-2">
                              <div className="flex items-start justify-between">
                                <div className="flex-1">
                                  <p className="text-sm font-medium">{item.topic}</p>
                                  <p className="text-xs text-muted-foreground mt-1">
                                    Source: {item.source}
                                    {item.page_ref && ` • ${item.page_ref}`}
                                  </p>
                                  {item.summary && (
                                    <p className="text-sm text-gray-600 mt-2">{item.summary}</p>
                                  )}
                                </div>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </TabsContent>

        <TabsContent value="courses" className="space-y-4">
          {loadingCourses ? (
            <Card>
              <CardContent className="py-8">
                <div className="flex items-center justify-center">
                  <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600" />
                  <p className="ml-3 text-sm text-muted-foreground">Loading recommended courses...</p>
                </div>
              </CardContent>
            </Card>
          ) : recommendedCourses.length === 0 ? (
            <Card>
              <CardContent className="py-8">
                <div className="text-center text-muted-foreground">
                  <GraduationCap className="h-12 w-12 mx-auto mb-3 opacity-50" />
                  <p>No course recommendations available yet</p>
                  <p className="text-sm mt-1">Courses will be generated based on your skill gaps</p>
                </div>
              </CardContent>
            </Card>
          ) : (
            recommendedCourses.map((course) => (
              <Card key={course.skill_id} className={course.generation_status === 'in_progress' ? 'border-blue-500' : ''}>
                <CardHeader>
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <CardTitle className="text-base flex items-center gap-2">
                        <GraduationCap className="h-4 w-4 text-purple-600" />
                        {course.course_title}
                      </CardTitle>
                      <p className="text-sm text-muted-foreground mt-1">
                        {course.skill_name} • {course.exam_domain}
                      </p>
                    </div>
                    <div className="flex items-center gap-2 ml-2">
                      <Badge
                        variant={course.priority >= 7 ? 'destructive' : course.priority >= 4 ? 'default' : 'secondary'}
                      >
                        Priority: {course.priority}/10
                      </Badge>
                      <Badge variant="outline" className="capitalize">
                        {course.difficulty_level}
                      </Badge>
                    </div>
                  </div>
                </CardHeader>
                <CardContent>
                  <div className="space-y-4">
                    <p className="text-sm text-gray-700">{course.course_description}</p>

                    <div className="flex items-center gap-4 text-sm text-muted-foreground">
                      <div className="flex items-center gap-1">
                        <Target className="h-4 w-4" />
                        <span>{course.estimated_duration_minutes} minutes</span>
                      </div>
                      <div className="flex items-center gap-1">
                        <Award className="h-4 w-4" />
                        <span className="capitalize">{course.difficulty_level}</span>
                      </div>
                    </div>

                    {course.learning_objectives && course.learning_objectives.length > 0 && (
                      <div>
                        <h4 className="text-sm font-medium mb-2">Learning Objectives</h4>
                        <ul className="space-y-1">
                          {course.learning_objectives.map((objective, idx) => (
                            <li key={idx} className="text-sm text-gray-600 flex items-start">
                              <CheckCircle className="h-4 w-4 text-green-600 mr-2 mt-0.5 flex-shrink-0" />
                              <span>{objective}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}

                    <div className="flex items-center justify-between pt-3 border-t">
                      <div className="flex items-center gap-2">
                        <Badge
                          variant={
                            course.generation_status === 'completed'
                              ? 'default'
                              : course.generation_status === 'in_progress'
                              ? 'secondary'
                              : 'outline'
                          }
                        >
                          {course.generation_status === 'completed' && 'Generated'}
                          {course.generation_status === 'in_progress' && 'Generating...'}
                          {course.generation_status === 'pending' && 'Not Generated'}
                          {course.generation_status === 'failed' && 'Failed'}
                        </Badge>
                      </div>

                      <Button
                        size="sm"
                        onClick={() => handleGenerateCourse(course.skill_id)}
                        disabled={
                          course.generation_status === 'completed' ||
                          course.generation_status === 'in_progress' ||
                          generatingCourses.has(course.skill_id)
                        }
                      >
                        {generatingCourses.has(course.skill_id) ? (
                          <>
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2" />
                            Generating...
                          </>
                        ) : course.generation_status === 'completed' ? (
                          <>
                            <CheckCircle className="h-4 w-4 mr-2" />
                            View Course
                          </>
                        ) : course.generation_status === 'in_progress' ? (
                          <>
                            <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-2" />
                            In Progress
                          </>
                        ) : (
                          <>
                            <Play className="h-4 w-4 mr-2" />
                            Generate Course
                          </>
                        )}
                      </Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
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
