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

    // Transform backend data to include form fields from assessment_template
    const transformedData = { ...data }

    if (data.assessment_template) {
      // Extract ChromaDB prompts if they exist
      const chromadbPrompts = data.assessment_template._chromadb_prompts || {}
      transformedData.assessment_prompt = chromadbPrompts.assessment_prompt || ''
      transformedData.presentation_prompt = chromadbPrompts.presentation_prompt || ''
      transformedData.gap_analysis_prompt = chromadbPrompts.gap_analysis_prompt || ''
      transformedData.bundle_version = chromadbPrompts.bundle_version || 'v1.0'
      transformedData.resource_binding_enabled = chromadbPrompts.resource_binding_enabled !== undefined
        ? chromadbPrompts.resource_binding_enabled : true

      // Extract metadata fields if they exist
      const metadata = data.assessment_template._metadata || {}
      transformedData.provider = metadata.provider || data.provider || ''
      transformedData.description = metadata.description || data.description || ''
      transformedData.exam_code = metadata.exam_code || data.exam_code || ''
      transformedData.passing_score = metadata.passing_score || data.passing_score
      transformedData.exam_duration_minutes = metadata.exam_duration_minutes || data.exam_duration_minutes
      transformedData.question_count = metadata.question_count || data.question_count
      transformedData.prerequisites = metadata.prerequisites || data.prerequisites || []
      transformedData.recommended_experience = metadata.recommended_experience || data.recommended_experience || ''
      transformedData.is_active = metadata.is_active !== undefined ? metadata.is_active : (data.is_active !== undefined ? data.is_active : true)
    }

    // Transform exam_domains back to form format (merge subdomains and skills_measured into topics)
    if (data.exam_domains) {
      transformedData.exam_domains = data.exam_domains.map(domain => ({
        name: domain.name,
        weight_percentage: domain.weight_percentage,
        topics: [...(domain.subdomains || []), ...(domain.skills_measured || [])]
      }))
    }

    console.log('Returning transformed profile data:', JSON.stringify(transformedData, null, 2))

    return NextResponse.json(transformedData)

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
    const updateData = await request.json()
    const backendUrl = `${ASSESS_API_URL}/api/v1/certifications/${id}`

    console.log('Proxying PUT request to:', backendUrl)
    console.log('Update data received:', JSON.stringify(updateData, null, 2))

    // Transform data similar to create/update logic to preserve custom fields
    const db_exam_domains = []
    for (const domain of updateData.exam_domains || []) {
      // Ensure topics is always an array
      const topics = Array.isArray(domain.topics) ? domain.topics :
                     (typeof domain.topics === 'string' ?
                      domain.topics.split(',').map((t: string) => t.trim()).filter((t: string) => t) : [])

      const db_domain = {
        'name': domain.name,
        'weight_percentage': domain.weight_percentage,
        'topics': topics, // Backend expects topics field
        'subdomains': topics.slice(0, Math.floor(topics.length/2)) || [],
        'skills_measured': topics.slice(Math.floor(topics.length/2)) || []
      }
      db_exam_domains.push(db_domain)
    }

    // Store ChromaDB fields and additional metadata in assessment_template
    const assessment_template = {
      _chromadb_prompts: {
        assessment_prompt: updateData.assessment_prompt,
        presentation_prompt: updateData.presentation_prompt,
        gap_analysis_prompt: updateData.gap_analysis_prompt,
        bundle_version: updateData.bundle_version,
        resource_binding_enabled: updateData.resource_binding_enabled
      },
      _metadata: {
        provider: updateData.provider,
        description: updateData.description || null,
        exam_code: updateData.exam_code || null,
        passing_score: updateData.passing_score || null,
        exam_duration_minutes: updateData.exam_duration_minutes || null,
        question_count: updateData.question_count || null,
        prerequisites: updateData.prerequisites || [],
        recommended_experience: updateData.recommended_experience || null,
        is_active: updateData.is_active !== undefined ? updateData.is_active : true
      }
    }

    // Create profile data for backend, only including fields that are actually present
    const backendData: Record<string, unknown> = {}

    const setIfDefined = (key: string, value: unknown) => {
      if (value !== undefined) {
        backendData[key] = value
      }
    }

    setIfDefined('name', updateData.name)
    setIfDefined('version', updateData.version)

    if (updateData.exam_domains !== undefined) {
      backendData.exam_domains = db_exam_domains
    }

    if (updateData.knowledge_base_path) {
      backendData.knowledge_base_path = updateData.knowledge_base_path
    } else if (updateData.name && updateData.version) {
      backendData.knowledge_base_path = `knowledge_base/${updateData.name.toLowerCase().replace(/ /g, '_')}_v${updateData.version}`
    }

    // Persist prompt fields directly so they reach the backend columns
    setIfDefined('assessment_prompt', updateData.assessment_prompt)
    setIfDefined('presentation_prompt', updateData.presentation_prompt)
    setIfDefined('gap_analysis_prompt', updateData.gap_analysis_prompt)
    setIfDefined('resource_binding_enabled', updateData.resource_binding_enabled)

    // Preserve assessment template metadata only when we have content to update
    const chromaPrompts = Object.fromEntries(
      Object.entries({
        assessment_prompt: updateData.assessment_prompt,
        presentation_prompt: updateData.presentation_prompt,
        gap_analysis_prompt: updateData.gap_analysis_prompt,
        bundle_version: updateData.bundle_version,
        resource_binding_enabled: updateData.resource_binding_enabled
      }).filter(([, value]) => value !== undefined && value !== '')
    )

    const metadataFields = Object.fromEntries(
      Object.entries({
        provider: updateData.provider,
        description: updateData.description ?? null,
        exam_code: updateData.exam_code ?? null,
        passing_score: updateData.passing_score ?? null,
        exam_duration_minutes: updateData.exam_duration_minutes ?? null,
        question_count: updateData.question_count ?? null,
        prerequisites: updateData.prerequisites ?? [],
        recommended_experience: updateData.recommended_experience ?? null,
        is_active: updateData.is_active !== undefined ? updateData.is_active : undefined
      }).filter(([, value]) => value !== undefined)
    )

    if (Object.keys(chromaPrompts).length > 0 || Object.keys(metadataFields).length > 0) {
      backendData.assessment_template = {
        _chromadb_prompts: Object.keys(chromaPrompts).length > 0 ? chromaPrompts : undefined,
        _metadata: Object.keys(metadataFields).length > 0 ? metadataFields : undefined
      }
    }

    console.log('Sending to backend:', JSON.stringify(backendData, null, 2))

    const response = await fetch(backendUrl, {
      method: 'PUT',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(backendData),
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
