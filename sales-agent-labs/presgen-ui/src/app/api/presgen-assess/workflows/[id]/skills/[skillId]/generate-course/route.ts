import { NextRequest, NextResponse } from 'next/server'

const ASSESS_API_URL = process.env.NEXT_PUBLIC_ASSESS_API_URL || 'http://localhost:8081'

export async function POST(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string; skillId: string }> }
) {
  const { id, skillId } = await params
  const requestStart = Date.now()

  if (!id || !skillId) {
    return NextResponse.json(
      { error: 'workflow id and skillId are required' },
      { status: 400 }
    )
  }

  const backendUrl = `${ASSESS_API_URL}/api/v1/workflows/${encodeURIComponent(
    id
  )}/skills/${encodeURIComponent(skillId)}/generate-course`

  console.info(
    JSON.stringify({
      scope: 'ui.generateCourse',
      stage: 'request_start',
      workflowId: id,
      skillId,
      backendUrl,
      ts: requestStart,
    })
  )

  try {
    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    const text = await response.text()
    let data: any = {}
    try {
      data = text ? JSON.parse(text) : {}
    } catch (parseError) {
      console.warn('Failed to parse generate-course response JSON', parseError)
      data = text
    }

    if (!response.ok) {
      const detail = typeof data === 'object' && data && 'detail' in data
        ? (data as Record<string, unknown>).detail
        : undefined
      console.warn(
        JSON.stringify({
          scope: 'ui.generateCourse',
          stage: 'response_error',
          workflowId: id,
          skillId,
          status: response.status,
          duration_ms: Date.now() - requestStart,
          detail,
        })
      )
      return NextResponse.json(
        { error: detail || `API error: ${response.status}` },
        { status: response.status }
      )
    }

    console.info(
      JSON.stringify({
        scope: 'ui.generateCourse',
        stage: 'response_success',
        workflowId: id,
        skillId,
        status: response.status,
        duration_ms: Date.now() - requestStart,
      })
    )
    return NextResponse.json(data)
  } catch (error) {
    console.error('Error proxying generate-course request:', error)
    console.error(
      JSON.stringify({
        scope: 'ui.generateCourse',
        stage: 'exception',
        workflowId: id,
        skillId,
        duration_ms: Date.now() - requestStart,
        error: (error as Error)?.message,
      })
    )
    return NextResponse.json(
      { error: 'Failed to connect to PresGen-Assess service' },
      { status: 502 }
    )
  }
}
