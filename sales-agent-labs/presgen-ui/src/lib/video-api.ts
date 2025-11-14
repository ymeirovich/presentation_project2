import { VideoFormData, VideoSummary, VideoJobStatus, VideoPreviewResponse, CropRegion } from "./video-schemas"

// API base URL - empty string for production (uses relative URLs through nginx)
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? ''

export class VideoApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public response?: any
  ) {
    super(message)
    this.name = 'VideoApiError'
  }
}

async function handleVideoApiResponse<T>(response: Response): Promise<T> {
  let data: any
  
  try {
    const text = await response.text()
    
    if (!text || (!text.trim().startsWith('{') && !text.trim().startsWith('['))) {
      throw new VideoApiError(response.status, text || 'Unknown server error')
    }
    
    data = JSON.parse(text)
  } catch (e) {
    if (e instanceof VideoApiError) throw e
    throw new VideoApiError(response.status, 'Invalid JSON response from server')
  }
  
  if (!response.ok) {
    const message = data?.detail || data?.message || `Request failed with status ${response.status}`
    throw new VideoApiError(response.status, message, data)
  }
  
  return data
}

export async function uploadVideo(file: File, config: VideoFormData): Promise<{ job_id: string }> {
  const formData = new FormData()
  formData.append('file', file)
  
  // Add configuration as JSON metadata
  formData.append('config', JSON.stringify(config))
  
  const response = await fetch(`${API_BASE_URL}/video/upload`, {
    method: 'POST',
    body: formData
  })
  
  return handleVideoApiResponse(response)
}

export async function startVideoProcessing(jobId: string): Promise<{ job_id: string; status: string }> {
  const response = await fetch(`${API_BASE_URL}/video/process/${jobId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    }
  })
  
  return handleVideoApiResponse(response)
}

export async function startPhase2Processing(jobId: string): Promise<{ job_id: string; status: string }> {
  const response = await fetch(`${API_BASE_URL}/video/process-phase2/${jobId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    }
  })
  
  return handleVideoApiResponse(response)
}

export async function getVideoJobStatus(jobId: string): Promise<VideoJobStatus> {
  const response = await fetch(`${API_BASE_URL}/video/status/${jobId}`, {
    method: 'GET',
    headers: {
      'Content-Type': 'application/json'
    }
  })
  
  return handleVideoApiResponse(response)
}

export async function getVideoPreview(jobId: string): Promise<VideoPreviewResponse> {
  const response = await fetch(`${API_BASE_URL}/video/preview/${jobId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    }
  })
  
  return handleVideoApiResponse(response)
}

export async function updateBulletPoints(jobId: string, summary: VideoSummary): Promise<VideoPreviewResponse> {
  const response = await fetch(`${API_BASE_URL}/video/bullets/${jobId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(summary)
  })
  
  return handleVideoApiResponse(response)
}

export async function updateCropRegion(jobId: string, cropRegion: CropRegion): Promise<{ success: boolean }> {
  const response = await fetch(`${API_BASE_URL}/video/crop/${jobId}`, {
    method: 'PUT',
    headers: {
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(cropRegion)
  })
  
  return handleVideoApiResponse(response)
}

export async function generateFinalVideo(jobId: string): Promise<{ job_id: string; status: string }> {
  const response = await fetch(`${API_BASE_URL}/video/generate/${jobId}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json'
    }
  })
  
  return handleVideoApiResponse(response)
}

export async function downloadVideo(jobId: string): Promise<string> {
  const response = await fetch(`${API_BASE_URL}/video/result/${jobId}`, {
    method: 'GET'
  })
  
  if (!response.ok) {
    throw new VideoApiError(response.status, 'Failed to download video')
  }
  
  // Return the download URL or blob URL
  return response.url
}