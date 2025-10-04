import { NextRequest, NextResponse } from 'next/server'
import { ASSESS_API_URL } from '@/lib/config'

export async function GET(request: NextRequest) {
  try {
    const backendUrl = `${ASSESS_API_URL}/health`

    console.log('Testing PresGen-Assess health at:', backendUrl)

    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    const data = await response.json()

    if (!response.ok) {
      console.error('PresGen-Assess health check failed:', response.status, data)
      return NextResponse.json(
        { error: `Health check failed: ${response.status}`, backend_url: backendUrl },
        { status: response.status }
      )
    }

    console.log('PresGen-Assess health check success:', data)
    return NextResponse.json({
      ...data,
      backend_url: backendUrl,
      proxy_status: 'working'
    })

  } catch (error) {
    console.error('Error connecting to PresGen-Assess:', error)
    return NextResponse.json(
      {
        error: 'Failed to connect to PresGen-Assess service',
        backend_url: ASSESS_API_URL,
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 502 }
    )
  }
}