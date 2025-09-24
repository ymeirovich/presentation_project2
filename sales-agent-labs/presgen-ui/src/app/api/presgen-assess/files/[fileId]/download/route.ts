import { NextRequest, NextResponse } from 'next/server';
import { MockFileStorage } from '@/lib/mock-file-storage';

/**
 * Download file - proxies to PresGen-Assess backend
 */
export async function GET(
  request: NextRequest,
  context: { params: Promise<{ fileId: string }> }
) {
  try {
    const { fileId } = await context.params;

    // Proxy the download request to the PresGen-Assess backend
    const backendUrl = `${process.env.PRESGEN_ASSESS_URL || 'http://localhost:8081'}/api/v1/presgen-assess/files/${fileId}/download`;

    console.log(`Proxying GET file download request to: ${backendUrl}`);

    const response = await fetch(backendUrl, {
      method: 'GET',
    });

    if (!response.ok) {
      console.error('Backend download file error:', response.status);

      // If the endpoint doesn't exist yet, try mock storage
      if (response.status === 404 || response.status === 405) {
        console.log('Backend not available, trying mock storage for download');
        const mockFile = MockFileStorage.getFile(fileId);

        if (mockFile) {
          const content = mockFile.file_content || `Content of ${mockFile.original_filename}\n\nThis is stored in mock storage.`;

          return new NextResponse(content, {
            headers: {
              'Content-Type': 'text/plain',
              'Content-Disposition': `attachment; filename="${mockFile.original_filename}"`,
            },
          });
        }

        // File not found in mock storage either
        const mockContent = `File not found: ${fileId}\n\nThis file may have been uploaded before the mock storage system was implemented.`;

        return new NextResponse(mockContent, {
          status: 404,
          headers: {
            'Content-Type': 'text/plain',
            'Content-Disposition': `attachment; filename="file-not-found-${fileId}.txt"`,
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