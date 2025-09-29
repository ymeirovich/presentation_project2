import { NextRequest, NextResponse } from 'next/server'

const ASSESS_API_URL = process.env.NEXT_PUBLIC_ASSESS_API_URL || 'http://localhost:8081'

export async function GET(request: NextRequest, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params

  if (!id) {
    console.error('Gap analysis export proxy missing workflow id')
    return NextResponse.json({ error: 'Workflow id is required' }, { status: 400 })
  }

  const format = request.nextUrl.searchParams.get('format') || 'json'
  const backendUrl = `${ASSESS_API_URL}/api/v1/workflows/${encodeURIComponent(id)}/gap-analysis/export?format=${encodeURIComponent(format)}`
  console.log('Proxying GET workflow gap analysis export to:', backendUrl)

  try {
    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
      cache: 'no-store',
    })

    if (!response.ok) {
      const text = await response.text()
      console.error('PresGen-Assess API error (gap-analysis export):', response.status, text)
      return NextResponse.json(
        { error: `API error: ${response.status}`, details: text },
        { status: response.status }
      )
    }

    const buffer = await response.arrayBuffer()
    const contentType = response.headers.get('content-type') || 'application/octet-stream'
    const contentDisposition = response.headers.get('content-disposition') || undefined

    return new NextResponse(buffer, {
      status: 200,
      headers: {
        'Content-Type': contentType,
        ...(contentDisposition ? { 'Content-Disposition': contentDisposition } : {}),
      },
    })
  } catch (error) {
    console.error('Error proxying gap analysis export request:', error)
    return NextResponse.json(
      { error: 'Failed to connect to PresGen-Assess service' },
      { status: 502 }
    )
  }
}
