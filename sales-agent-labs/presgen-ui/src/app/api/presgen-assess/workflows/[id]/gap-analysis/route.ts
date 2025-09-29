import { NextRequest, NextResponse } from 'next/server'

const ASSESS_API_URL = process.env.NEXT_PUBLIC_ASSESS_API_URL || 'http://localhost:8081'

export async function GET(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params

  if (!id) {
    console.error('Workflow gap analysis proxy missing id parameter')
    return NextResponse.json({ error: 'Workflow id is required' }, { status: 400 })
  }

  const backendUrl = `${ASSESS_API_URL}/api/v1/workflows/${encodeURIComponent(id)}/gap-analysis`
  console.log('Proxying GET workflow gap analysis request to:', backendUrl)

  try {
    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      cache: 'no-store',
    })

    const text = await response.text()
    const data = text ? JSON.parse(text) : {}

    if (!response.ok) {
      console.error('PresGen-Assess API error (gap-analysis):', response.status, data)
      return NextResponse.json(
        { error: data.detail || `API error: ${response.status}` },
        { status: response.status }
      )
    }

    return NextResponse.json(data)
  } catch (error) {
    console.error('Error proxying workflow gap analysis to PresGen-Assess:', error)
    return NextResponse.json(
      { error: 'Failed to connect to PresGen-Assess service' },
      { status: 502 }
    )
  }
}
