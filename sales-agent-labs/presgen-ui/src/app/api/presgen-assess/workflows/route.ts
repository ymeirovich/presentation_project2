import { NextRequest, NextResponse } from 'next/server'

import { ASSESS_API_URL } from '@/lib/config'

export async function GET(request: NextRequest) {
  try {
    const url = new URL(request.url)
    const searchParams = url.searchParams.toString()
    const backendUrl = `${ASSESS_API_URL}/api/v1/workflows${searchParams ? `?${searchParams}` : ''}`

    console.log('Proxying GET workflows request to:', backendUrl)

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
    console.error('Error proxying workflows to PresGen-Assess:', error)
    return NextResponse.json(
      { error: 'Failed to connect to PresGen-Assess service' },
      { status: 502 }
    )
  }
}

export async function POST(request: NextRequest) {
  try {
    const body = await request.json()
    const backendUrl = `${ASSESS_API_URL}/api/v1/workflows`

    console.log('Proxying POST workflows request to:', backendUrl)

    const response = await fetch(backendUrl, {
      method: 'POST',
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
    console.error('Error proxying workflows to PresGen-Assess:', error)
    return NextResponse.json(
      { error: 'Failed to connect to PresGen-Assess service' },
      { status: 502 }
    )
  }
}