import { z } from "zod"

// Video upload form validation
export const VideoFormSchema = z.object({
  language: z.string().min(2).default("en"),
  maxBullets: z.number().min(3).max(10).default(5),
  cropMode: z.enum(["auto", "manual"]).default("auto"),
  cropRegion: z.object({
    x: z.number().min(0),
    y: z.number().min(0),
    width: z.number().min(1),
    height: z.number().min(1)
  }).optional()
})

export type VideoFormData = z.infer<typeof VideoFormSchema>

// Bullet point validation
export const BulletPointSchema = z.object({
  timestamp: z.string().regex(/^\d{2}:\d{2}$/, "Timestamp must be in MM:SS format"),
  text: z.string().min(1).max(80, "Text must be 80 characters or less"),
  confidence: z.number().min(0).max(1),
  duration: z.number().min(15).max(45)
})

export const VideoSummarySchema = z.object({
  bullet_points: z.array(BulletPointSchema).min(3, "At least 3 bullet points required").max(5),
  main_themes: z.array(z.string()).max(3),
  total_duration: z.string().regex(/^\d{2}:\d{2}$/),
  language: z.string().default("en"),
  summary_confidence: z.number().min(0).max(1)
})

export type BulletPoint = z.infer<typeof BulletPointSchema>
export type VideoSummary = z.infer<typeof VideoSummarySchema>

// Crop region validation
export const CropRegionSchema = z.object({
  x: z.number().min(0),
  y: z.number().min(0), 
  width: z.number().min(1),
  height: z.number().min(1)
})

export type CropRegion = z.infer<typeof CropRegionSchema>

// Job status types
export const VideoJobStatusSchema = z.object({
  job_id: z.string(),
  status: z.enum(["uploaded", "processing", "phase1_complete", "phase2_complete", "completed", "failed"]),
  progress: z.object({
    phase: z.string(),
    percentage: z.number().min(0).max(100).optional(),
    current_task: z.string().optional(),
    time_elapsed: z.number().optional(),
    time_remaining: z.number().optional()
  }).optional(),
  error: z.string().optional()
})

export type VideoJobStatus = z.infer<typeof VideoJobStatusSchema>

// Video preview response
export const VideoPreviewResponseSchema = z.object({
  job_id: z.string(),
  summary: VideoSummarySchema,
  slide_urls: z.array(z.string()),
  video_metadata: z.record(z.any()),
  crop_region: CropRegionSchema,
  processing_stats: z.object({
    phase1_time: z.number(),
    phase2_time: z.number(),
    slides_generated: z.number()
  })
})

export type VideoPreviewResponse = z.infer<typeof VideoPreviewResponseSchema>

// Video languages supported
export const VIDEO_LANGUAGES = [
  { value: "en", label: "English" },
  { value: "es", label: "Spanish" },
  { value: "fr", label: "French" },
  { value: "de", label: "German" },
  { value: "it", label: "Italian" },
  { value: "pt", label: "Portuguese" },
  { value: "ru", label: "Russian" },
  { value: "ja", label: "Japanese" },
  { value: "ko", label: "Korean" },
  { value: "zh", label: "Chinese" }
] as const

// Accepted video file types
export const VIDEO_FILE_TYPES = {
  'video/mp4': ['.mp4'],
  'video/quicktime': ['.mov'],
  'video/x-msvideo': ['.avi'],
  'video/webm': ['.webm']
}

export const MAX_VIDEO_SIZE_MB = 200