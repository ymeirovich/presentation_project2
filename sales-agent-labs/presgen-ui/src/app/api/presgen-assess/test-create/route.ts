import { NextRequest, NextResponse } from 'next/server'

// PresGen-Assess Backend API URL
const ASSESS_API_URL = process.env.NEXT_PUBLIC_ASSESS_API_URL || 'http://localhost:8081'

export async function POST(request: NextRequest) {
  try {
    // Test with minimal valid data
    const testData = {
      name: "Test Certification",
      version: "1.0",
      exam_domains: [
        {
          name: "Test Domain",
          weight_percentage: 100,
          subdomains: ["Test Subdomain"],
          skills_measured: ["Test Skill"]
        }
      ]
    }

    const backendUrl = `${ASSESS_API_URL}/api/v1/certifications`

    console.log('Testing certification creation with minimal data:', JSON.stringify(testData, null, 2))

    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(testData),
    })

    const data = await response.json()

    return NextResponse.json({
      test_data: testData,
      backend_url: backendUrl,
      response_status: response.status,
      response_data: data,
      success: response.ok
    })

  } catch (error) {
    console.error('Test creation error:', error)
    return NextResponse.json(
      {
        error: 'Test failed',
        details: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    )
  }
}