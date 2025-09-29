'use client'

import React from 'react'
import type { TooltipProps } from 'recharts'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, ScatterChart, Scatter } from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { DomainPerformance } from '@/lib/assess-schemas'

interface DomainPerformanceChartProps {
  data: DomainPerformance[]
  chartType?: 'bar' | 'scatter'
  className?: string
}

interface ChartDataPoint {
  domain: string
  displayDomain: string
  score: number
  confidence: number
  overconfidence: number
  questionCount: number
  correctCount: number
  isOverconfident: boolean
}

export function DomainPerformanceChart({
  data,
  chartType = 'bar',
  className
}: DomainPerformanceChartProps) {
  const chartData: ChartDataPoint[] = data.map(domain => {
    const truncated = domain.domain.length > 15 ? `${domain.domain.substring(0, 15)}...` : domain.domain
    return {
      domain: domain.domain,
      displayDomain: truncated,
      score: domain.score,
      confidence: domain.confidence_score,
      overconfidence: domain.overconfidence_ratio,
      questionCount: domain.question_count,
      correctCount: domain.correct_count,
      isOverconfident: domain.overconfidence_ratio > 1.2,
    }
  })

  const CustomTooltip: React.FC<TooltipProps<number, string>> = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const point = payload[0].payload as ChartDataPoint

      return (
        <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-md">
          <p className="font-semibold">{point.domain}</p>
          <p className="text-sm text-gray-600">
            Performance: {point.score.toFixed(1)}%
          </p>
          <p className="text-sm text-gray-600">
            Confidence: {point.confidence.toFixed(1)}%
          </p>
          <p className="text-sm text-gray-600">
            Questions: {point.correctCount}/{point.questionCount}
          </p>
          {point.isOverconfident && (
            <p className="text-sm text-orange-600">
              ⚠️ Overconfident (ratio: {point.overconfidence.toFixed(2)})
            </p>
          )}
        </div>
      )
    }
    return null
  }

  const renderBarChart = () => (
    <ResponsiveContainer width="100%" height={400}>
      <BarChart
        data={chartData}
        margin={{
          top: 20,
          right: 30,
          left: 20,
          bottom: 60,
        }}
      >
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          dataKey="displayDomain"
          angle={-45}
          textAnchor="end"
          height={80}
          fontSize={12}
        />
        <YAxis
          label={{ value: 'Score (%)', angle: -90, position: 'insideLeft' }}
          domain={[0, 100]}
        />
        <Tooltip content={<CustomTooltip />} />
        <Bar
          dataKey="score"
          fill="#2196f3"
          radius={[4, 4, 0, 0]}
          name="Performance Score"
        />
        <Bar
          dataKey="confidence"
          fill="#ff9800"
          radius={[4, 4, 0, 0]}
          name="Confidence Score"
          fillOpacity={0.7}
        />
      </BarChart>
    </ResponsiveContainer>
  )

  const renderScatterChart = () => (
    <ResponsiveContainer width="100%" height={400}>
      <ScatterChart
        margin={{
          top: 20,
          right: 20,
          bottom: 20,
          left: 20,
        }}
      >
        <CartesianGrid />
        <XAxis
          type="number"
          dataKey="score"
          name="Performance Score"
          domain={[0, 100]}
          label={{ value: 'Performance Score (%)', position: 'insideBottom', offset: -10 }}
        />
        <YAxis
          type="number"
          dataKey="confidence"
          name="Confidence Score"
          domain={[0, 100]}
          label={{ value: 'Confidence Score (%)', angle: -90, position: 'insideLeft' }}
        />
        <Tooltip content={<CustomTooltip />} />
        <Scatter name="Domains" data={chartData} fill="#2196f3">
          {chartData.map((entry, index) => (
            <Scatter
              key={`cell-${index}`}
              fill={entry.isOverconfident ? '#f44336' : '#2196f3'}
            />
          ))}
        </Scatter>
        {/* Reference line for ideal confidence */}
        <line x1={0} y1={0} x2={100} y2={100} stroke="#666" strokeDasharray="5,5" />
      </ScatterChart>
    </ResponsiveContainer>
  )

  const overconfidentDomains = chartData.filter(d => d.isOverconfident)
  const averageScore = chartData.length > 0 ? chartData.reduce((sum, d) => sum + d.score, 0) / chartData.length : 0
  const averageConfidence = chartData.length > 0 ? chartData.reduce((sum, d) => sum + d.confidence, 0) / chartData.length : 0

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-base">Domain Performance Analysis</CardTitle>
        <div className="flex flex-wrap gap-2 text-sm text-muted-foreground">
          <span>Avg Performance: {averageScore.toFixed(1)}%</span>
          <span>Avg Confidence: {averageConfidence.toFixed(1)}%</span>
          {overconfidentDomains.length > 0 && (
            <Badge variant="outline" className="text-orange-600 border-orange-600">
              {overconfidentDomains.length} Overconfident
            </Badge>
          )}
        </div>
      </CardHeader>
      <CardContent>
        {chartType === 'bar' ? renderBarChart() : renderScatterChart()}

        {chartType === 'scatter' && (
          <div className="mt-4 text-xs text-muted-foreground">
            <p>• Points above the diagonal line indicate overconfidence</p>
            <p>• Points below the diagonal line indicate underconfidence</p>
            <p>• Red points highlight significant overconfidence (ratio &gt; 1.2)</p>
          </div>
        )}

        {overconfidentDomains.length > 0 && (
          <div className="mt-4">
            <h4 className="text-sm font-medium mb-2">Overconfident Domains:</h4>
            <div className="flex flex-wrap gap-1">
              {overconfidentDomains.map((domain, index) => (
                <Badge key={index} variant="outline" className="text-orange-600 border-orange-600">
                  {domain.domain}
                </Badge>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}
