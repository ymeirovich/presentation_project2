import { NextRequest, NextResponse } from 'next/server';
import { mockFileStorage } from '@/lib/mock-file-storage';

/**
 * Test endpoint to check mock storage status
 */
export async function GET(request: NextRequest) {
  try {
    const stats = mockFileStorage.getStorageStats();

    return NextResponse.json({
      message: 'Mock storage test successful',
      storage_stats: stats,
      all_files: stats.files,
      timestamp: new Date().toISOString()
    });
  } catch (error) {
    return NextResponse.json({
      error: 'Mock storage test failed',
      detail: error instanceof Error ? error.message : 'Unknown error'
    }, { status: 500 });
  }
}