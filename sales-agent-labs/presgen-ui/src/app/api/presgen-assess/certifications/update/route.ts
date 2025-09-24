import { NextRequest, NextResponse } from 'next/server'

// PresGen-Assess Backend API URL
const ASSESS_API_URL = process.env.NEXT_PUBLIC_ASSESS_API_URL || 'http://localhost:8081'

export async function POST(request: NextRequest) {
  try {
    const { id, ...updateData } = await request.json()

    if (!id) {
      return NextResponse.json(
        { error: 'Profile ID is required' },
        { status: 400 }
      )
    }

    console.log('UPDATE profile request for ID:', id)
    console.log('Update data:', JSON.stringify(updateData, null, 2))

    // Get the original profile to preserve timestamps
    const getUrl = `${ASSESS_API_URL}/api/v1/certifications/${id}`
    const getResponse = await fetch(getUrl)

    if (!getResponse.ok) {
      return NextResponse.json(
        { error: 'Profile not found' },
        { status: 404 }
      )
    }

    const originalProfile = await getResponse.json()

    // Convert API schema to database schema (same as create logic)
    const db_exam_domains = []
    for (const domain of updateData.exam_domains || []) {
      const db_domain = {
        'name': domain.name,
        'weight_percentage': domain.weight_percentage,
        'subdomains': domain.topics?.slice(0, Math.floor(domain.topics.length/2)) || [],
        'skills_measured': domain.topics?.slice(Math.floor(domain.topics.length/2)) || []
      }
      db_exam_domains.push(db_domain)
    }

    // Store additional form fields in assessment_template as metadata
    let assessment_template = updateData.assessment_template || {}
    if (typeof assessment_template !== 'object') {
      assessment_template = {}
    }

    assessment_template['_metadata'] = {
      'provider': updateData.provider,
      'description': updateData.description || null,
      'exam_code': updateData.exam_code || null,
      'passing_score': updateData.passing_score || null,
      'exam_duration_minutes': updateData.exam_duration_minutes || null,
      'question_count': updateData.question_count || null,
      'prerequisites': updateData.prerequisites || [],
      'recommended_experience': updateData.recommended_experience || null,
      'is_active': updateData.is_active !== undefined ? updateData.is_active : true
    }

    // First, delete the existing profile
    const deleteUrl = `${ASSESS_API_URL}/api/v1/certifications/${id}`
    const deleteResponse = await fetch(deleteUrl, { method: 'DELETE' })

    if (!deleteResponse.ok && deleteResponse.status !== 204) {
      console.error('Failed to delete original profile:', deleteResponse.status)
      return NextResponse.json(
        { error: 'Failed to update profile' },
        { status: 500 }
      )
    }

    // Create profile data for database model (only include fields that exist in DB model)
    const db_profile_data = {
      'name': updateData.name,
      'version': updateData.version,
      'exam_domains': db_exam_domains,
      'knowledge_base_path': `knowledge_base/${updateData.name.toLowerCase().replace(/ /g, '_')}_v${updateData.version}`,
      'assessment_template': assessment_template
    }

    // Create new profile using our own create endpoint (which handles schema conversion)
    const createUrl = 'http://localhost:3000/api/presgen-assess/certifications'
    const createResponse = await fetch(createUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(updateData), // Use the original form data
    })

    if (!createResponse.ok) {
      let data;
      try {
        data = await createResponse.json()
      } catch (e) {
        data = { detail: 'Unknown error' }
      }
      console.error('PresGen-Assess API error:', createResponse.status, data)
      return NextResponse.json(
        { error: data.detail || `API error: ${createResponse.status}` },
        { status: createResponse.status }
      )
    }

    // Parse and return the response from the create endpoint
    const newProfile = await createResponse.json()
    console.log('Profile recreated with new ID:', newProfile.id)

    return NextResponse.json(newProfile)

  } catch (error) {
    console.error('Error proxying to PresGen-Assess:', error)
    return NextResponse.json(
      { error: 'Failed to connect to PresGen-Assess service' },
      { status: 502 }
    )
  }
}