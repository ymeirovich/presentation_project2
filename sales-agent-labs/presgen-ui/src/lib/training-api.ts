import {
  TrainingVideoRequest,
  TrainingVideoResponse,
  VoiceCloneRequest,
  VoiceCloneResponse,
  VoiceProfilesResponse,
  TrainingStatusResponse,
} from "./training-schemas"

// API configuration
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080"

class TrainingApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message)
    this.name = "TrainingApiError"
  }
}

// Helper function to handle API responses
async function handleApiResponse<T>(response: Response): Promise<T> {
  if (!response.ok) {
    let errorMessage = `HTTP ${response.status}: ${response.statusText}`

    try {
      const errorData = await response.json()
      errorMessage = errorData.detail || errorData.message || errorMessage
    } catch {
      // If we can't parse the error response, use the default message
    }

    throw new TrainingApiError(errorMessage, response.status)
  }

  return response.json()
}

// Generate training video
export async function generateTrainingVideo(
  request: TrainingVideoRequest,
  referenceVideo?: File
): Promise<TrainingVideoResponse> {
  const endpoint = `/training/${request.mode.replace('_', '-')}`

  // For presentation-only mode (no file upload), send JSON
  if (request.mode === 'presentation_only' && !referenceVideo) {
    const response = await fetch(`${API_BASE_URL}${endpoint}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(request),
    })

    return handleApiResponse<TrainingVideoResponse>(response)
  }

  // For modes that require file uploads, use FormData
  const formData = new FormData()

  // Add all the request fields as form data
  formData.append('voice_profile_name', request.voice_profile_name)
  formData.append('quality_level', request.quality_level)
  formData.append('use_cache', String(request.use_cache))

  if (request.content_text) {
    formData.append('content_text', request.content_text)
  }

  if (request.content_file_path) {
    formData.append('content_file_path', request.content_file_path)
  }

  if (request.google_slides_url) {
    formData.append('google_slides_url', request.google_slides_url)
  }

  // Add the reference video file if provided
  if (referenceVideo) {
    formData.append('reference_video', referenceVideo)
  }

  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: "POST",
    body: formData, // Don't set Content-Type header, let browser set it with boundary
  })

  return handleApiResponse<TrainingVideoResponse>(response)
}

// Clone voice from video
export async function cloneVoiceFromVideo(
  request: VoiceCloneRequest
): Promise<VoiceCloneResponse> {
  const response = await fetch(`${API_BASE_URL}/training/clone-voice`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(request),
  })

  return handleApiResponse<VoiceCloneResponse>(response)
}

// Get voice profiles
export async function getVoiceProfiles(): Promise<VoiceProfilesResponse> {
  const response = await fetch(`${API_BASE_URL}/training/voice-profiles`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  })

  return handleApiResponse<VoiceProfilesResponse>(response)
}

// Get training job status
export async function getTrainingStatus(jobId: string): Promise<TrainingStatusResponse> {
  const response = await fetch(`${API_BASE_URL}/training/status/${jobId}`, {
    method: "GET",
    headers: {
      "Content-Type": "application/json",
    },
  })

  return handleApiResponse<TrainingStatusResponse>(response)
}

// Export the error class for error handling
export { TrainingApiError }