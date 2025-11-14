// Common types used across components

export interface UploadedDataset {
  dataset_id: string
  sheets: string[]
  original_filename: string
  upload_time: string
}

export interface TabConfig {
  value: string
  label: string
  disabled?: boolean
  tooltip?: string
}

export const TEMPLATE_STYLES = [
  { value: "corporate", label: "Corporate" },
  { value: "creative", label: "Creative" },
  { value: "minimal", label: "Minimal" },
] as const

export const CHART_STYLES = [
  { value: "modern", label: "Modern" },
  { value: "classic", label: "Classic" },
  { value: "minimal", label: "Minimal" },
] as const

export const ACCEPTED_TEXT_FILES = {
  'text/plain': ['.txt'],
}

export const ACCEPTED_REPORT_FILES = {
  'application/pdf': ['.pdf'],
  'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx'],
  'text/plain': ['.txt'],
}

export const ACCEPTED_DATA_FILES = {
  'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': ['.xlsx'],
  'text/csv': ['.csv'],
}

export const ACCEPTED_VIDEO_FILES = {
  'video/mp4': ['.mp4'],
  'video/quicktime': ['.mov'],
  'video/x-msvideo': ['.avi'],
  'video/x-matroska': ['.mkv'],
}

export const MAX_FILE_SIZE_MB = 10
export const MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024

export const MAX_REPORT_FILE_SIZE_MB = 20
export const MAX_REPORT_FILE_SIZE_BYTES = MAX_REPORT_FILE_SIZE_MB * 1024 * 1024

export const MAX_DATA_FILE_SIZE_MB = 50
export const MAX_DATA_FILE_SIZE_BYTES = MAX_DATA_FILE_SIZE_MB * 1024 * 1024

export const MAX_VIDEO_FILE_SIZE_MB = 200
export const MAX_VIDEO_FILE_SIZE_BYTES = MAX_VIDEO_FILE_SIZE_MB * 1024 * 1024