import { NextRequest, NextResponse } from 'next/server'

const ASSESS_API_URL = process.env.NEXT_PUBLIC_ASSESS_API_URL || 'http://localhost:8081'

export async function POST(
  request: NextRequest,
  { params }: { params: Promise<{ course_id: string }> }
) {
  try {
    const { course_id } = await params
    const backendUrl = `${ASSESS_API_URL}/api/v1/gap-analysis-dashboard/courses/${course_id}/generate`

    console.log('Proxying POST Trigger Course Generation for course:', course_id, 'to:', backendUrl)

    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    const data = await response.json()

    if (!response.ok) {
      console.error('Course Generation API error:', response.status, data)
      return NextResponse.json(
        { error: data.detail || `API error: ${response.status}` },
        { status: response.status }
      )
    }

    return NextResponse.json(data)

  } catch (error) {
    console.error('Error proxying Course Generation request:', error)
    return NextResponse.json(
      { error: 'Failed to connect to PresGen-Assess service' },
      { status: 502 }
    )
  }
}