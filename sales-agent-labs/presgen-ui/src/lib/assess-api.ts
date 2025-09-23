import { z } from 'zod'
import { ApiError } from '@/lib/api'
import {
  AssessmentFormValues,
  AssessmentRequestPayload,
  AssessmentWorkflowResponse,
  AssessmentWorkflowResponseSchema,
  CertificationProfile,
  CertificationProfileSchema,
  WorkflowDetail,
  WorkflowDetailSchema,
  WorkflowListResponse,
  WorkflowListResponseSchema,
  WorkflowStatusUpdate,
} from '@/lib/assess-schemas'

const ASSESS_API_BASE_URL = process.env.NEXT_PUBLIC_ASSESS_API_URL
  || process.env.NEXT_PUBLIC_API_BASE_URL
  || 'http://localhost:8080'

const API_PREFIX = '/api/v1'

function buildUrl(path: string): string {
  return `${ASSESS_API_BASE_URL}${API_PREFIX}${path}`
}

function getHeaders(contentType?: string): Record<string, string> {
  const headers: Record<string, string> = {}
  if (contentType) {
    headers['Content-Type'] = contentType
  }
  return headers
}

async function parseResponse<T>(response: Response, schema: z.ZodTypeAny): Promise<T> {
  let parsed: unknown

  try {
    const text = await response.text()
    parsed = text ? JSON.parse(text) : {}
  } catch {
    throw new ApiError(response.status, 'Failed to parse server response')
  }

  if (!response.ok) {
    const message = typeof parsed === 'object' && parsed && 'detail' in parsed
      ? String((parsed as Record<string, unknown>).detail)
      : response.statusText || 'Request failed'

    throw new ApiError(response.status, message, parsed)
  }

  const validation = schema.safeParse(parsed)
  if (!validation.success) {
    console.warn('Assess API response validation failed', validation.error)
    throw new ApiError(response.status, 'Unexpected server response shape', parsed)
  }

  return validation.data
}

export async function fetchCertificationProfiles(): Promise<CertificationProfile[]> {
  const response = await fetch(buildUrl('/certifications'), {
    headers: getHeaders(),
    cache: 'no-store',
  })

  const schema = z.array(CertificationProfileSchema)
  const profiles = await parseResponse<CertificationProfile[]>(response, schema)

  return profiles.sort((a, b) => a.name.localeCompare(b.name))
}

export async function requestAssessmentWorkflow(
  formValues: AssessmentFormValues,
  options?: { userId?: string }
): Promise<AssessmentWorkflowResponse> {
  const domainDistributionObject = Object.fromEntries(
    formValues.domainDistribution.map((entry) => [entry.domain, entry.questionCount])
  )

  const payload: AssessmentRequestPayload = {
    user_id: options?.userId ?? 'ui-demo',
    certification_profile_id: formValues.certificationId,
    workflow_type: 'assessment_generation',
    parameters: {
      title: formValues.title.trim(),
      summary_markdown: formValues.summaryMarkdown.trim(),
      difficulty_level: formValues.difficulty,
      question_count: formValues.questionCount,
      passing_score: formValues.passingScore,
      time_limit_minutes: formValues.timeLimitMinutes,
      slide_count: formValues.slideCount,
      domain_distribution: domainDistributionObject,
      include_avatar: formValues.includeAvatar,
      notes_markdown: formValues.notesMarkdown?.trim() || '',
    },
  }

  const response = await fetch(buildUrl('/workflows'), {
    method: 'POST',
    headers: getHeaders('application/json'),
    body: JSON.stringify(payload),
  })

  return parseResponse<AssessmentWorkflowResponse>(response, AssessmentWorkflowResponseSchema)
}

// Workflow Management API Functions

export async function fetchWorkflows(options?: {
  status_filter?: string
  skip?: number
  limit?: number
}): Promise<WorkflowListResponse> {
  const searchParams = new URLSearchParams()
  if (options?.status_filter) searchParams.set('status_filter', options.status_filter)
  if (options?.skip) searchParams.set('skip', options.skip.toString())
  if (options?.limit) searchParams.set('limit', options.limit.toString())

  const url = buildUrl(`/workflows${searchParams.toString() ? `?${searchParams}` : ''}`)
  const response = await fetch(url, {
    headers: getHeaders(),
    cache: 'no-store',
  })

  return parseResponse<WorkflowListResponse>(response, WorkflowListResponseSchema)
}

export async function fetchWorkflowDetail(workflowId: string): Promise<WorkflowDetail> {
  const response = await fetch(buildUrl(`/workflows/${workflowId}`), {
    headers: getHeaders(),
    cache: 'no-store',
  })

  return parseResponse<WorkflowDetail>(response, WorkflowDetailSchema)
}

export async function updateWorkflowStatus(
  workflowId: string,
  update: WorkflowStatusUpdate
): Promise<WorkflowDetail> {
  const response = await fetch(buildUrl(`/workflows/${workflowId}/status`), {
    method: 'PUT',
    headers: getHeaders('application/json'),
    body: JSON.stringify(update),
  })

  return parseResponse<WorkflowDetail>(response, WorkflowDetailSchema)
}

export async function retryWorkflow(workflowId: string): Promise<WorkflowDetail> {
  return updateWorkflowStatus(workflowId, { status: 'pending', progress: 0 })
}
