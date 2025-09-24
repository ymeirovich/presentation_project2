import { NextRequest, NextResponse } from 'next/server';
import { MockFileStorage } from '@/lib/mock-file-storage';

/**
 * Get files for a specific certification profile - with mock storage fallback
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

    // Try backend first
    const backendUrl = `${process.env.PRESGEN_ASSESS_URL || 'http://localhost:8081'}/api/v1/presgen-assess/files/profile/${profileId}`;
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
      console.log('Files retrieved successfully from backend:', responseData);
      return NextResponse.json(responseData);
    }

    // Backend not available or failed, use mock storage
    console.log('Using mock storage for file retrieval');
    const mockFiles = MockFileStorage.getFilesForProfile(profileId);
    const storageStats = MockFileStorage.getStorageStats();

    console.log(`📁 Mock storage: Found ${mockFiles.length} files for profile ${profileId}`);
    console.log(`📊 Storage stats:`, storageStats);

    // Transform mock files to expected API format
    const apiFiles = mockFiles.map(file => ({
      file_id: file.file_id,
      original_filename: file.original_filename,
      resource_type: file.resource_type,
      file_size: file.file_size,
      processing_status: file.processing_status,
      chunk_count: file.chunk_count,
      upload_timestamp: file.upload_timestamp,
      error_message: file.error_message
    }));

    const response = {
      files: apiFiles,
      total: apiFiles.length,
      profileId: profileId,
      message: mockFiles.length > 0 ? 'Files retrieved from mock storage' : 'No files uploaded yet'
    };

    return NextResponse.json(response);

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