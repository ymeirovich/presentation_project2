import { NextRequest, NextResponse } from 'next/server';
import { MockFileStorage, generateMockFileId, determineResourceType, MockFileRecord } from '@/lib/mock-file-storage';

/**
 * File upload endpoint - with mock storage fallback for development
 */
export async function POST(request: NextRequest) {
  try {
    // Get the form data from the request
    const formData = await request.formData();
    const file = formData.get('file') as File;
    const certProfileId = formData.get('cert_profile_id') as string;
    const resourceType = formData.get('resource_type') as string;

    if (!file || !certProfileId) {
      return NextResponse.json(
        { error: 'Missing required fields: file and cert_profile_id' },
        { status: 400 }
      );
    }

    // Try to proxy to backend first
    const backendUrl = `${process.env.PRESGEN_ASSESS_URL || 'http://localhost:8081'}/api/v1/presgen-assess/files`;
    console.log(`Proxying file upload to: ${backendUrl}`);

    let backendResponse;
    try {
      backendResponse = await fetch(backendUrl, {
        method: 'POST',
        body: formData,
      });
    } catch (backendError) {
      console.log('Backend not available, using mock storage');
    }

    // If backend is available and successful, use its response
    if (backendResponse && backendResponse.ok) {
      const responseData = await backendResponse.json();
      console.log('File upload successful via backend:', responseData);
      return NextResponse.json(responseData);
    }

    // Backend not available or failed, use mock storage
    console.log('Using mock storage for file upload');

    // Read file content for mock storage
    const fileContent = await file.text();
    const fileId = generateMockFileId();

    // Create mock file record
    const mockFile = MockFileStorage.addFile({
      file_id: fileId,
      original_filename: file.name,
      resource_type: (resourceType as MockFileRecord['resource_type']) || determineResourceType(file.name),
      file_size: file.size,
      processing_status: 'completed', // Mock as completed immediately
      chunk_count: Math.floor(file.size / 1000) + 1, // Simulate chunking
      cert_profile_id: certProfileId,
      file_content: fileContent.substring(0, 1000), // Store first 1000 chars for download
    });

    // Return response in expected format
    const response = {
      file_id: mockFile.file_id,
      original_filename: mockFile.original_filename,
      processing_status: mockFile.processing_status,
      resource_type: mockFile.resource_type,
      file_size: mockFile.file_size,
      chunk_count: mockFile.chunk_count,
      upload_timestamp: mockFile.upload_timestamp,
      message: 'File uploaded successfully using mock storage'
    };

    console.log('Mock file upload successful:', response);
    return NextResponse.json(response);

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