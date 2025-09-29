import { NextRequest, NextResponse } from 'next/server'

const ASSESS_API_URL = process.env.NEXT_PUBLIC_ASSESS_API_URL || 'http://localhost:8081'

export async function POST(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params

  if (!id) {
    console.error('Gap analysis Sheets export proxy missing workflow id')
    return NextResponse.json({ error: 'Workflow id is required' }, { status: 400 })
  }

  const backendUrl = `${ASSESS_API_URL}/api/v1/workflows/${encodeURIComponent(id)}/gap-analysis/export-to-sheets`
  console.log('Proxying POST workflow gap analysis export to:', backendUrl)

  try {
    const body = await request.json().catch(() => ({}))

    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
      cache: 'no-store',
    })

    const text = await response.text()
    const data = text ? JSON.parse(text) : {}

    if (!response.ok) {
      console.error('PresGen-Assess API error (gap-analysis export-to-sheets):', response.status, data)
      return NextResponse.json(
        { error: data.detail || `API error: ${response.status}`, details: data },
        { status: response.status }
      )
    }

    return NextResponse.json(data)
  } catch (error) {
    console.error('Error proxying gap analysis export-to-sheets request:', error)
    return NextResponse.json(
      { error: 'Failed to connect to PresGen-Assess service' },
      { status: 502 }
    )
  }
}
