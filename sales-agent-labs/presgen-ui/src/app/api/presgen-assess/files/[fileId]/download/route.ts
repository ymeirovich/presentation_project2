import { NextRequest, NextResponse } from 'next/server';

/**
 * Download file - proxies to PresGen-Assess backend
 * Backend is the single source of truth
 */
export async function GET(
  request: NextRequest,
  context: { params: Promise<{ fileId: string }> }
) {
  try {
    const { fileId } = await context.params;

    // Proxy the download request to the PresGen-Assess backend
    const backendUrl = `${process.env.PRESGEN_ASSESS_URL || 'http://localhost:8000'}/api/v1/presgen-assess/files/${fileId}/download`;

    console.log(`Proxying GET file download request to: ${backendUrl}`);

    const response = await fetch(backendUrl, {
      method: 'GET',
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error(`❌ Backend download file failed (${response.status}):`, errorText);

      return NextResponse.json(
        {
          error: 'Failed to download file',
          detail: errorText,
          status: response.status
        },
        { status: response.status }
      );
    }

    // Stream the file back to the client
    const blob = await response.blob();
    console.log(`✅ File download successful: ${fileId}`);

    return new NextResponse(blob, {
      headers: {
        'Content-Type': response.headers.get('Content-Type') || 'application/octet-stream',
        'Content-Disposition': response.headers.get('Content-Disposition') || `attachment; filename="${fileId}"`,
      },
    });

  } catch (error) {
    console.error('❌ File download error:', error);

    return NextResponse.json(
      {
        error: 'File download failed',
        detail: error instanceof Error ? error.message : 'Unknown error'
      },
      { status: 500 }
    );
  }
}