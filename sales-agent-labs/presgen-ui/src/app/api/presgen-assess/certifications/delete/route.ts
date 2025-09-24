import { NextRequest, NextResponse } from 'next/server'

// PresGen-Assess Backend API URL
const ASSESS_API_URL = process.env.NEXT_PUBLIC_ASSESS_API_URL || 'http://localhost:8081'

export async function POST(request: NextRequest) {
  try {
    const { id } = await request.json()

    if (!id) {
      return NextResponse.json(
        { error: 'Profile ID is required' },
        { status: 400 }
      )
    }

    console.log('DELETE profile request for ID:', id)
    const backendUrl = `${ASSESS_API_URL}/api/v1/certifications/${id}`

    console.log('Proxying DELETE request to:', backendUrl)

    const response = await fetch(backendUrl, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    console.log('Backend response status:', response.status)

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
      console.log('Profile deleted successfully')
      return NextResponse.json({ success: true, message: 'Profile deleted successfully' }, { status: 200 })
    }

    // Try to parse JSON response for other success cases
    try {
      const data = await response.json()
      return NextResponse.json(data)
    } catch (e) {
      // If no JSON body, return success indicator
      return NextResponse.json({ success: true, message: 'Profile deleted successfully' })
    }

  } catch (error) {
    console.error('Error proxying to PresGen-Assess:', error)
    return NextResponse.json(
      { error: 'Failed to connect to PresGen-Assess service' },
      { status: 502 }
    )
  }
}