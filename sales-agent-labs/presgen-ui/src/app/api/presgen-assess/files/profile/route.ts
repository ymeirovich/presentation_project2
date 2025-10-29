import { NextRequest, NextResponse } from 'next/server';

/**
 * Get files for a specific certification profile
 * Proxies to PresGen-Assess backend - single source of truth
 * Expects profileId as a query parameter
 */
export async function GET(request: NextRequest) {
  let profileId: string | null = null;

  try {
    const { searchParams } = new URL(request.url);
    profileId = searchParams.get('profileId');

    if (!profileId) {
      return NextResponse.json(
        { error: 'profileId query parameter is required' },
        { status: 400 }
      );
    }

    // Try backend first
    const backendUrl = `${process.env.PRESGEN_ASSESS_URL || 'http://localhost:8000'}/api/v1/presgen-assess/files/profile/${profileId}`;
    console.log(`Proxying GET files request to: ${backendUrl}`);

    let backendResponse;
    try {
      backendResponse = await fetch(backendUrl, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
    } catch (backendError) {
      console.log('Backend not available, using mock storage');
    }

    // If backend is available and successful, use its response
    if (backendResponse && backendResponse.ok) {
      const responseData = await backendResponse.json();
      console.log(`✅ Files retrieved successfully from backend: ${responseData.files?.length || 0} files for profile ${profileId}`);
      return NextResponse.json(responseData);
    }

    // Backend failed - return error (no mock storage fallback)
    if (backendResponse) {
      const errorText = await backendResponse.text();
      console.error(`❌ Backend get files failed (${backendResponse.status}):`, errorText);
      return NextResponse.json({
        files: [],
        total: 0,
        profileId: profileId,
        message: 'Failed to retrieve files from backend',
        error: errorText
      }, { status: backendResponse.status });
    }

    // Backend not available at all
    return NextResponse.json({
      files: [],
      total: 0,
      profileId: profileId,
      message: 'Backend not available'
    }, { status: 503 });

  } catch (error) {
    console.error('Get files error:', error);

    // Return empty files list as fallback
    return NextResponse.json({
      files: [],
      total: 0,
      profileId: profileId || 'unknown',
      message: 'File retrieval temporarily unavailable',
      error: error instanceof Error ? error.message : 'Unknown error'
    });
  }
}