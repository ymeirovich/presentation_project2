import { NextRequest, NextResponse } from 'next/server';
import { MockFileStorage } from '@/lib/mock-file-storage';

/**
 * Test endpoint to check mock storage status
 */
export async function GET(request: NextRequest) {
  try {
    const stats = MockFileStorage.getStorageStats();
    const allFiles = MockFileStorage.getAllFiles();

    return NextResponse.json({
      message: 'Mock storage test successful',
      storage_stats: stats,
      all_files: allFiles.map(file => ({
        file_id: file.file_id,
        original_filename: file.original_filename,
        cert_profile_id: file.cert_profile_id,
        processing_status: file.processing_status,
        upload_timestamp: file.upload_timestamp
      })),
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    return NextResponse.json({
      error: 'Mock storage test failed',
      detail: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}