'use client'

import { useState, useEffect } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Textarea } from "@/components/ui/textarea"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { FileDrop } from "../FileDrop"
import { TrainingFormSchema, TrainingFormData } from "@/lib/training-schemas"
import { generateTrainingVideo, getVoiceProfiles } from "@/lib/training-api"
import { toast } from "sonner"
import { FileText, Loader2, Video, Presentation, PlayCircle } from "lucide-react"
import { ACCEPTED_VIDEO_FILES } from "@/lib/types"

interface TrainingFormProps {
  onJobCreated: (jobId: string, result?: import("@/lib/training-schemas").TrainingVideoResponse) => void
  className?: string
}

export function TrainingForm({ onJobCreated, className }: TrainingFormProps) {
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [voiceProfiles, setVoiceProfiles] = useState<Array<{name: string, created_at: string}>>([])
  const [isLoadingProfiles, setIsLoadingProfiles] = useState(false)

  const form = useForm<TrainingFormData>({
    resolver: zodResolver(TrainingFormSchema),
    defaultValues: {
      mode: "video_only",
      voice_profile_name: "",
      content_text: "",
      google_slides_url: "",
      quality_level: "standard",
    },
  })

  const { register, handleSubmit, formState: { errors }, watch, setValue, reset } = form
  const watchedValues = watch()

  // Load voice profiles on component mount
  useEffect(() => {
    loadVoiceProfiles()
  }, [])

  const loadVoiceProfiles = async () => {
    setIsLoadingProfiles(true)
    try {
      const profiles = await getVoiceProfiles()
      setVoiceProfiles(profiles.profiles)
    } catch (error) {
      console.error('Failed to load voice profiles:', error)
      toast.error("Failed to load voice profiles")
    } finally {
      setIsLoadingProfiles(false)
    }
  }

  const onFileSelect = (file: File) => {
    setUploadedFile(file)
    // Set the reference video path for video-only and combined modes
    if (watchedValues.mode === "video_only" || watchedValues.mode === "video_presentation") {
      // We'll handle the file upload in the API call
    }
  }

  const removeFile = () => {
    setUploadedFile(null)
  }

  const clearForm = () => {
    reset()
    setUploadedFile(null)
  }

  const onSubmit = async (data: TrainingFormData) => {
    // Validate required fields based on mode
    if (data.mode === "video_only" || data.mode === "video_presentation") {
      if (!data.content_text.trim()) {
        toast.error("Content text is required for video generation")
        return
      }
    }

    if (data.mode === "presentation_only" || data.mode === "video_presentation") {
      if (!data.google_slides_url.trim()) {
        toast.error("Google Slides URL is required for presentation generation")
        return
      }
    }

    if (!data.voice_profile_name) {
      toast.error("Please select a voice profile")
      return
    }

    setIsSubmitting(true)

    try {
      // Create the request payload
      const requestData = {
        mode: data.mode,
        voice_profile_name: data.voice_profile_name,
        quality_level: data.quality_level,
        content_text: data.content_text || undefined,
        google_slides_url: data.google_slides_url || undefined,
        use_cache: true,
      }

      console.log('Submitting training request:', requestData)
      if (uploadedFile) {
        console.log('Reference video file:', uploadedFile.name, uploadedFile.size)
      }

      const result = await generateTrainingVideo(requestData, uploadedFile || undefined)

      if (result.success) {
        toast.success("Video generation completed successfully!")
        onJobCreated(result.job_id, result)
      } else {
        toast.error(`Generation failed: ${result.error}`)
        // Still call onJobCreated with failed result to show error in UI
        onJobCreated(result.job_id, result)
      }
    } catch (error: any) {
      console.error('Training generation error:', error)
      toast.error(error.message || "Failed to start video generation")
    } finally {
      setIsSubmitting(false)
    }
  }

  const getModeIcon = (mode: string) => {
    switch (mode) {
      case "video_only":
        return <Video className="h-4 w-4" />
      case "presentation_only":
        return <Presentation className="h-4 w-4" />
      case "video_presentation":
        return <PlayCircle className="h-4 w-4" />
      default:
        return <FileText className="h-4 w-4" />
    }
  }

  const getModeDescription = (mode: string) => {
    switch (mode) {
      case "video_only":
        return "Generate avatar video with voice narration from text content"
      case "presentation_only":
        return "Convert Google Slides presentation to narrated video"
      case "video_presentation":
        return "Combined avatar introduction + narrated presentation slides"
      default:
        return ""
    }
  }

  return (
    <Card className={className}>
      <CardHeader>
        <CardTitle>Avatar Video Generation</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
          {/* Generation Mode */}
          <div className="space-y-2">
            <Label htmlFor="mode">Generation Mode</Label>
            <Select
              value={watchedValues.mode}
              onValueChange={(value) => setValue("mode", value as any)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select generation mode" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="video_only">
                  <div className="flex items-center gap-2">
                    <Video className="h-4 w-4" />
                    Video-Only
                  </div>
                </SelectItem>
                <SelectItem value="presentation_only">
                  <div className="flex items-center gap-2">
                    <Presentation className="h-4 w-4" />
                    Presentation-Only
                  </div>
                </SelectItem>
                <SelectItem value="video_presentation">
                  <div className="flex items-center gap-2">
                    <PlayCircle className="h-4 w-4" />
                    Video-Presentation (Combined)
                  </div>
                </SelectItem>
              </SelectContent>
            </Select>
            {watchedValues.mode && (
              <p className="text-sm text-muted-foreground">
                {getModeDescription(watchedValues.mode)}
              </p>
            )}
            {errors.mode && (
              <p className="text-sm text-red-500">{errors.mode.message}</p>
            )}
          </div>

          {/* Voice Profile */}
          <div className="space-y-2">
            <Label htmlFor="voice_profile_name">Voice Profile</Label>
            <Select
              value={watchedValues.voice_profile_name}
              onValueChange={(value) => setValue("voice_profile_name", value)}
              disabled={isLoadingProfiles}
            >
              <SelectTrigger>
                <SelectValue placeholder={isLoadingProfiles ? "Loading profiles..." : "Select voice profile"} />
              </SelectTrigger>
              <SelectContent>
                {voiceProfiles.length > 0 ? (
                  voiceProfiles.map((profile) => (
                    <SelectItem key={profile.name} value={profile.name}>
                      {profile.name}
                      <span className="text-muted-foreground ml-2 text-xs">
                        (Created: {new Date(profile.created_at).toLocaleDateString()})
                      </span>
                    </SelectItem>
                  ))
                ) : (
                  <div className="px-2 py-1.5 text-sm text-muted-foreground">
                    No voice profiles found - create one below.
                  </div>
                )}
              </SelectContent>
            </Select>
            {errors.voice_profile_name && (
              <p className="text-sm text-red-500">{errors.voice_profile_name.message}</p>
            )}
          </div>

          {/* Content Text - for video_only and video_presentation modes */}
          {(watchedValues.mode === "video_only" || watchedValues.mode === "video_presentation") && (
            <div className="space-y-2">
              <Label htmlFor="content_text">
                Content Text
                {watchedValues.mode === "video_presentation" ? " (Avatar Introduction)" : ""}
              </Label>
              <Textarea
                {...register("content_text")}
                placeholder={
                  watchedValues.mode === "video_presentation"
                    ? "Enter the introduction text that the avatar will speak..."
                    : "Enter the content text that the avatar will narrate..."
                }
                rows={6}
                className="resize-none"
              />
              {errors.content_text && (
                <p className="text-sm text-red-500">{errors.content_text.message}</p>
              )}
            </div>
          )}

          {/* Google Slides URL - for presentation_only and video_presentation modes */}
          {(watchedValues.mode === "presentation_only" || watchedValues.mode === "video_presentation") && (
            <div className="space-y-2">
              <Label htmlFor="google_slides_url">Google Slides URL</Label>
              <Input
                {...register("google_slides_url")}
                placeholder="https://docs.google.com/presentation/d/..."
                type="url"
              />
              <p className="text-sm text-muted-foreground">
                The presentation Notes section will be used for slide narration
              </p>
              {errors.google_slides_url && (
                <p className="text-sm text-red-500">{errors.google_slides_url.message}</p>
              )}
            </div>
          )}

          {/* Reference Video Upload - for video modes */}
          {(watchedValues.mode === "video_only" || watchedValues.mode === "video_presentation") && (
            <div className="space-y-2">
              <Label>Reference Video (Optional)</Label>
              <FileDrop
                onFileSelect={onFileSelect}
                acceptedFiles={ACCEPTED_VIDEO_FILES}
                uploadedFile={uploadedFile}
                onRemoveFile={removeFile}
                maxSizeText="200MB"
                helpText="Upload a reference video to extract avatar appearance (MP4, MOV, AVI)"
              />
            </div>
          )}

          {/* Quality Level */}
          <div className="space-y-2">
            <Label htmlFor="quality_level">Quality Level</Label>
            <Select
              value={watchedValues.quality_level}
              onValueChange={(value) => setValue("quality_level", value as any)}
            >
              <SelectTrigger>
                <SelectValue placeholder="Select quality level" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="fast">Fast (Lower quality, faster processing)</SelectItem>
                <SelectItem value="standard">Standard (Balanced quality and speed)</SelectItem>
                <SelectItem value="high">High (Best quality, slower processing)</SelectItem>
              </SelectContent>
            </Select>
            {errors.quality_level && (
              <p className="text-sm text-red-500">{errors.quality_level.message}</p>
            )}
          </div>

          {/* Action Buttons */}
          <div className="flex gap-2 pt-4">
            <Button
              type="submit"
              disabled={isSubmitting}
              className="flex-1"
            >
              {isSubmitting ? (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              ) : (
                getModeIcon(watchedValues.mode)
              )}
              {isSubmitting ? "Generating..." : "Generate Video"}
            </Button>
            <Button
              type="button"
              variant="outline"
              onClick={clearForm}
              disabled={isSubmitting}
            >
              Clear
            </Button>
          </div>
        </form>
      </CardContent>
    </Card>
  )
}