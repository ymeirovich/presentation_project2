import { NextRequest, NextResponse } from 'next/server';

/**
 * Download file - proxies to PresGen-Assess backend
 */
export async function GET(
  request: NextRequest,
  { params }: { params: { fileId: string } }
) {
  try {
    const { fileId } = params;

    // Proxy the download request to the PresGen-Assess backend
    const backendUrl = `${process.env.PRESGEN_ASSESS_URL || 'http://localhost:8081'}/api/v1/presgen-assess/files/${fileId}/download`;

    console.log(`Proxying GET file download request to: ${backendUrl}`);

    const response = await fetch(backendUrl, {
      method: 'GET',
    });

    if (!response.ok) {
      console.error('Backend download file error:', response.status);

      // If the endpoint doesn't exist yet, return a mock file
      if (response.status === 404 || response.status === 405) {
        const mockContent = `Mock file content for ${fileId}\n\nThis is a placeholder until the backend file storage is implemented.`;

        return new NextResponse(mockContent, {
          headers: {
            'Content-Type': 'text/plain',
            'Content-Disposition': `attachment; filename="file-${fileId}.txt"`,
          },
        });
      }

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

  } catch (error) {
    console.error('File download error:', error);

    // Return a mock file as fallback
    const mockContent = `Error downloading file ${params.fileId}\n\nError: ${error instanceof Error ? error.message : 'Unknown error'}`;

    return new NextResponse(mockContent, {
      status: 500,
      headers: {
        'Content-Type': 'text/plain',
        'Content-Disposition': `attachment; filename="error-${params.fileId}.txt"`,
      },
    });
  }
}