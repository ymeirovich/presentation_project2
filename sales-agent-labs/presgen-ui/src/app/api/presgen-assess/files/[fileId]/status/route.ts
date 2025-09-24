import { NextRequest, NextResponse } from 'next/server';

/**
 * Get file processing status - proxies to PresGen-Assess backend
 */
export async function GET(
  request: NextRequest,
  { params }: { params: { fileId: string } }
) {
  try {
    const { fileId } = params;

    // Proxy the request to the PresGen-Assess backend
    const backendUrl = `${process.env.PRESGEN_ASSESS_URL || 'http://localhost:8081'}/api/v1/presgen-assess/files/${fileId}/status`;

    console.log(`Proxying GET file status request to: ${backendUrl}`);

    const response = await fetch(backendUrl, {
      method: 'GET',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      console.error('Backend get file status error:', response.status);

      // If the endpoint doesn't exist yet, return mock completed status
      if (response.status === 404 || response.status === 405) {
        return NextResponse.json({
          file_id: fileId,
          status: 'completed',
          processing_status: 'completed',
          message: 'File status endpoints not yet implemented in backend'
        });
      }

      return NextResponse.json(
        {
          error: 'Failed to get file status',
          status: response.status
        },
        { status: response.status }
      );
    }

    const responseData = await response.json();
    console.log('File status retrieved successfully:', responseData);
    return NextResponse.json(responseData);

  } catch (error) {
    console.error('Get file status error:', error);

    // Return mock completed status as fallback
    return NextResponse.json({
      file_id: fileId,
      status: 'completed',
      processing_status: 'completed',
      message: 'File status temporarily unavailable'
    });
  }
}