import { NextRequest, NextResponse } from 'next/server'

const ASSESS_API_URL = process.env.NEXT_PUBLIC_PRESGEN_ASSESS_URL || 'http://localhost:8000'

export async function POST(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params

  if (!id) {
    console.error('Resume workflow proxy missing id parameter')
    return NextResponse.json({ error: 'Workflow id is required' }, { status: 400 })
  }

  const backendUrl = `${ASSESS_API_URL}/api/v1/workflows/${encodeURIComponent(id)}/resume-paused`
  console.log('Proxying POST resume workflow request to:', backendUrl)

  try {
    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    const data = await response.json()

    if (!response.ok) {
      console.error('PresGen-Assess API error (resume):', response.status, data)
      return NextResponse.json(
        { error: data.detail || `API error: ${response.status}` },
        { status: response.status }
      )
    }

    return NextResponse.json(data)
  } catch (error) {
    console.error('Error proxying resume workflow to PresGen-Assess:', error)
    return NextResponse.json(
      { error: 'Failed to connect to PresGen-Assess service' },
      { status: 502 }
    )
  }
}
