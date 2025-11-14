/**
 * Mock file storage for testing
 * This is a placeholder for the test route
 */

export interface FileUploadResult {
  url: string;
  id: string;
  name?: string;
  size?: number;
}

export class MockFileStorage {
  private files: Map<string, FileUploadResult> = new Map();

  async upload(file: File): Promise<FileUploadResult> {
    const id = `mock-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`;
    const result: FileUploadResult = {
      url: `/mock/files/${id}`,
      id,
      name: file.name,
      size: file.size
    };
    this.files.set(id, result);
    return result;
  }

  async delete(id: string): Promise<boolean> {
    return this.files.delete(id);
  }

  async get(id: string): Promise<FileUploadResult | null> {
    return this.files.get(id) || null;
  }

  async list(): Promise<FileUploadResult[]> {
    return Array.from(this.files.values());
  }

  getStorageStats() {
    const totalFiles = this.files.size;
    const totalSize = Array.from(this.files.values()).reduce((sum, file) => sum + (file.size || 0), 0);
    return {
      totalFiles,
      totalSize,
      files: Array.from(this.files.values())
    };
  }
}

// Export singleton instance
export const mockFileStorage = new MockFileStorage();
