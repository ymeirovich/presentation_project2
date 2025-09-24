"use client";

import React, { useState, useEffect } from 'react';
import {
  FileText,
  Download,
  Trash2,
  RefreshCw,
  AlertCircle,
  CheckCircle,
  Clock,
  Eye,
  Filter
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { Input } from '@/components/ui/input';
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
  AlertDialogTrigger,
} from '@/components/ui/alert-dialog';
import { cn } from '@/lib/utils';

export interface FileResource {
  file_id: string;
  original_filename: string;
  resource_type: 'exam_guide' | 'transcript' | 'supplemental';
  file_size: number;
  processing_status: 'pending' | 'processing' | 'completed' | 'failed';
  chunk_count: number;
  upload_timestamp: string;
  error_message?: string;
}

interface ResourceManagerProps {
  certProfileId: string;
  onResourceDeleted: (fileId: string) => void;
  onResourcesChanged: () => void;
  className?: string;
}

const RESOURCE_TYPE_LABELS = {
  exam_guide: 'Exam Guide',
  transcript: 'Transcript',
  supplemental: 'Supplemental'
};

const RESOURCE_TYPE_COLORS = {
  exam_guide: 'bg-blue-100 text-blue-800 border-blue-200',
  transcript: 'bg-green-100 text-green-800 border-green-200',
  supplemental: 'bg-purple-100 text-purple-800 border-purple-200'
};

const STATUS_COLORS = {
  completed: 'text-green-600',
  processing: 'text-blue-600',
  pending: 'text-yellow-600',
  failed: 'text-red-600'
};

export default function ResourceManager({
  certProfileId,
  onResourceDeleted,
  onResourcesChanged,
  className
}: ResourceManagerProps) {
  const [resources, setResources] = useState<FileResource[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filterType, setFilterType] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [searchTerm, setSearchTerm] = useState('');
  const [refreshing, setRefreshing] = useState(false);

  const formatFileSize = (bytes: number): string => {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const formatDate = (timestamp: string): string => {
    try {
      return new Date(timestamp).toLocaleString();
    } catch {
      return timestamp;
    }
  };

  const loadResources = async () => {
    try {
      setError(null);
      const response = await fetch(`/api/presgen-assess/files/profile/${certProfileId}`);

      if (!response.ok) {
        throw new Error(`Failed to load resources: ${response.status}`);
      }

      const data = await response.json();
      setResources(data.files || []);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load resources');
      console.error('Error loading resources:', err);
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadResources();
    onResourcesChanged();
  };

  const handleDelete = async (fileId: string, filename: string) => {
    try {
      const response = await fetch(`/api/presgen-assess/files/${fileId}`, {
        method: 'DELETE'
      });

      if (!response.ok) {
        throw new Error('Failed to delete file');
      }

      setResources(prev => prev.filter(r => r.file_id !== fileId));
      onResourceDeleted(fileId);
      onResourcesChanged();

    } catch (err) {
      console.error('Error deleting resource:', err);
      setError(err instanceof Error ? err.message : 'Failed to delete resource');
    }
  };

  const handleDownload = async (fileId: string, filename: string) => {
    try {
      const response = await fetch(`/api/presgen-assess/files/${fileId}/download`);

      if (!response.ok) {
        throw new Error('Failed to download file');
      }

      // Create download link
      const blob = await response.blob();
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);

    } catch (err) {
      console.error('Error downloading resource:', err);
      setError(err instanceof Error ? err.message : 'Failed to download resource');
    }
  };

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-600" />;
      case 'failed':
        return <AlertCircle className="w-4 h-4 text-red-600" />;
      case 'processing':
        return <Clock className="w-4 h-4 text-blue-600 animate-spin" />;
      case 'pending':
        return <Clock className="w-4 h-4 text-yellow-600" />;
      default:
        return <Clock className="w-4 h-4 text-gray-400" />;
    }
  };

  // Filter resources based on search and filters
  const filteredResources = resources.filter(resource => {
    const matchesSearch = resource.original_filename.toLowerCase().includes(searchTerm.toLowerCase());
    const matchesType = filterType === 'all' || resource.resource_type === filterType;
    const matchesStatus = filterStatus === 'all' || resource.processing_status === filterStatus;

    return matchesSearch && matchesType && matchesStatus;
  });

  const resourceCounts = {
    total: resources.length,
    exam_guide: resources.filter(r => r.resource_type === 'exam_guide').length,
    transcript: resources.filter(r => r.resource_type === 'transcript').length,
    supplemental: resources.filter(r => r.resource_type === 'supplemental').length,
    completed: resources.filter(r => r.processing_status === 'completed').length,
    processing: resources.filter(r => r.processing_status === 'processing').length,
    failed: resources.filter(r => r.processing_status === 'failed').length
  };

  useEffect(() => {
    if (certProfileId) {
      loadResources();
    }
  }, [certProfileId]);

  if (loading) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center p-8">
          <RefreshCw className="w-6 h-6 animate-spin mr-2" />
          <span>Loading resources...</span>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-center justify-between">
          <div>
            <CardTitle className="flex items-center space-x-2">
              <FileText className="w-5 h-5" />
              <span>Resource Manager</span>
              <Badge variant="outline">{resourceCounts.total} files</Badge>
            </CardTitle>
          </div>

          <Button
            variant="outline"
            size="sm"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            <RefreshCw className={cn("w-4 h-4", refreshing && "animate-spin")} />
            {refreshing ? 'Refreshing...' : 'Refresh'}
          </Button>
        </div>

        {/* Quick Stats */}
        <div className="flex flex-wrap gap-2 mt-4">
          <Badge variant="outline" className="text-blue-700 border-blue-200">
            Exam Guides: {resourceCounts.exam_guide}
          </Badge>
          <Badge variant="outline" className="text-green-700 border-green-200">
            Transcripts: {resourceCounts.transcript}
          </Badge>
          <Badge variant="outline" className="text-purple-700 border-purple-200">
            Supplemental: {resourceCounts.supplemental}
          </Badge>
          <Badge variant="outline" className="text-green-700 border-green-200">
            Processed: {resourceCounts.completed}
          </Badge>
          {resourceCounts.processing > 0 && (
            <Badge variant="outline" className="text-blue-700 border-blue-200">
              Processing: {resourceCounts.processing}
            </Badge>
          )}
          {resourceCounts.failed > 0 && (
            <Badge variant="outline" className="text-red-700 border-red-200">
              Failed: {resourceCounts.failed}
            </Badge>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-4">
        {/* Filters */}
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1">
            <Input
              placeholder="Search files..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              className="w-full"
            />
          </div>

          <Select value={filterType} onValueChange={setFilterType}>
            <SelectTrigger className="w-full sm:w-40">
              <SelectValue placeholder="Filter by type" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Types</SelectItem>
              <SelectItem value="exam_guide">Exam Guides</SelectItem>
              <SelectItem value="transcript">Transcripts</SelectItem>
              <SelectItem value="supplemental">Supplemental</SelectItem>
            </SelectContent>
          </Select>

          <Select value={filterStatus} onValueChange={setFilterStatus}>
            <SelectTrigger className="w-full sm:w-40">
              <SelectValue placeholder="Filter by status" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All Statuses</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="processing">Processing</SelectItem>
              <SelectItem value="pending">Pending</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
            </SelectContent>
          </Select>
        </div>

        {error && (
          <div className="flex items-center space-x-2 p-3 bg-red-50 border border-red-200 rounded-md">
            <AlertCircle className="w-4 h-4 text-red-600" />
            <span className="text-sm text-red-700">{error}</span>
          </div>
        )}

        {/* Resources List */}
        <div className="space-y-3">
          {filteredResources.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              {searchTerm || filterType !== 'all' || filterStatus !== 'all'
                ? 'No resources match your filters'
                : 'No resources uploaded yet'
              }
            </div>
          ) : (
            filteredResources.map((resource) => (
              <Card key={resource.file_id} className="border-l-4 border-l-gray-200">
                <CardContent className="p-4">
                  <div className="flex items-start justify-between">
                    <div className="flex items-start space-x-3 flex-1">
                      <FileText className="w-5 h-5 text-gray-400 mt-0.5" />

                      <div className="flex-1 min-w-0">
                        <div className="flex items-center space-x-2 mb-1">
                          <h4 className="font-medium text-gray-900 truncate">
                            {resource.original_filename}
                          </h4>
                          <Badge
                            variant="outline"
                            className={cn("text-xs", RESOURCE_TYPE_COLORS[resource.resource_type])}
                          >
                            {RESOURCE_TYPE_LABELS[resource.resource_type]}
                          </Badge>
                        </div>

                        <div className="flex items-center space-x-4 text-xs text-gray-500 mb-2">
                          <span>{formatFileSize(resource.file_size)}</span>
                          <span>{formatDate(resource.upload_timestamp)}</span>
                          {resource.chunk_count > 0 && (
                            <span>{resource.chunk_count} chunks</span>
                          )}
                        </div>

                        <div className="flex items-center space-x-2">
                          {getStatusIcon(resource.processing_status)}
                          <span className={cn(
                            "text-xs font-medium capitalize",
                            STATUS_COLORS[resource.processing_status as keyof typeof STATUS_COLORS]
                          )}>
                            {resource.processing_status}
                          </span>
                        </div>

                        {resource.error_message && (
                          <p className="text-xs text-red-600 mt-2">
                            {resource.error_message}
                          </p>
                        )}
                      </div>

                      <div className="flex items-center space-x-1">
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={() => handleDownload(resource.file_id, resource.original_filename)}
                          title="Download file"
                          className="p-2"
                        >
                          <Download className="w-4 h-4" />
                        </Button>

                        <AlertDialog>
                          <AlertDialogTrigger asChild>
                            <Button
                              variant="ghost"
                              size="sm"
                              title="Delete file"
                              className="p-2 text-red-600 hover:text-red-700 hover:bg-red-50"
                            >
                              <Trash2 className="w-4 h-4" />
                            </Button>
                          </AlertDialogTrigger>
                          <AlertDialogContent>
                            <AlertDialogHeader>
                              <AlertDialogTitle>Delete Resource</AlertDialogTitle>
                              <AlertDialogDescription>
                                Are you sure you want to delete "{resource.original_filename}"?
                                This will permanently remove the file and all its processed chunks from the knowledge base.
                                This action cannot be undone.
                              </AlertDialogDescription>
                            </AlertDialogHeader>
                            <AlertDialogFooter>
                              <AlertDialogCancel>Cancel</AlertDialogCancel>
                              <AlertDialogAction
                                onClick={() => handleDelete(resource.file_id, resource.original_filename)}
                                className="bg-red-600 hover:bg-red-700"
                              >
                                Delete
                              </AlertDialogAction>
                            </AlertDialogFooter>
                          </AlertDialogContent>
                        </AlertDialog>
                      </div>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
}