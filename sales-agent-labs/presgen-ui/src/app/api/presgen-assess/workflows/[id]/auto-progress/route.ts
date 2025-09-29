import { NextRequest, NextResponse } from 'next/server'

const ASSESS_API_URL = process.env.NEXT_PUBLIC_ASSESS_API_URL || 'http://localhost:8081'

export async function POST(_request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params

  if (!id) {
    console.error('Auto-progress proxy missing id parameter')
    return NextResponse.json({ error: 'Workflow id is required' }, { status: 400 })
  }

  const backendUrl = `${ASSESS_API_URL}/api/v1/workflows/${encodeURIComponent(id)}/auto-progress`
  console.log('Proxying POST auto-progress request to:', backendUrl)

  try {
    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    const data = await response.json()

    if (!response.ok) {
      console.error('PresGen-Assess API error (auto-progress):', response.status, data)
      return NextResponse.json(
        { error: data.detail || `API error: ${response.status}` },
        { status: response.status }
      )
    }

    return NextResponse.json(data)
  } catch (error) {
    console.error('Error proxying auto-progress to PresGen-Assess:', error)
    return NextResponse.json(
      { error: 'Failed to connect to PresGen-Assess service' },
      { status: 502 }
    )
  }
}