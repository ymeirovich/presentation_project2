import { NextRequest, NextResponse } from 'next/server'

import { ASSESS_API_URL } from '@/lib/config'

export async function GET(request: NextRequest) {
  try {
    // Test database connection by listing existing profiles
    const backendUrl = `${ASSESS_API_URL}/api/v1/certifications`

    console.log('Testing database connection - listing profiles:', backendUrl)

    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    const data = await response.json()

    return NextResponse.json({
      database_test: 'list_profiles',
      backend_url: backendUrl,
      response_status: response.status,
      response_data: data,
      success: response.ok,
      message: response.ok ? 'Database connection working' : 'Database connection failed'
    })

  } catch (error) {
    console.error('Database test error:', error)
    return NextResponse.json(
      {
        error: 'Database test failed',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    )
  }
}