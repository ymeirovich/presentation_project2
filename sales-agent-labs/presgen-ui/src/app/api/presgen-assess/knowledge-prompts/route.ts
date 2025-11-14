import { NextRequest, NextResponse } from 'next/server'

// PresGen-Assess Backend API URL
const ASSESS_API_URL = process.env.NEXT_PUBLIC_ASSESS_API_URL || '""'

export async function POST(request: NextRequest) {
  try {
    const createData = await request.json()
    const backendUrl = `${ASSESS_API_URL}/api/v1/knowledge-prompts/`

    console.log('🗂️ PROXY: POST create knowledge-prompts:', createData)

    const response = await fetch(backendUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(createData),
    })

    const data = await response.json()

    if (!response.ok) {
      console.error('🗂️ PROXY: Knowledge prompts POST API error:', response.status, data)
      return NextResponse.json(
        { error: data.detail || `API error: ${response.status}` },
        { status: response.status }
      )
    }

    console.log('🗂️ PROXY: Successfully created knowledge base prompts:', createData.collection_name)
    return NextResponse.json(data)

  } catch (error) {
    console.error('🗂️ PROXY: Error proxying knowledge prompts POST:', error)
    return NextResponse.json(
      { error: 'Failed to connect to PresGen-Assess service' },
      { status: 502 }
    )
  }
}

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url)
    const backendUrl = `${ASSESS_API_URL}/api/v1/knowledge-prompts/?${searchParams.toString()}`

    console.log('🗂️ PROXY: GET list knowledge-prompts')

    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    const data = await response.json()

    if (!response.ok) {
      console.error('🗂️ PROXY: Knowledge prompts list API error:', response.status, data)
      return NextResponse.json(
        { error: data.detail || `API error: ${response.status}` },
        { status: response.status }
      )
    }

    console.log('🗂️ PROXY: Successfully listed knowledge base prompts')
    return NextResponse.json(data)

  } catch (error) {
    console.error('🗂️ PROXY: Error proxying knowledge prompts list:', error)
    return NextResponse.json(
      { error: 'Failed to connect to PresGen-Assess service' },
      { status: 502 }
    )
  }
}