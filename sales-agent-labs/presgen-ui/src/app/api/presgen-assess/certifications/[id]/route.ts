import { NextRequest, NextResponse } from 'next/server'

// PresGen-Assess Backend API URL
const ASSESS_API_URL = process.env.NEXT_PUBLIC_ASSESS_API_URL || 'http://localhost:8081'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params
    const backendUrl = `${ASSESS_API_URL}/api/v1/certifications/${id}`

    console.log('Proxying GET request to:', backendUrl)

    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    const data = await response.json()

    if (!response.ok) {
      console.error('PresGen-Assess API error:', response.status, data)
      return NextResponse.json(
        { error: data.detail || `API error: ${response.status}` },
        { status: response.status }
      )
    }

    return NextResponse.json(data)

  } catch (error) {
    console.error('Error proxying to PresGen-Assess:', error)
    return NextResponse.json(
      { error: 'Failed to connect to PresGen-Assess service' },
      { status: 502 }
    )
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ id: string }> }
) {
  try {
    const { id } = await params
    const body = await request.json()
    const backendUrl = `${ASSESS_API_URL}/api/v1/certifications/${id}`

    console.log('Proxying PUT request to:', backendUrl)

    const response = await fetch(backendUrl, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })

    const data = await response.json()

    if (!response.ok) {
      console.error('PresGen-Assess API error:', response.status, data)
      return NextResponse.json(
        { error: data.detail || `API error: ${response.status}` },
        { status: response.status }
      )
    }

    return NextResponse.json(data)

  } catch (error) {
    console.error('Error proxying to PresGen-Assess:', error)
    return NextResponse.json(
      { error: 'Failed to connect to PresGen-Assess service' },
      { status: 502 }
    )
  }
}

export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ id: string }> }
) {
  try {
    console.log('DELETE request received in dynamic route')
    const { id } = await context.params
    console.log('Profile ID to delete:', id)

    const backendUrl = `${ASSESS_API_URL}/api/v1/certifications/${id}`

    console.log('Proxying DELETE request to:', backendUrl)

    const response = await fetch(backendUrl, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    if (!response.ok) {
      let data;
      try {
        data = await response.json()
      } catch (e) {
        data = { detail: 'Unknown error' }
      }
      console.error('PresGen-Assess API error:', response.status, data)
      return NextResponse.json(
        { error: data.detail || `API error: ${response.status}` },
        { status: response.status }
      )
    }

    // Handle 204 No Content responses (successful deletes)
    if (response.status === 204) {
      return NextResponse.json({ success: true }, { status: 200 })
    }

    // Try to parse JSON response for other success cases
    try {
      const data = await response.json()
      return NextResponse.json(data)
    } catch (e) {
      // If no JSON body, return success indicator
      return NextResponse.json({ success: true })
    }

  } catch (error) {
    console.error('Error proxying to PresGen-Assess:', error)
    return NextResponse.json(
      { error: 'Failed to connect to PresGen-Assess service' },
      { status: 502 }
    )
  }
}