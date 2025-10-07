import { NextRequest, NextResponse } from 'next/server'

const ASSESS_API_URL = process.env.NEXT_PUBLIC_ASSESS_API_URL || 'http://localhost:8000'

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

  const backendUrl = `${ASSESS_API_URL}/api/v1/workflows/${encodeURIComponent(id)}/courses/${encodeURIComponent(courseId)}/video`

  try {
    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      const text = await response.text()
      const detail = (() => {
        try {
          const parsed = JSON.parse(text)
          if (parsed && typeof parsed === 'object' && 'detail' in parsed) {
            return parsed.detail
          }
        } catch (error) {
          // ignore parse errors, fall through to default message
        }
        return `API error: ${response.status}`
      })()
      return NextResponse.json({ error: detail }, { status: response.status })
    }

    const arrayBuffer = await response.arrayBuffer()
    return new NextResponse(arrayBuffer, {
      status: 200,
      headers: {
        'Content-Type': 'video/mp4',
        'Content-Disposition': `attachment; filename="avatar-${courseId}.mp4"`,
      },
    })
  } catch (error) {
    console.error('Error proxying video download:', error)
    return NextResponse.json(
      { error: 'Failed to retrieve course video' },
      { status: 502 }
    )
  }
}
