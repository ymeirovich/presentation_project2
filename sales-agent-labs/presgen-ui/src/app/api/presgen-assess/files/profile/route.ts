import { NextRequest, NextResponse } from 'next/server';

/**
 * Get files for a specific certification profile - proxies to PresGen-Assess backend
 * Expects profileId as a query parameter
 */
export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const profileId = searchParams.get('profileId');

    if (!profileId) {
      return NextResponse.json(
        { error: 'profileId query parameter is required' },
        { status: 400 }
      );
    }

    // Proxy the request to the PresGen-Assess backend
    const backendUrl = `${process.env.PRESGEN_ASSESS_URL || 'http://localhost:8081'}/api/v1/presgen-assess/files/profile/${profileId}`;

    console.log(`Proxying GET files request to: ${backendUrl}`);

    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      console.error('Backend get files error:', response.status);

      // If the endpoint doesn't exist yet, return empty files list
      if (response.status === 404 || response.status === 405) {
        return NextResponse.json({
          files: [],
          total: 0,
          profileId: profileId,
          message: 'File management endpoints not yet implemented in backend'
        });
      }

      return NextResponse.json(
        {
          error: 'Failed to retrieve files',
          status: response.status
        },
        { status: response.status }
      );
    }

    const responseData = await response.json();
    console.log('Files retrieved successfully:', responseData);
    return NextResponse.json(responseData);

  } catch (error) {
    console.error('Get files error:', error);

    // Return empty files list as fallback
    return NextResponse.json({
      files: [],
      total: 0,
      message: 'File retrieval temporarily unavailable'
    });
  }
}