"use client";

import React, { useState, useRef, useCallback } from 'react';
import { Upload, X, FileText, AlertCircle, CheckCircle, Clock } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent } from '@/components/ui/card';
import { cn } from '@/lib/utils';

export interface FileUploadStatus {
  file_id: string;
  filename: string;
  size: number;
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'failed';
  progress: number;
  error?: string;
  resource_type: 'exam_guide' | 'transcript' | 'supplemental';
}

interface FileUploadZoneProps {
  onFilesUploaded: (files: FileUploadStatus[]) => void;
  acceptedTypes?: string[];
  maxFileSize?: number; // in bytes
  maxFiles?: number;
  certProfileId: string;
  disabled?: boolean;
  className?: string;
}

const RESOURCE_TYPE_LABELS = {
  exam_guide: 'Exam Guide',
  transcript: 'Transcript',
  supplemental: 'Supplemental'
};

const RESOURCE_TYPE_COLORS = {
  exam_guide: 'bg-blue-100 text-blue-800',
  transcript: 'bg-green-100 text-green-800',
  supplemental: 'bg-purple-100 text-purple-800'
};

export default function FileUploadZone({
  onFilesUploaded,
  acceptedTypes = ['.pdf', '.docx', '.txt', '.md'],
  maxFileSize = 50 * 1024 * 1024, // 50MB
  maxFiles = 10,
  certProfileId,
  disabled = false,
  className
}: FileUploadZoneProps) {
  const [uploadedFiles, setUploadedFiles] = useState<FileUploadStatus[]>([]);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const validateFile = (file: File): string | null => {
    // Check file type
    const fileExtension = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!acceptedTypes.includes(fileExtension)) {
      return `File type ${fileExtension} not supported. Accepted types: ${acceptedTypes.join(', ')}`;
    }

    // Check file size
    if (file.size > maxFileSize) {
      return `File size (${formatFileSize(file.size)}) exceeds maximum allowed size (${formatFileSize(maxFileSize)})`;
    }

    return null;
  };

  const determineResourceType = (filename: string): 'exam_guide' | 'transcript' | 'supplemental' => {
    const lower = filename.toLowerCase();

    if (lower.includes('guide') || lower.includes('exam') || lower.includes('study')) {
      return 'exam_guide';
    }

    if (lower.includes('transcript') || lower.includes('video') || lower.includes('course')) {
      return 'transcript';
    }

    return 'supplemental';
  };

  const uploadFile = async (file: File): Promise<FileUploadStatus> => {
    const fileId = `upload_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
    const resourceType = determineResourceType(file.name);

    const fileStatus: FileUploadStatus = {
      file_id: fileId,
      filename: file.name,
      size: file.size,
      status: 'uploading',
      progress: 0,
      resource_type: resourceType
    };

    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('cert_profile_id', certProfileId);
      formData.append('resource_type', resourceType);
      formData.append('process_immediately', 'true');

      // Simulate upload progress (in real implementation, use XMLHttpRequest for progress)
      const progressInterval = setInterval(() => {
        setUploadedFiles(prev =>
          prev.map(f =>
            f.file_id === fileId
              ? { ...f, progress: Math.min(f.progress + Math.random() * 20, 90) }
              : f
          )
        );
      }, 200);

      const response = await fetch('/api/presgen-assess/files/upload', {
        method: 'POST',
        body: formData
      });

      clearInterval(progressInterval);

      if (!response.ok) {
        const errorData = await response.json();
        throw new Error(errorData.detail || errorData.error || 'Upload failed');
      }

      const result = await response.json();

      // Update with successful upload
      const updatedStatus: FileUploadStatus = {
        ...fileStatus,
        file_id: result.file_id,
        status: result.processing_status === 'processing' ? 'processing' : 'completed',
        progress: 100
      };

      // If processing, poll for status updates
      if (result.processing_status === 'processing') {
        pollFileStatus(result.file_id, updatedStatus);
      }

      return updatedStatus;

    } catch (error) {
      return {
        ...fileStatus,
        status: 'failed',
        progress: 0,
        error: error instanceof Error ? error.message : 'Upload failed'
      };
    }
  };

  const pollFileStatus = async (fileId: string, initialStatus: FileUploadStatus) => {
    const pollInterval = setInterval(async () => {
      try {
        const response = await fetch(`/api/presgen-assess/files/${fileId}/status`);
        if (response.ok) {
          const statusData = await response.json();

          setUploadedFiles(prev =>
            prev.map(f =>
              f.file_id === fileId
                ? {
                    ...f,
                    status: statusData.status === 'completed' ? 'completed' :
                           statusData.status === 'failed' ? 'failed' : 'processing',
                    error: statusData.error_message
                  }
                : f
            )
          );

          if (statusData.status === 'completed' || statusData.status === 'failed') {
            clearInterval(pollInterval);
          }
        }
      } catch (error) {
        console.error('Failed to poll file status:', error);
        clearInterval(pollInterval);
      }
    }, 2000);

    // Clear polling after 5 minutes
    setTimeout(() => clearInterval(pollInterval), 5 * 60 * 1000);
  };

  const handleFileSelection = useCallback(async (files: FileList) => {
    if (disabled || uploadedFiles.length + files.length > maxFiles) {
      return;
    }

    setIsUploading(true);

    const validFiles: File[] = [];
    const errors: string[] = [];

    // Validate all files first
    Array.from(files).forEach(file => {
      const error = validateFile(file);
      if (error) {
        errors.push(`${file.name}: ${error}`);
      } else {
        validFiles.push(file);
      }
    });

    if (errors.length > 0) {
      // Show validation errors
      console.error('File validation errors:', errors);
      setIsUploading(false);
      return;
    }

    // Create initial file statuses
    const initialStatuses: FileUploadStatus[] = validFiles.map(file => ({
      file_id: `pending_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
      filename: file.name,
      size: file.size,
      status: 'pending' as const,
      progress: 0,
      resource_type: determineResourceType(file.name)
    }));

    setUploadedFiles(prev => [...prev, ...initialStatuses]);

    // Upload files
    const uploadPromises = validFiles.map(async (file, index) => {
      const result = await uploadFile(file);

      setUploadedFiles(prev =>
        prev.map(f =>
          f.file_id === initialStatuses[index].file_id ? result : f
        )
      );

      return result;
    });

    try {
      const results = await Promise.all(uploadPromises);
      onFilesUploaded(results);
    } finally {
      setIsUploading(false);
    }
  }, [certProfileId, disabled, maxFiles, uploadedFiles.length, onFilesUploaded]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    if (!disabled) {
      setIsDragOver(true);
    }
  }, [disabled]);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
  }, []);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);

    if (!disabled && e.dataTransfer.files) {
      handleFileSelection(e.dataTransfer.files);
    }
  }, [disabled, handleFileSelection]);

  const handleFileInputChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      handleFileSelection(e.target.files);
    }
  }, [handleFileSelection]);

  const removeFile = (fileId: string) => {
    setUploadedFiles(prev => prev.filter(f => f.file_id !== fileId));
  };

  const getStatusIcon = (status: FileUploadStatus['status']) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-red-600" />;
      case 'processing':
      case 'uploading':
        return <Clock className="w-4 h-4 text-blue-600 animate-spin" />;
      default:
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  return (
    <div className={cn("space-y-4", className)}>
      {/* Upload Zone */}
      <Card
        className={cn(
          "relative border-2 border-dashed transition-colors",
          isDragOver && !disabled ? "border-blue-400 bg-blue-50" : "border-gray-300",
          disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer hover:border-gray-400"
        )}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !disabled && fileInputRef.current?.click()}
      >
        <CardContent className="flex flex-col items-center justify-center p-8 text-center">
          <Upload className={cn(
            "w-12 h-12 mb-4",
            isDragOver && !disabled ? "text-blue-500" : "text-gray-400"
          )} />

          <h3 className="text-lg font-semibold mb-2">
            {isDragOver ? "Drop files here" : "Upload Certification Resources"}
          </h3>

          <p className="text-sm text-gray-600 mb-4">
            Drag and drop files or click to browse
          </p>

          <p className="text-xs text-gray-500 mb-4">
            Supported formats: {acceptedTypes.join(', ')} • Max size: {formatFileSize(maxFileSize)} • Max files: {maxFiles}
          </p>

          <Button
            type="button"
            variant="outline"
            disabled={disabled || isUploading}
            onClick={(e) => {
              e.stopPropagation();
              fileInputRef.current?.click();
            }}
          >
            {isUploading ? 'Uploading...' : 'Choose Files'}
          </Button>
        </CardContent>
      </Card>

      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept={acceptedTypes.join(',')}
        onChange={handleFileInputChange}
        className="hidden"
        disabled={disabled}
      />

      {/* Uploaded Files List */}
      {uploadedFiles.length > 0 && (
        <div className="space-y-3">
          <h4 className="font-medium text-sm text-gray-700">Uploaded Files ({uploadedFiles.length})</h4>

          {uploadedFiles.map((file) => (
            <Card key={file.file_id} className="p-4">
              <div className="flex items-start justify-between">
                <div className="flex items-start space-x-3 flex-1">
                  <FileText className="w-5 h-5 text-gray-400 mt-0.5" />

                  <div className="flex-1 min-w-0">
                    <div className="flex items-center space-x-2 mb-1">
                      <p className="text-sm font-medium text-gray-900 truncate">
                        {file.filename}
                      </p>
                      <Badge className={cn("text-xs", RESOURCE_TYPE_COLORS[file.resource_type])}>
                        {RESOURCE_TYPE_LABELS[file.resource_type]}
                      </Badge>
                    </div>

                    <p className="text-xs text-gray-500 mb-2">
                      {formatFileSize(file.size)}
                    </p>

                    {(file.status === 'uploading' || file.status === 'processing') && (
                      <Progress value={file.progress} className="h-1 mb-2" />
                    )}

                    {file.error && (
                      <p className="text-xs text-red-600 mb-2">{file.error}</p>
                    )}
                  </div>

                  <div className="flex items-center space-x-2">
                    {getStatusIcon(file.status)}

                    <Button
                      type="button"
                      variant="ghost"
                      size="sm"
                      onClick={() => removeFile(file.file_id)}
                      className="p-1 h-auto text-gray-400 hover:text-gray-600"
                    >
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}