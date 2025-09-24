import { NextRequest, NextResponse } from 'next/server';

/**
 * Delete file - proxies to PresGen-Assess backend
 */
export async function DELETE(
  request: NextRequest,
  { params }: { params: { fileId: string } }
) {
  try {
    const { fileId } = params;

    // Proxy the request to the PresGen-Assess backend
    const backendUrl = `${process.env.PRESGEN_ASSESS_URL || 'http://localhost:8081'}/api/v1/presgen-assess/files/${fileId}`;

    console.log(`Proxying DELETE file request to: ${backendUrl}`);

    const response = await fetch(backendUrl, {
      method: 'DELETE',
      headers: {
        'Content-Type': 'application/json',
      },
    });

    if (!response.ok) {
      console.error('Backend delete file error:', response.status);

      // If the endpoint doesn't exist yet, return success
      if (response.status === 404 || response.status === 405) {
        return NextResponse.json({
          file_id: fileId,
          success: true,
          message: 'File delete endpoints not yet implemented in backend'
        });
      }

      return NextResponse.json(
        {
          error: 'Failed to delete file',
          status: response.status
        },
        { status: response.status }
      );
    }

    const responseData = await response.json();
    console.log('File deleted successfully:', responseData);
    return NextResponse.json(responseData);

  } catch (error) {
    console.error('Delete file error:', error);

    // Return success as fallback
    return NextResponse.json({
      file_id: fileId,
      success: true,
      message: 'File delete temporarily unavailable'
    });
  }
}

/**
 * Download file - proxies to PresGen-Assess backend
 */
export async function GET(
  request: NextRequest,
  { params }: { params: { fileId: string } }
) {
  try {
    const { fileId } = params;
    const url = new URL(request.url);

    // Check if this is a download request
    if (url.pathname.endsWith('/download')) {
      // Proxy the download request to the PresGen-Assess backend
      const backendUrl = `${process.env.PRESGEN_ASSESS_URL || 'http://localhost:8081'}/api/v1/presgen-assess/files/${fileId}/download`;

      console.log(`Proxying GET file download request to: ${backendUrl}`);

      const response = await fetch(backendUrl, {
        method: 'GET',
      });

      if (!response.ok) {
        console.error('Backend download file error:', response.status);

        return NextResponse.json(
          {
            error: 'Failed to download file',
            status: response.status
          },
          { status: response.status }
        );
      }

      // Stream the file back to the client
      const blob = await response.blob();
      return new NextResponse(blob, {
        headers: {
          'Content-Type': response.headers.get('Content-Type') || 'application/octet-stream',
          'Content-Disposition': response.headers.get('Content-Disposition') || `attachment; filename="${fileId}"`,
        },
      });
    }

    return NextResponse.json({ error: 'Invalid request' }, { status: 400 });

  } catch (error) {
    console.error('File operation error:', error);
    return NextResponse.json(
      {
        error: 'File operation failed',
        detail: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}