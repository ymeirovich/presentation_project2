import { NextRequest, NextResponse } from 'next/server'

const ASSESS_API_URL = process.env.NEXT_PUBLIC_ASSESS_API_URL || 'http://localhost:8081'

export async function GET(
  _request: NextRequest,
  { params }: { params: Promise<{ id: string; courseId: string }> }
) {
  const { id, courseId } = await params

  if (!id || !courseId) {
    return NextResponse.json(
      { error: 'workflow id and courseId are required' },
      { status: 400 }
    )
  }

  const backendUrl = `${ASSESS_API_URL}/api/v1/workflows/${encodeURIComponent(
    id
  )}/courses/${encodeURIComponent(courseId)}/status`

  try {
    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      cache: 'no-cache',
    })

    const text = await response.text()
    let data: any = {}
    try {
      data = text ? JSON.parse(text) : {}
    } catch (parseError) {
      console.warn('Failed to parse course status response JSON', parseError)
      data = text
    }

    if (!response.ok) {
      const detail = typeof data === 'object' && data && 'detail' in data
        ? (data as Record<string, unknown>).detail
        : undefined
      return NextResponse.json(
        { error: detail || `API error: ${response.status}` },
        { status: response.status }
      )
    }

    return NextResponse.json(data)
  } catch (error) {
    console.error('Error proxying course status request:', error)
    return NextResponse.json(
      { error: 'Failed to connect to PresGen-Assess service' },
      { status: 502 }
    )
  }
}
