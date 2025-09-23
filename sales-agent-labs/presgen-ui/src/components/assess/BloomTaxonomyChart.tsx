'use client'

import React from 'react'
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, Legend, BarChart, Bar, XAxis, YAxis, CartesianGrid } from 'recharts'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { BloomTaxonomyLevel, BLOOM_TAXONOMY_LEVELS } from '@/lib/assess-schemas'

interface BloomTaxonomyChartProps {
  data: BloomTaxonomyLevel[]
  chartType?: 'pie' | 'bar'
  className?: string
}

interface ChartDataPoint {
  name: string
  value: number
  score: number
  color: string
  questionCount: number
  correctCount: number
}

export function BloomTaxonomyChart({
  data,
  chartType = 'bar',
  className
}: BloomTaxonomyChartProps) {
  const chartData: ChartDataPoint[] = data.map(level => {
    const taxonomyLevel = BLOOM_TAXONOMY_LEVELS.find(t => t.value === level.level)
    return {
      name: taxonomyLevel?.label || level.label,
      value: level.question_count,
      score: level.score,
      color: taxonomyLevel?.color || '#90caf9',
      questionCount: level.question_count,
      correctCount: level.correct_count,
    }
  })

  const CustomTooltip = ({ active, payload }: { active?: boolean; payload?: any[] }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload
      return (
        <div className="bg-white p-3 border border-gray-200 rounded-lg shadow-md">
          <p className="font-semibold">{data.name}</p>
          <p className="text-sm text-gray-600">
            Score: {data.score.toFixed(1)}%
          </p>
          <p className="text-sm text-gray-600">
            Questions: {data.correctCount}/{data.questionCount}
          </p>
        </div>
      )
    }
    return null
  }

  const renderPieChart = () => (
    <ResponsiveContainer width="100%" height={300}>
      <PieChart>
        <Pie
          data={chartData}
          cx="50%"
          cy="50%"
          labelLine={false}
          label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
          outerRadius={80}
          fill="#8884d8"
          dataKey="value"
        >
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Pie>
        <Tooltip content={<CustomTooltip />} />
        <Legend />
      </PieChart>
    </ResponsiveContainer>
  )

  const renderBarChart = () => (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart
        data={chartData}
        margin={{
          top: 20,
          right: 30,
          left: 20,
          bottom: 5,
        }}
      >
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis
          dataKey="name"
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
        <Bar dataKey="score" radius={[4, 4, 0, 0]}>
          {chartData.map((entry, index) => (
            <Cell key={`cell-${index}`} fill={entry.color} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  )

  const totalQuestions = chartData.reduce((sum, level) => sum + level.questionCount, 0)
  const totalCorrect = chartData.reduce((sum, level) => sum + level.correctCount, 0)
  const averageScore = totalQuestions > 0 ? (totalCorrect / totalQuestions) * 100 : 0

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="text-base">Bloom's Taxonomy Breakdown</CardTitle>
        <div className="text-sm text-muted-foreground">
          Average Score: {averageScore.toFixed(1)}% ({totalCorrect}/{totalQuestions})
        </div>
      </CardHeader>
      <CardContent>
        {chartType === 'pie' ? renderPieChart() : renderBarChart()}

        <div className="mt-4 grid grid-cols-2 lg:grid-cols-3 gap-2 text-xs">
          {chartData.map((level, index) => (
            <div key={index} className="flex items-center space-x-2">
              <div
                className="w-3 h-3 rounded-sm"
                style={{ backgroundColor: level.color }}
              />
              <span className="truncate">
                {level.name}: {level.score.toFixed(0)}%
              </span>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}