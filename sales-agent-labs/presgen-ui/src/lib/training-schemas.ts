import { z } from "zod"

// Form schemas for validation
export const TrainingFormSchema = z.object({
  mode: z.enum(["video_only", "presentation_only", "video_presentation"]),
  voice_profile_name: z.string().min(1, "Voice profile is required"),
  content_text: z.string().optional(),
  google_slides_url: z.string().url().optional().or(z.literal("")),
  quality_level: z.enum(["fast", "standard", "high"]),
})

export const VoiceCloneFormSchema = z.object({
  profile_name: z.string()
    .min(3, "Profile name must be at least 3 characters")
    .max(50, "Profile name must be less than 50 characters")
    .regex(/^[a-zA-Z0-9_\-\s]+$/, "Profile name can only contain letters, numbers, spaces, hyphens, and underscores"),
  video_path: z.string().optional(),
})

export type TrainingFormData = z.infer<typeof TrainingFormSchema>
export type VoiceCloneFormData = z.infer<typeof VoiceCloneFormSchema>

// API request/response types
export interface TrainingVideoRequest {
  mode: "video_only" | "presentation_only" | "video_presentation"
  voice_profile_name: string
  content_text?: string
  content_file_path?: string
  google_slides_url?: string
  reference_video_path?: string
  quality_level: "fast" | "standard" | "high"
  use_cache: boolean
}

export interface TrainingVideoResponse {
  job_id: string
  success: boolean
  output_path?: string
  download_url?: string
  processing_time?: number
  mode: string
  total_duration?: number
  avatar_duration?: number
  presentation_duration?: number
  error?: string
}

export interface VoiceCloneRequest {
  video_path: string
  profile_name: string
}

export interface VoiceCloneResponse {
  success: boolean
  profile_name: string
  error?: string
}

export interface VoiceProfilesResponse {
  profiles: Array<{
    name: string
    created_at: string
    [key: string]: string | number | boolean
  }>
}

export interface TrainingStatusResponse {
  job_id: string
  status: string
  message: string
}