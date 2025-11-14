import {
  CoreGenerateRequest,
  CoreGenerateResponse,
  CoreGenerateResponseSchema,
  DataUploadResponse,
  DataUploadResponseSchema,
  UploadReportResp,
  UploadReportRespSchema,
  DataGenerateRequest,
  DataGenerateResponse,
  DataGenerateResponseSchema,
  GenerateDataRespOk,
  GenerateDataRespOkSchema,
} from "./schemas"

// API base URL - empty string for production (uses relative URLs through nginx)
// In development with .env.local, this will be set to http://localhost
const API_BASE_URL = process.env.NEXT_PUBLIC_API_BASE_URL ?? ''

// Common headers for all requests (no special headers needed with Next.js proxy)
function getCommonHeaders(contentType?: string): Record<string, string> {
  const headers: Record<string, string> = {}
  
  if (contentType) {
    headers['Content-Type'] = contentType
  }
  
  return headers
}

class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
    public response?: any
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

async function handleApiResponse<T>(response: Response, schema: any): Promise<T> {
  let data: any
  
  try {
    const text = await response.text()
    
    // If response is not JSON (like HTML error pages), create error structure
    if (!text || !text.trim().startsWith('{') && !text.trim().startsWith('[')) {
      throw new ApiError(response.status, text || 'Unknown server error')
    }
    
    data = text ? JSON.parse(text) : {}
  } catch (error) {
    if (error instanceof ApiError) {
      throw error
    }
    throw new ApiError(response.status, `Failed to parse response: ${error}`)
  }

  if (!response.ok) {
    // Handle specific error cases
    let errorMessage = `HTTP ${response.status}`
    
    if (data?.detail) {
      errorMessage = data.detail
    } else if (data?.error) {
      errorMessage = data.error
    } else if (data?.message) {
      errorMessage = data.message
    } else if (response.status === 422) {
      errorMessage = 'Validation error: Please check your input data'
    } else if (response.status === 500) {
      errorMessage = 'Server error: The presentation generation failed'
    } else if (response.status === 0 || response.status >= 502) {
      errorMessage = 'Network error: Cannot connect to the backend service'
    }
    
    throw new ApiError(response.status, errorMessage, data)
  }

  // Validate response against schema
  const result = schema.safeParse(data)
  if (!result.success) {
    console.warn('API response validation failed:', result.error)
    console.warn('Response data:', data)
    // Return data anyway but log the validation error
  }

  return data as T
}

// PresGen Core API
export async function createPresentation(
  request: CoreGenerateRequest,
  file?: File
): Promise<CoreGenerateResponse> {
  const url = `${API_BASE_URL}/render`
  
  let reportText = request.report_text
  
  // If file is provided, we need to read its content first
  if (file) {
    console.log('Reading file content:', file.name, file.type)
    try {
      reportText = await readFileContent(file)
      console.log('File content read successfully, length:', reportText.length)
    } catch (error) {
      console.error('Error reading file:', error)
      throw new Error(`Failed to read file: ${error}`)
    }
  }
  
  // Validate that we have content
  if (!reportText || reportText.trim().length === 0) {
    throw new Error('No content provided - either enter text or upload a file')
  }
  
  // Backend expects RenderRequest format
  const payload = {
    report_text: reportText,
    slides: request.slide_count,
    use_cache: true,
    request_id: generateRequestId(),
    report_prompt: request.report_prompt?.trim() || undefined,
  }
  
  console.log('Sending payload to backend:', {
    ...payload,
    report_text: `${payload.report_text.substring(0, 100)}...`, // Log first 100 chars only
    report_text_length: payload.report_text.length,
    has_special_chars: /[^\u0000-\u007F]/.test(payload.report_text),
    request_id: payload.request_id,
    report_prompt_length: payload.report_prompt ? payload.report_prompt.length : 0,
  })

  const controller = new AbortController()
  const timeoutId = setTimeout(() => controller.abort(), 5 * 60 * 1000) // 5 minute timeout
  
  try {
    const response = await fetch(url, {
      method: 'POST',
      headers: getCommonHeaders('application/json'),
      body: JSON.stringify(payload),
      signal: controller.signal
    })
    
    clearTimeout(timeoutId)
    console.log('Response received:', {
      status: response.status,
      statusText: response.statusText,
      ok: response.ok,
      headers: Object.fromEntries(response.headers.entries())
    })
    
    return handleApiResponse<CoreGenerateResponse>(response, CoreGenerateResponseSchema)
  } catch (error) {
    clearTimeout(timeoutId)
    if (error instanceof Error && error.name === 'AbortError') {
      throw new Error('Request timed out after 5 minutes')
    }
    throw error
  }
}

// Helper function to read file content
async function readFileContent(file: File): Promise<string> {
  const fileType = file.type.toLowerCase()
  const fileName = file.name.toLowerCase()

  // Handle PDF files
  if (fileType === 'application/pdf' || fileName.endsWith('.pdf')) {
    return readPDFContent(file)
  }
  
  // Handle DOCX files
  if (fileType === 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' || fileName.endsWith('.docx')) {
    return readDOCXContent(file)
  }
  
  // Handle text files (default)
  return readTextContent(file)
}

// Read text files
async function readTextContent(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = (e) => resolve(e.target?.result as string)
    reader.onerror = () => reject(new Error('Failed to read text file'))
    reader.readAsText(file)
  })
}

// Read PDF files
async function readPDFContent(file: File): Promise<string> {
  try {
    const pdfjs = await import('pdfjs-dist')
    
    // Configure worker - using CDN version for simplicity
    pdfjs.GlobalWorkerOptions.workerSrc = `//cdnjs.cloudflare.com/ajax/libs/pdf.js/${pdfjs.version}/pdf.worker.min.js`
    
    const arrayBuffer = await file.arrayBuffer()
    const pdf = await pdfjs.getDocument({ data: arrayBuffer }).promise
    
    let textContent = ''
    
    // Extract text from each page
    for (let pageNum = 1; pageNum <= pdf.numPages; pageNum++) {
      const page = await pdf.getPage(pageNum)
      const textContentPage = await page.getTextContent()
      
      const pageText = textContentPage.items
        .map((item: any) => item.str)
        .join(' ')
      
      textContent += pageText + '\n'
    }
    
    return textContent.trim()
  } catch (error) {
    throw new Error(`Failed to read PDF file: ${error}`)
  }
}

// Read DOCX files
async function readDOCXContent(file: File): Promise<string> {
  try {
    const mammoth = await import('mammoth')
    
    const arrayBuffer = await file.arrayBuffer()
    const result = await mammoth.extractRawText({ arrayBuffer })
    
    return result.value
  } catch (error) {
    throw new Error(`Failed to read DOCX file: ${error}`)
  }
}

// Helper function to generate request ID
function generateRequestId(): string {
  return `req-${Math.random().toString(36).substring(2, 11)}-${Date.now()}`
}

// PresGen Data API - Upload
export async function uploadDataFile(file: File): Promise<DataUploadResponse> {
  const url = `${API_BASE_URL}/data/upload`
  
  const formData = new FormData()
  formData.append('file', file)

  const response = await fetch(url, {
    method: 'POST',
    headers: getCommonHeaders(),
    body: formData,
  })

  return handleApiResponse<DataUploadResponse>(response, DataUploadResponseSchema)
}

// PresGen Data API - Upload Report
export async function uploadReport(file: File): Promise<UploadReportResp> {
  const url = `/api/presgen-data/upload-report`
  
  const formData = new FormData()
  formData.append('report_file', file)

  const response = await fetch(url, {
    method: 'POST',
    body: formData,
  })

  return handleApiResponse<UploadReportResp>(response, UploadReportRespSchema)
}

// PresGen Data API - Generate with Context
export async function generateDataWithContext(
  request: DataGenerateRequest
): Promise<GenerateDataRespOk> {
  const url = `/api/presgen-data/generate-mvp`
  
  const response = await fetch(url, {
    method: 'POST',
    headers: getCommonHeaders('application/json'),
    body: JSON.stringify(request),
  })

  return handleApiResponse<GenerateDataRespOk>(response, GenerateDataRespOkSchema)
}

// PresGen Data API - Generate (Legacy)
export async function generateDataPresentation(
  request: DataGenerateRequest
): Promise<DataGenerateResponse> {
  const url = `${API_BASE_URL}/data/ask`
  
  // Convert frontend request to backend DataAsk format
  const payload = {
    dataset_id: request.dataset_id,
    sheet: request.sheet_name,
    questions: request.questions,
    report_text: request.report_text,
    slides: request.slide_count,
    use_cache: true
  }
  
  const response = await fetch(url, {
    method: 'POST',
    headers: getCommonHeaders('application/json'),
    body: JSON.stringify(payload),
  })

  return handleApiResponse<DataGenerateResponse>(response, DataGenerateResponseSchema)
}

// Health check
export async function healthCheck(): Promise<{ ok: boolean }> {
  const url = `${API_BASE_URL}/healthz`
  
  const response = await fetch(url, {
    headers: getCommonHeaders()
  })
  return response.json()
}

// Export the ApiError for error handling in components
export { ApiError }
