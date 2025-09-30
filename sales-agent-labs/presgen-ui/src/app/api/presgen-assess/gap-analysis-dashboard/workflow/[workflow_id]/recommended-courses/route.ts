import { NextRequest, NextResponse } from 'next/server'

const ASSESS_API_URL = process.env.NEXT_PUBLIC_ASSESS_API_URL || 'http://localhost:8081'

export async function GET(
  request: NextRequest,
  { params }: { params: { workflow_id: string } }
) {
  try {
    const { workflow_id } = params
    const backendUrl = `${ASSESS_API_URL}/api/v1/gap-analysis-dashboard/workflow/${workflow_id}/recommended-courses`

    console.log('Proxying GET Recommended Courses for workflow:', workflow_id, 'to:', backendUrl)

    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      cache: 'no-store',
    })

    const data = await response.json()

    if (!response.ok) {
      console.error('Recommended Courses API error:', response.status, data)
      return NextResponse.json(
        { error: data.detail || `API error: ${response.status}` },
        { status: response.status }
      )
    }

    return NextResponse.json(data)

  } catch (error) {
    console.error('Error proxying Recommended Courses request:', error)
    return NextResponse.json(
      { error: 'Failed to connect to PresGen-Assess service' },
      { status: 502 }
    )
  }
}