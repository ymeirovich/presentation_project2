import { NextRequest, NextResponse } from 'next/server';

/**
 * File upload endpoint - proxies to PresGen-Assess backend
 * Backend is the single source of truth for all file operations
 */
export async function POST(request: NextRequest) {
  try {
    // Get the form data from the request
    const formData = await request.formData();
    const file = formData.get('file') as File;
    const certProfileId = formData.get('cert_profile_id') as string;
    const resourceType = formData.get('resource_type') as string;

    if (!file || !certProfileId) {
      return NextResponse.json(
        { error: 'Missing required fields: file and cert_profile_id' },
        { status: 400 }
      );
    }

    // Proxy to backend upload endpoint (FIXED: added /upload to URL)
    const backendUrl = `${process.env.PRESGEN_ASSESS_URL || 'http://localhost:8000'}/api/v1/presgen-assess/files/upload`;
    console.log(`📤 Proxying file upload to: ${backendUrl}`);
    console.log(`📄 File: ${file.name}, Size: ${file.size}, Profile: ${certProfileId}, Type: ${resourceType}`);

    const backendResponse = await fetch(backendUrl, {
      method: 'POST',
      body: formData,
    });

    if (!backendResponse.ok) {
      const errorText = await backendResponse.text();
      console.error(`❌ Backend upload failed (${backendResponse.status}):`, errorText);

      let errorDetail;
      try {
        const errorJson = JSON.parse(errorText);
        errorDetail = errorJson.detail || errorJson.error || errorText;
      } catch {
        errorDetail = errorText;
      }

      return NextResponse.json(
        {
          error: 'File upload failed',
          detail: errorDetail,
          status: backendResponse.status
        },
        { status: backendResponse.status }
      );
    }

    const responseData = await backendResponse.json();
    console.log('✅ File upload successful via backend:', responseData);
    return NextResponse.json(responseData);

  } catch (error) {
    console.error('❌ File upload error:', error);
    return NextResponse.json(
      {
        error: 'File upload failed',
        detail: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}