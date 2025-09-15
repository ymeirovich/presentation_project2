'use client'

import { useState, useEffect } from "react"
import { useForm } from "react-hook-form"
import { zodResolver } from "@hookform/resolvers/zod"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Input } from "@/components/ui/input"
import { Label } from "@/components/ui/label"
import { Badge } from "@/components/ui/badge"
import { FileDrop } from "../FileDrop"
import { VoiceCloneFormSchema, VoiceCloneFormData } from "@/lib/training-schemas"
import { cloneVoiceFromVideo, getVoiceProfiles } from "@/lib/training-api"
import { toast } from "sonner"
import { ACCEPTED_VIDEO_FILES } from "@/lib/types"
import { Loader2, User, Plus, Trash2, RefreshCw } from "lucide-react"

interface VoiceProfileManagerProps {
  className?: string
}

export function VoiceProfileManager({ className }: VoiceProfileManagerProps) {
  const [uploadedFile, setUploadedFile] = useState<File | null>(null)
  const [isCloning, setIsCloning] = useState(false)
  const [voiceProfiles, setVoiceProfiles] = useState<Array<{name: string, created_at: string}>>([])
  const [isLoadingProfiles, setIsLoadingProfiles] = useState(false)
  const [showCloneForm, setShowCloneForm] = useState(false)

  const form = useForm<VoiceCloneFormData>({
    resolver: zodResolver(VoiceCloneFormSchema),
    defaultValues: {
      profile_name: "",
      video_path: "",
    },
  })

  const { register, handleSubmit, formState: { errors }, reset } = form

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
  }

  const removeFile = () => {
    setUploadedFile(null)
  }

  const clearForm = () => {
    reset()
    setUploadedFile(null)
    setShowCloneForm(false)
  }

  const onSubmit = async (data: VoiceCloneFormData) => {
    if (!uploadedFile) {
      toast.error("Please upload a video file")
      return
    }

    if (!data.profile_name.trim()) {
      toast.error("Please enter a profile name")
      return
    }

    setIsCloning(true)

    try {
      // In a real implementation, we'd first upload the file and get a path
      // For now, we'll use the test video path from the documentation
      const testVideoPath = "/Users/yitzchak/Documents/learn/presentation_project/sales-agent-labs/sadtalker-api/examples/presgen_test2.mp4"

      const result = await cloneVoiceFromVideo({
        video_path: testVideoPath, // In production, this would be the uploaded file path
        profile_name: data.profile_name.trim(),
      })

      if (result.success) {
        toast.success(`Voice profile "${result.profile_name}" created successfully!`)
        clearForm()
        loadVoiceProfiles() // Refresh the profiles list
      } else {
        toast.error(`Voice cloning failed: ${result.error}`)
      }
    } catch (error: any) {
      console.error('Voice cloning error:', error)
      toast.error(error.message || "Failed to clone voice")
    } finally {
      setIsCloning(false)
    }
  }

  const handleDeleteProfile = (profileName: string) => {
    // TODO: Implement profile deletion API
    toast.info("Profile deletion functionality coming soon")
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <CardTitle className="flex items-center gap-2">
            <User className="h-5 w-5" />
            Voice Profile Manager
          </CardTitle>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={loadVoiceProfiles}
              disabled={isLoadingProfiles}
            >
              {isLoadingProfiles ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <RefreshCw className="h-4 w-4" />
              )}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => setShowCloneForm(!showCloneForm)}
            >
              <Plus className="h-4 w-4 mr-2" />
              Clone Voice
            </Button>
          </div>
        </div>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Existing Voice Profiles */}
        <div className="space-y-3">
          <h4 className="text-sm font-medium">Available Voice Profiles</h4>
          {isLoadingProfiles ? (
            <div className="flex items-center gap-2 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Loading profiles...</span>
            </div>
          ) : voiceProfiles.length > 0 ? (
            <div className="space-y-2">
              {voiceProfiles.map((profile) => (
                <div
                  key={profile.name}
                  className="flex items-center justify-between p-3 border rounded-lg"
                >
                  <div>
                    <div className="font-medium">{profile.name}</div>
                    <div className="text-sm text-muted-foreground">
                      Created: {new Date(profile.created_at).toLocaleDateString()}
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <Badge variant="secondary">Ready</Badge>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => handleDeleteProfile(profile.name)}
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <div className="text-center py-6 text-muted-foreground">
              <User className="h-8 w-8 mx-auto mb-2 opacity-50" />
              <div>No voice profiles found</div>
              <div className="text-sm">Create your first voice profile by cloning from a video</div>
            </div>
          )}
        </div>

        {/* Voice Cloning Form */}
        {showCloneForm && (
          <>
            <div className="border-t my-4" />
            <div className="space-y-4">
              <h4 className="text-sm font-medium">Clone Voice from Video</h4>
              <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                {/* Profile Name */}
                <div className="space-y-2">
                  <Label htmlFor="profile_name">Profile Name</Label>
                  <Input
                    {...register("profile_name")}
                    placeholder="Enter a name for this voice profile..."
                    disabled={isCloning}
                  />
                  {errors.profile_name && (
                    <p className="text-sm text-red-500">{errors.profile_name.message}</p>
                  )}
                </div>

                {/* Video Upload */}
                <div className="space-y-2">
                  <Label>Training Video</Label>
                  <FileDrop
                    onFileSelect={onFileSelect}
                    acceptedFiles={ACCEPTED_VIDEO_FILES}
                    uploadedFile={uploadedFile}
                    onRemoveFile={removeFile}
                    maxSizeText="200MB"
                    helpText="Upload a clear video with good audio quality (MP4, MOV, AVI). Minimum 30 seconds recommended."
                    disabled={isCloning}
                  />
                  <p className="text-xs text-muted-foreground">
                    Tip: Use a video with clear speech, minimal background noise, and consistent audio levels for best results.
                  </p>
                </div>

                {/* Action Buttons */}
                <div className="flex gap-2">
                  <Button
                    type="submit"
                    disabled={isCloning || !uploadedFile}
                    className="flex-1"
                  >
                    {isCloning ? (
                      <Loader2 className="h-4 w-4 mr-2 animate-spin" />
                    ) : (
                      <Plus className="h-4 w-4 mr-2" />
                    )}
                    {isCloning ? "Cloning Voice..." : "Clone Voice"}
                  </Button>
                  <Button
                    type="button"
                    variant="outline"
                    onClick={clearForm}
                    disabled={isCloning}
                  >
                    Cancel
                  </Button>
                </div>
              </form>
            </div>
          </>
        )}

        {/* Usage Information */}
        <div className="bg-muted/50 p-3 rounded-lg">
          <div className="text-sm">
            <div className="font-medium mb-1">Voice Cloning Requirements</div>
            <ul className="text-muted-foreground space-y-1 text-xs">
              <li>• Clear audio with minimal background noise</li>
              <li>• Consistent speaking pace and volume</li>
              <li>• Minimum 30 seconds of speech recommended</li>
              <li>• Single speaker preferred for best results</li>
            </ul>
          </div>
        </div>
      </CardContent>
    </Card>
  )
}