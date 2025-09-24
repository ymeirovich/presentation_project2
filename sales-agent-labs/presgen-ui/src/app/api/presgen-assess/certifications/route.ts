import { NextRequest, NextResponse } from 'next/server'

// PresGen-Assess Backend API URL
const ASSESS_API_URL = process.env.NEXT_PUBLIC_ASSESS_API_URL || 'http://localhost:8081'

export async function GET(request: NextRequest) {
  try {
    const url = new URL(request.url)
    const searchParams = url.searchParams.toString()
    const backendUrl = `${ASSESS_API_URL}/api/v1/certifications/${searchParams ? `?${searchParams}` : ''}`

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

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const backendUrl = `${ASSESS_API_URL}/api/v1/certifications/`

    console.log('Proxying POST request to:', backendUrl)
    console.log('Request body:', JSON.stringify(body, null, 2))

    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(body),
    })

    const data = await response.json()

    if (!response.ok) {
      console.error('PresGen-Assess API error:', {
        status: response.status,
        statusText: response.statusText,
        url: backendUrl,
        requestBody: body,
        responseData: data
      })
      return NextResponse.json(
        { detail: data.detail || data.message || `API error: ${response.status}` },
        { status: response.status }
      )
    }

    return NextResponse.json(data)

  } catch (error) {
    console.error('Error proxying to PresGen-Assess:', error)
    return NextResponse.json(
      { detail: 'Failed to connect to PresGen-Assess service' },
      { status: 502 }
    )
  }
}

