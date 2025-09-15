'use client'

import { useState, useEffect } from "react"
import { TrainingForm } from "./TrainingForm"
import { TrainingProcessingStatus } from "./TrainingProcessingStatus"
import { VoiceProfileManager } from "./VoiceProfileManager"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Badge } from "@/components/ui/badge"
import { TrainingVideoResponse } from "@/lib/training-schemas"
import { toast } from "sonner"
import { ArrowRight, Download, Loader2, Settings, User, Video, Presentation, PlayCircle } from "lucide-react"
import { cn } from "@/lib/utils"

type WorkflowStep =
  | 'setup'       // Initial form and voice profile setup
  | 'processing'  // Video generation in progress
  | 'complete'    // Generated video ready for download

interface TrainingWorkflowProps {
  className?: string
}

export function TrainingWorkflow({ className }: TrainingWorkflowProps) {
  const [currentStep, setCurrentStep] = useState<WorkflowStep>('setup')
  const [currentJobId, setCurrentJobId] = useState<string>('')
  const [processingResult, setProcessingResult] = useState<TrainingVideoResponse | null>(null)
  const [isProcessing, setIsProcessing] = useState(false)

  // Handle job creation from form submission
  const handleJobCreated = (jobId: string) => {
    setCurrentJobId(jobId)
    setCurrentStep('processing')
    setIsProcessing(true)
  }

  // Handle processing completion
  const handleProcessingComplete = (result: TrainingVideoResponse) => {
    setProcessingResult(result)
    setCurrentStep('complete')
    setIsProcessing(false)

    if (result.success) {
      toast.success("Avatar video generated successfully!")
    } else {
      toast.error(`Generation failed: ${result.error}`)
    }
  }

  // Reset workflow to start over
  const handleStartOver = () => {
    setCurrentStep('setup')
    setCurrentJobId('')
    setProcessingResult(null)
    setIsProcessing(false)
  }

  const renderStepContent = () => {
    switch (currentStep) {
      case 'setup':
        return (
          <div className="space-y-6">
            <TrainingForm onJobCreated={handleJobCreated} />
            <div className="border-t my-6" />
            <VoiceProfileManager />
          </div>
        )

      case 'processing':
        return (
          <TrainingProcessingStatus
            jobId={currentJobId}
            onComplete={handleProcessingComplete}
          />
        )

      case 'complete':
        return (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2">
                <PlayCircle className="h-5 w-5 text-green-500" />
                Video Generation Complete
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {processingResult && (
                <>
                  <div className="grid grid-cols-2 gap-4 text-sm">
                    <div>
                      <span className="font-medium">Mode:</span>
                      <Badge variant="secondary" className="ml-2">
                        {processingResult.mode}
                      </Badge>
                    </div>
                    <div>
                      <span className="font-medium">Processing Time:</span>
                      <span className="ml-2">
                        {processingResult.processing_time
                          ? `${Math.round(processingResult.processing_time)}s`
                          : 'N/A'
                        }
                      </span>
                    </div>
                    <div>
                      <span className="font-medium">Total Duration:</span>
                      <span className="ml-2">
                        {processingResult.total_duration
                          ? `${Math.round(processingResult.total_duration)}s`
                          : 'N/A'
                        }
                      </span>
                    </div>
                    <div>
                      <span className="font-medium">Status:</span>
                      <Badge variant={processingResult.success ? "default" : "destructive"} className="ml-2">
                        {processingResult.success ? "Success" : "Failed"}
                      </Badge>
                    </div>
                  </div>

                  {processingResult.success && processingResult.output_path && (
                    <div className="flex gap-2">
                      <Button
                        variant="default"
                        className="flex-1"
                        onClick={() => {
                          // TODO: Implement download functionality
                          toast.info("Download functionality coming soon")
                        }}
                      >
                        <Download className="h-4 w-4 mr-2" />
                        Download Video
                      </Button>
                      <Button
                        variant="outline"
                        onClick={handleStartOver}
                      >
                        Generate Another
                      </Button>
                    </div>
                  )}

                  {!processingResult.success && (
                    <div className="space-y-2">
                      <div className="text-sm text-red-600 bg-red-50 p-3 rounded-md">
                        <strong>Error:</strong> {processingResult.error}
                      </div>
                      <Button variant="outline" onClick={handleStartOver}>
                        Try Again
                      </Button>
                    </div>
                  )}
                </>
              )}
            </CardContent>
          </Card>
        )

      default:
        return null
    }
  }

  const getStepIcon = (step: WorkflowStep, isActive: boolean) => {
    const iconClass = cn("h-4 w-4", isActive ? "text-primary" : "text-muted-foreground")

    switch (step) {
      case 'setup':
        return <Settings className={iconClass} />
      case 'processing':
        return <Loader2 className={cn(iconClass, isProcessing && "animate-spin")} />
      case 'complete':
        return <PlayCircle className={iconClass} />
    }
  }

  return (
    <div className={cn("space-y-6", className)}>
      {/* Progress Steps */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Video className="h-5 w-5" />
            PresGen-Training: AI Avatar Video Generation
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="flex items-center space-x-4">
            {[
              { key: 'setup' as const, label: 'Setup & Configuration' },
              { key: 'processing' as const, label: 'Video Generation' },
              { key: 'complete' as const, label: 'Download' },
            ].map((step, index, array) => (
              <div key={step.key} className="flex items-center">
                <div className={cn(
                  "flex items-center gap-2 px-3 py-2 rounded-lg transition-colors",
                  currentStep === step.key
                    ? "bg-primary/10 text-primary border border-primary/20"
                    : "text-muted-foreground"
                )}>
                  {getStepIcon(step.key, currentStep === step.key)}
                  <span className="text-sm font-medium">{step.label}</span>
                </div>
                {index < array.length - 1 && (
                  <ArrowRight className="h-4 w-4 text-muted-foreground mx-2" />
                )}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>

      {/* Current Step Content */}
      {renderStepContent()}

      {/* Feature Overview */}
      {currentStep === 'setup' && (
        <Card>
          <CardHeader>
            <CardTitle>Three Generation Modes</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="text-center space-y-2 p-4 border rounded-lg">
                <User className="h-8 w-8 mx-auto text-blue-500" />
                <h3 className="font-semibold">Video-Only</h3>
                <p className="text-sm text-muted-foreground">
                  Generate avatar videos with voice narration from text content
                </p>
              </div>
              <div className="text-center space-y-2 p-4 border rounded-lg">
                <Presentation className="h-8 w-8 mx-auto text-green-500" />
                <h3 className="font-semibold">Presentation-Only</h3>
                <p className="text-sm text-muted-foreground">
                  Convert Google Slides to narrated presentation videos
                </p>
              </div>
              <div className="text-center space-y-2 p-4 border rounded-lg">
                <PlayCircle className="h-8 w-8 mx-auto text-purple-500" />
                <h3 className="font-semibold">Video-Presentation</h3>
                <p className="text-sm text-muted-foreground">
                  Combined avatar intro with presentation slides
                </p>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}