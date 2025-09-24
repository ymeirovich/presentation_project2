/**
 * Mock file storage for development/testing
 * This provides in-memory storage of file metadata until backend implementation is ready
 */

export interface MockFileRecord {
  file_id: string;
  original_filename: string;
  resource_type: 'exam_guide' | 'transcript' | 'supplemental';
  file_size: number;
  processing_status: 'pending' | 'processing' | 'completed' | 'failed';
  chunk_count: number;
  upload_timestamp: string;
  cert_profile_id: string;
  error_message?: string;
  file_content?: string; // Store file content for downloads
}

// Persistent storage using file system
const STORAGE_FILE_PATH = '/tmp/presgen-mock-storage.json';

interface PersistedStorage {
  files: Record<string, MockFileRecord>;
  profileIndex: Record<string, string[]>;
}

// Load storage from file
function loadStorage(): PersistedStorage {
  try {
    const fs = require('fs');
    if (fs.existsSync(STORAGE_FILE_PATH)) {
      const data = fs.readFileSync(STORAGE_FILE_PATH, 'utf8');
      return JSON.parse(data);
    }
  } catch (error) {
    console.warn('Failed to load mock storage from file:', error);
  }
  return { files: {}, profileIndex: {} };
}

// Save storage to file
function saveStorage(): void {
  try {
    const fs = require('fs');
    const storage: PersistedStorage = {
      files: Object.fromEntries(mockFileStorage),
      profileIndex: Object.fromEntries(
        Array.from(profileFilesIndex.entries()).map(([profileId, fileIds]) => [
          profileId,
          Array.from(fileIds)
        ])
      )
    };
    fs.writeFileSync(STORAGE_FILE_PATH, JSON.stringify(storage, null, 2));
  } catch (error) {
    console.warn('Failed to save mock storage to file:', error);
  }
}

// Initialize from persistent storage
const persistedData = loadStorage();
const mockFileStorage = new Map<string, MockFileRecord>(Object.entries(persistedData.files));
const profileFilesIndex = new Map<string, Set<string>>(
  Object.entries(persistedData.profileIndex).map(([profileId, fileIds]) => [
    profileId,
    new Set(fileIds)
  ])
);

export class MockFileStorage {

  static addFile(fileData: Omit<MockFileRecord, 'upload_timestamp'>): MockFileRecord {
    const file: MockFileRecord = {
      ...fileData,
      upload_timestamp: new Date().toISOString(),
    };

    mockFileStorage.set(file.file_id, file);

    // Add to profile index
    if (!profileFilesIndex.has(file.cert_profile_id)) {
      profileFilesIndex.set(file.cert_profile_id, new Set());
    }
    profileFilesIndex.get(file.cert_profile_id)!.add(file.file_id);

    console.log(`📁 Mock storage: Added file ${file.file_id} for profile ${file.cert_profile_id}`);
    console.log(`📊 Total files in storage: ${mockFileStorage.size}`);

    // Persist to file
    saveStorage();

    return file;
  }

  static getFile(fileId: string): MockFileRecord | undefined {
    return mockFileStorage.get(fileId);
  }

  static getFilesForProfile(profileId: string): MockFileRecord[] {
    const fileIds = profileFilesIndex.get(profileId);
    if (!fileIds) {
      return [];
    }

    const files: MockFileRecord[] = [];
    fileIds.forEach(fileId => {
      const file = mockFileStorage.get(fileId);
      if (file) {
        files.push(file);
      }
    });

    // Sort by upload timestamp (newest first)
    return files.sort((a, b) => new Date(b.upload_timestamp).getTime() - new Date(a.upload_timestamp).getTime());
  }

  static updateFileStatus(fileId: string, status: MockFileRecord['processing_status'], errorMessage?: string): MockFileRecord | undefined {
    const file = mockFileStorage.get(fileId);
    if (file) {
      file.processing_status = status;
      if (errorMessage) {
        file.error_message = errorMessage;
      }
      mockFileStorage.set(fileId, file);
      console.log(`📝 Mock storage: Updated file ${fileId} status to ${status}`);

      // Persist changes
      saveStorage();
    }
    return file;
  }

  static deleteFile(fileId: string): boolean {
    const file = mockFileStorage.get(fileId);
    if (!file) {
      return false;
    }

    // Remove from profile index
    const profileFiles = profileFilesIndex.get(file.cert_profile_id);
    if (profileFiles) {
      profileFiles.delete(fileId);
      if (profileFiles.size === 0) {
        profileFilesIndex.delete(file.cert_profile_id);
      }
    }

    // Remove from main storage
    mockFileStorage.delete(fileId);
    console.log(`🗑️ Mock storage: Deleted file ${fileId}`);

    // Persist changes
    saveStorage();

    return true;
  }

  static getAllFiles(): MockFileRecord[] {
    return Array.from(mockFileStorage.values());
  }

  static getStorageStats(): { totalFiles: number, profileCount: number } {
    return {
      totalFiles: mockFileStorage.size,
      profileCount: profileFilesIndex.size
    };
  }

  static clearAll(): void {
    mockFileStorage.clear();
    profileFilesIndex.clear();
    console.log('🧹 Mock storage: Cleared all files');
  }
}

// Helper function to generate realistic file IDs
export function generateMockFileId(): string {
  return `file_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

// Helper function to determine resource type from filename
export function determineResourceType(filename: string): MockFileRecord['resource_type'] {
  const name = filename.toLowerCase();

  if (name.includes('exam') || name.includes('guide') || name.includes('study') || name.includes('prep')) {
    return 'exam_guide';
  }

  if (name.includes('transcript') || name.includes('course') || name.includes('lecture') || name.includes('video')) {
    return 'transcript';
  }

  return 'supplemental';
}