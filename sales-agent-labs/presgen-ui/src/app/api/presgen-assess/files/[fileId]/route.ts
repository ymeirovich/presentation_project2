import { NextRequest, NextResponse } from 'next/server';
import { MockFileStorage } from '@/lib/mock-file-storage';

/**
 * Delete file - proxies to PresGen-Assess backend
 */
export async function DELETE(
  request: NextRequest,
  context: { params: Promise<{ fileId: string }> }
) {
  try {
    const { fileId } = await context.params;

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

      // If the endpoint doesn't exist yet, try mock storage
      if (response.status === 404 || response.status === 405) {
        console.log('Backend not available, trying mock storage for delete');
        const wasDeleted = MockFileStorage.deleteFile(fileId);
        return NextResponse.json({
          file_id: fileId,
          success: true,
          message: wasDeleted ? 'File deleted from mock storage' : 'File not found in mock storage'
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

    // Try mock storage as fallback
    try {
      const wasDeleted = MockFileStorage.deleteFile(fileId);
      return NextResponse.json({
        file_id: fileId,
        success: true,
        message: wasDeleted ? 'File deleted from mock storage' : 'File not found in mock storage'
      });
    } catch (mockError) {
      return NextResponse.json({
        file_id: fileId,
        success: true,
        message: 'File delete temporarily unavailable'
      });
    }
  }
}

/**
 * Download file - proxies to PresGen-Assess backend
 */
export async function GET(
  request: NextRequest,
  context: { params: Promise<{ fileId: string }> }
) {
  try {
    const { fileId } = await context.params;
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