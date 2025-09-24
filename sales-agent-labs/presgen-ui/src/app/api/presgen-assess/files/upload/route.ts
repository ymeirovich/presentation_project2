import { NextRequest, NextResponse } from 'next/server';

/**
 * File upload endpoint - proxies to PresGen-Assess backend
 */
export async function POST(request: NextRequest) {
  try {
    // Get the form data from the request
    const formData = await request.formData();

    // Proxy the request to the PresGen-Assess backend
    const backendUrl = `${process.env.PRESGEN_ASSESS_URL || 'http://localhost:8081'}/api/v1/presgen-assess/files`;

    console.log(`Proxying file upload to: ${backendUrl}`);

    const response = await fetch(backendUrl, {
      method: 'POST',
      body: formData,
      // Don't set Content-Type header, let fetch handle it for FormData
    });

    const responseData = await response.json();

    if (!response.ok) {
      console.error('Backend file upload error:', response.status, responseData);
      return NextResponse.json(
        {
          error: 'File upload failed',
          detail: responseData.detail || 'Unknown error',
          status: response.status
        },
        { status: response.status }
      );
    }

    console.log('File upload successful:', responseData);
    return NextResponse.json(responseData);

  } catch (error) {
    console.error('File upload error:', error);
    return NextResponse.json(
      {
        error: 'File upload failed',
        detail: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}