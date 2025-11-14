import { z } from "zod"

// Base API response schema
export const ApiResponseSchema = z.object({
  ok: z.boolean(),
  message: z.string().optional(),
  error: z.string().optional(),
})

// PresGen Core API schemas
export const CoreGenerateRequestSchema = z.object({
  report_text: z.string().min(1, "Report text is required"),
  presentation_title: z.string().optional(),
  slide_count: z.number().min(3).max(15).default(5),
  include_images: z.boolean().default(true),
  speaker_notes: z.boolean().default(false),
  template_style: z.enum(["corporate", "creative", "minimal"]).default("corporate"),
  report_prompt: z.string().optional(),
})

export const CoreGenerateResponseSchema = ApiResponseSchema.extend({
  url: z.string().optional(),
  presentation_id: z.string().optional(),
  created_slides: z.number().optional(),
  first_slide_id: z.string().optional(),
})

// PresGen Data API schemas
export const DataUploadResponseSchema = z.object({
  dataset_id: z.string(),
  file_name: z.string(),
  sheets: z.array(z.string()),
  schema: z.array(z.object({
    sheet: z.string(),
    columns: z.array(z.object({
      name: z.string(),
      dtype: z.string()
    }))
  })),
  preview_csv: z.string(),
})

// Report Upload Response Schema
export const UploadReportRespSchema = z.object({
  ok: z.literal(true),
  report_id: z.string(),
  char_count: z.number().optional()
})

export const DataGenerateRequestSchema = z.object({
  dataset_id: z.string().min(1, "Dataset ID is required"),
  sheet_name: z.string().optional(),
  has_headers: z.boolean().default(true),
  questions: z.array(z.string()).default([]),
  report_text: z.string().optional(),
  report_id: z.string().optional(),
  presentation_title: z.string().min(3, "Presentation title is required"),
  slide_count: z.number().min(3).max(20).default(7),
  chart_style: z.enum(["modern", "classic", "minimal"]).default("modern"),
  include_images: z.boolean().default(true),
  speaker_notes: z.boolean().default(true),
  template_style: z.enum(["corporate", "creative", "minimal"]).default("corporate"),
  report_prompt: z.string().optional(),
}).refine(
  (data) => {
    const hasReportText = data.report_text && data.report_text.trim().length > 0;
    const hasReportId = data.report_id;
    return hasReportText || hasReportId;
  },
  {
    message: "Either report text or report ID must be provided",
    path: ["report_text"]
  }
)

export const DataGenerateResponseSchema = ApiResponseSchema.extend({
  slides_url: z.string().url().optional(),
  url: z.string().optional(), // For backwards compatibility
  dataset_id: z.string().optional(),
  created_slides: z.number().optional(),
})

// New Generate Data Response Schema
export const GenerateDataRespOkSchema = z.object({
  ok: z.literal(true),
  slides_url: z.string().url(),
  message: z.string().optional()
})

// Form validation schemas
export const CoreFormSchema = z.object({
  report_text: z.string(), // We'll validate this conditionally in the component
  presentation_title: z.string().min(1, "Presentation title is required"),
  slide_count: z.number().min(3).max(15),
  include_images: z.boolean(),
  speaker_notes: z.boolean(),
  template_style: z.enum(["corporate", "creative", "minimal"]),
})

// Schema for validating when no file is uploaded
export const CoreFormWithTextSchema = CoreFormSchema.extend({
  report_text: z.string().min(50, "Report text must be at least 50 characters when no file is uploaded"),
})

export const DataFormSchema = z.object({
  sheet_name: z.string().min(1, "Sheet name is required"),
  has_headers: z.boolean(),
  report_text: z.string().optional(),
  report_file: z.any().optional(),
  questions_multiline: z.string().min(1, "At least one question is required"),
  presentation_title: z.string().min(3, "Presentation title must be at least 3 characters"),
  slide_count: z.number().min(3).max(20),
  chart_style: z.enum(["modern", "classic", "minimal"]),
  include_images: z.boolean(),
  speaker_notes: z.boolean(),
  template_style: z.enum(["corporate", "creative", "minimal"]),
}).refine(
  (data) => {
    const hasReportText = data.report_text && data.report_text.trim().length > 0;
    const hasReportFile = data.report_file;
    return hasReportText || hasReportFile;
  },
  {
    message: "Either report text or report file must be provided",
    path: ["report_text"]
  }
)

// File validation schema
export const FileValidationSchema = z.object({
  name: z.string(),
  size: z.number().max(10 * 1024 * 1024, "File size must be less than 10MB"),
  type: z.string().refine((type) => {
    const allowedTypes = [
      'text/plain',
      'application/pdf', 
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    ]
    return allowedTypes.includes(type) || type === '' // Allow empty type for file extension fallback
  }, "File must be .txt, .pdf, or .docx format"),
})

// Export types
export type ApiResponse = z.infer<typeof ApiResponseSchema>
export type CoreGenerateRequest = z.infer<typeof CoreGenerateRequestSchema>
export type CoreGenerateResponse = z.infer<typeof CoreGenerateResponseSchema>
export type DataUploadResponse = z.infer<typeof DataUploadResponseSchema>
export type UploadReportResp = z.infer<typeof UploadReportRespSchema>
export type DataGenerateRequest = z.infer<typeof DataGenerateRequestSchema>
export type DataGenerateResponse = z.infer<typeof DataGenerateResponseSchema>
export type GenerateDataRespOk = z.infer<typeof GenerateDataRespOkSchema>
export type CoreFormData = z.infer<typeof CoreFormSchema>
export type DataFormData = z.infer<typeof DataFormSchema>
export type FileValidation = z.infer<typeof FileValidationSchema>
