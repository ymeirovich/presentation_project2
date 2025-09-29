import { NextRequest, NextResponse } from 'next/server'

// PresGen-Assess Backend API URL
const ASSESS_API_URL = process.env.NEXT_PUBLIC_ASSESS_API_URL || 'http://localhost:8080'

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ collection_name: string }> }
) {
  try {
    const { collection_name } = await params
    const backendUrl = `${ASSESS_API_URL}/api/v1/knowledge-prompts/${collection_name}`

    console.log('🗂️ PROXY: GET knowledge-prompts for collection:', collection_name)

    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    })

    const data = await response.json()

    if (!response.ok) {
      console.error('🗂️ PROXY: Knowledge prompts API error:', response.status, data)
      return NextResponse.json(
        { error: data.detail || `API error: ${response.status}` },
        { status: response.status }
      )
    }

    console.log('🗂️ PROXY: Successfully retrieved knowledge base prompts:', collection_name)
    return NextResponse.json(data)

  } catch (error) {
    console.error('🗂️ PROXY: Error proxying knowledge prompts GET:', error)
    return NextResponse.json(
      { error: 'Failed to connect to PresGen-Assess service' },
      { status: 502 }
    )
  }
}

export async function PUT(
  request: NextRequest,
  { params }: { params: Promise<{ collection_name: string }> }
) {
  try {
    const { collection_name } = await params
    const updateData = await request.json()
    const backendUrl = `${ASSESS_API_URL}/api/v1/knowledge-prompts/${collection_name}`

    console.log('🗂️ PROXY: PUT knowledge-prompts for collection:', collection_name, updateData)

    const response = await fetch(backendUrl, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(updateData),
    })

    const data = await response.json()

    if (!response.ok) {
      console.error('🗂️ PROXY: Knowledge prompts PUT API error:', response.status, data)
      return NextResponse.json(
        { error: data.detail || `API error: ${response.status}` },
        { status: response.status }
      )
    }

    console.log('🗂️ PROXY: Successfully updated knowledge base prompts:', collection_name)
    return NextResponse.json(data)

  } catch (error) {
    console.error('🗂️ PROXY: Error proxying knowledge prompts PUT:', error)
    return NextResponse.json(
      { error: 'Failed to connect to PresGen-Assess service' },
      { status: 502 }
    )
  }
}

export async function DELETE(
  request: NextRequest,
  { params }: { params: Promise<{ collection_name: string }> }
) {
  try {
    const { collection_name } = await params
    const backendUrl = `${ASSESS_API_URL}/api/v1/knowledge-prompts/${collection_name}`

    console.log('🗂️ PROXY: DELETE knowledge-prompts for collection:', collection_name)

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
      console.error('🗂️ PROXY: Knowledge prompts DELETE API error:', response.status, data)
      return NextResponse.json(
        { error: data.detail || `API error: ${response.status}` },
        { status: response.status }
      )
    }

    console.log('🗂️ PROXY: Successfully deleted knowledge base prompts:', collection_name)

    // Handle 204 No Content responses
    if (response.status === 204) {
      return NextResponse.json({ success: true }, { status: 200 })
    }

    try {
      const data = await response.json()
      return NextResponse.json(data)
    } catch (e) {
      return NextResponse.json({ success: true })
    }

  } catch (error) {
    console.error('🗂️ PROXY: Error proxying knowledge prompts DELETE:', error)
    return NextResponse.json(
      { error: 'Failed to connect to PresGen-Assess service' },
      { status: 502 }
    )
  }
}