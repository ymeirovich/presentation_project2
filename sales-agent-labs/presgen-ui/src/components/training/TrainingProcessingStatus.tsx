'use client'

import { useState, useEffect } from "react"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"
import { Badge } from "@/components/ui/badge"
import { TrainingVideoResponse } from "@/lib/training-schemas"
import { getTrainingStatus } from "@/lib/training-api"
import { toast } from "sonner"
import { Loader2, CheckCircle, XCircle, Clock, Zap } from "lucide-react"

interface TrainingProcessingStatusProps {
  jobId: string
  onComplete: (result: TrainingVideoResponse) => void
  className?: string
}

export function TrainingProcessingStatus({
  jobId,
  onComplete,
  className
}: TrainingProcessingStatusProps) {
  const [status, setStatus] = useState<string>("starting")
  const [progress, setProgress] = useState<number>(0)
  const [elapsedTime, setElapsedTime] = useState<number>(0)
  const [estimatedTimeRemaining, setEstimatedTimeRemaining] = useState<number | null>(null)
  const [currentPhase, setCurrentPhase] = useState<string>("Initializing...")
  const [result, setResult] = useState<TrainingVideoResponse | null>(null)

  // Simulate processing for now since we're doing synchronous processing
  useEffect(() => {
    if (!jobId) return

    let interval: NodeJS.Timeout | null = null
    let startTime = Date.now()

    // Simulate processing phases
    const phases = [
      { name: "Initializing components", duration: 2000 },
      { name: "Processing content", duration: 3000 },
      { name: "Generating voice audio", duration: 5000 },
      { name: "Creating avatar video", duration: 15000 },
      { name: "Rendering final output", duration: 8000 },
      { name: "Completing generation", duration: 2000 }
    ]

    let currentPhaseIndex = 0
    let phaseStartTime = startTime

    const updateProgress = () => {
      const now = Date.now()
      const totalElapsed = now - startTime
      setElapsedTime(Math.floor(totalElapsed / 1000))

      if (currentPhaseIndex < phases.length) {
        const phase = phases[currentPhaseIndex]
        const phaseElapsed = now - phaseStartTime
        const phaseProgress = Math.min(phaseElapsed / phase.duration, 1)

        setCurrentPhase(phase.name)

        // Calculate overall progress
        const completedPhases = currentPhaseIndex
        const currentPhaseWeight = phaseProgress
        const totalPhases = phases.length
        const overallProgress = ((completedPhases + currentPhaseWeight) / totalPhases) * 100
        setProgress(Math.min(overallProgress, 95)) // Cap at 95% until actually complete

        // Estimate remaining time
        const avgPhaseTime = totalElapsed / (currentPhaseIndex + phaseProgress)
        const remainingPhases = totalPhases - (currentPhaseIndex + phaseProgress)
        setEstimatedTimeRemaining(Math.floor((remainingPhases * avgPhaseTime) / 1000))

        if (phaseElapsed >= phase.duration) {
          currentPhaseIndex++
          phaseStartTime = now
        }
      } else {
        // Simulation complete - this would normally be replaced by actual API polling
        setProgress(100)
        setCurrentPhase("Generation complete!")
        setEstimatedTimeRemaining(0)

        // Create mock result for demonstration
        const mockResult: TrainingVideoResponse = {
          job_id: jobId,
          success: true,
          output_path: `/tmp/training_video_${jobId}.mp4`,
          processing_time: totalElapsed / 1000,
          mode: "video_only", // This would come from the original request
          total_duration: 60,
          avatar_duration: 60,
          presentation_duration: 0,
          error: null
        }

        setResult(mockResult)
        onComplete(mockResult)

        if (interval) {
          clearInterval(interval)
        }
      }
    }

    interval = setInterval(updateProgress, 500) // Update every 500ms for smooth progress

    return () => {
      if (interval) {
        clearInterval(interval)
      }
    }
  }, [jobId, onComplete])

  const formatTime = (seconds: number): string => {
    const mins = Math.floor(seconds / 60)
    const secs = seconds % 60
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const getStatusIcon = () => {
    if (result?.success) {
      return <CheckCircle className="h-5 w-5 text-green-500" />
    } else if (result?.success === false) {
      return <XCircle className="h-5 w-5 text-red-500" />
    } else {
      return <Loader2 className="h-5 w-5 animate-spin text-blue-500" />
    }
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle className="flex items-center gap-2">
          {getStatusIcon()}
          Avatar Video Generation
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-6">
        {/* Progress Bar */}
        <div className="space-y-2">
          <div className="flex justify-between text-sm">
            <span className="font-medium">{currentPhase}</span>
            <span className="text-muted-foreground">{Math.round(progress)}%</span>
          </div>
          <Progress value={progress} className="h-3" />
        </div>

        {/* Status Information */}
        <div className="grid grid-cols-2 gap-4 text-sm">
          <div className="flex items-center gap-2">
            <Clock className="h-4 w-4 text-muted-foreground" />
            <span>Elapsed:</span>
            <Badge variant="secondary">{formatTime(elapsedTime)}</Badge>
          </div>
          {estimatedTimeRemaining !== null && estimatedTimeRemaining > 0 && (
            <div className="flex items-center gap-2">
              <Zap className="h-4 w-4 text-muted-foreground" />
              <span>Remaining:</span>
              <Badge variant="outline">{formatTime(estimatedTimeRemaining)}</Badge>
            </div>
          )}
        </div>

        {/* Processing Details */}
        <div className="space-y-2">
          <h4 className="text-sm font-medium">Processing Steps:</h4>
          <div className="space-y-1 text-sm text-muted-foreground">
            <div className="flex items-center gap-2">
              <CheckCircle className="h-3 w-3 text-green-500" />
              <span>Voice profile loaded</span>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle className="h-3 w-3 text-green-500" />
              <span>Content processed</span>
            </div>
            <div className="flex items-center gap-2">
              {progress >= 50 ? (
                <CheckCircle className="h-3 w-3 text-green-500" />
              ) : (
                <Loader2 className="h-3 w-3 animate-spin" />
              )}
              <span>Avatar video generation</span>
            </div>
            <div className="flex items-center gap-2">
              {progress >= 90 ? (
                <CheckCircle className="h-3 w-3 text-green-500" />
              ) : progress >= 50 ? (
                <Loader2 className="h-3 w-3 animate-spin" />
              ) : (
                <div className="h-3 w-3 rounded-full border-2 border-muted" />
              )}
              <span>Final rendering</span>
            </div>
          </div>
        </div>

        {/* Performance Info */}
        <div className="bg-muted/50 p-3 rounded-lg">
          <div className="text-sm">
            <div className="font-medium mb-1">Hardware Optimization</div>
            <div className="text-muted-foreground">
              Processing optimized for M1 Mac with MPS acceleration
            </div>
          </div>
        </div>

        {/* Error State */}
        {result?.success === false && (
          <div className="bg-red-50 border border-red-200 p-3 rounded-lg">
            <div className="text-sm text-red-800">
              <div className="font-medium">Generation Failed</div>
              <div className="mt-1">{result.error}</div>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}