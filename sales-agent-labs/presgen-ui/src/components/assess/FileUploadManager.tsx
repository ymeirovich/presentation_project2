'use client';

import React, { useState, useEffect } from 'react';
import { Upload, Database, FileText, Settings, ChevronRight, AlertCircle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select';
import { toast } from 'sonner';

// Import ChromaDB file upload components
import FileUploadZone, { FileUploadStatus } from '@/components/file-upload/FileUploadZone';
import ResourceManager from '@/components/file-upload/ResourceManager';
import PromptEditor from '@/components/file-upload/PromptEditor';

// Import certification API
import { CertificationAPI, CertificationProfile } from '@/lib/certification-api';

interface FileUploadManagerProps {
  className?: string;
}

export default function FileUploadManager({ className }: FileUploadManagerProps) {
  const [certificationProfiles, setCertificationProfiles] = useState<CertificationProfile[]>([]);
  const [selectedProfileId, setSelectedProfileId] = useState<string>('');
  const [profilesLoading, setProfilesLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('upload');
  const [uploadStatuses, setUploadStatuses] = useState<FileUploadStatus[]>([]);

  // Load certification profiles
  useEffect(() => {
    const loadProfiles = async () => {
      try {
        setProfilesLoading(true);
        const profiles = await CertificationAPI.getAll();
        setCertificationProfiles(profiles);

        // Auto-select first profile if available
        if (profiles.length > 0 && !selectedProfileId) {
          setSelectedProfileId(profiles[0].id);
        }
      } catch (error) {
        console.error('Error loading certification profiles:', error);
        toast.error('Failed to load certification profiles');
      } finally {
        setProfilesLoading(false);
      }
    };

    loadProfiles();
  }, [selectedProfileId]);

  const selectedProfile = certificationProfiles.find(p => p.id === selectedProfileId);

  const handleFileUploadComplete = (status: FileUploadStatus) => {
    setUploadStatuses(prev => [...prev.filter(s => s.file_id !== status.file_id), status]);

    if (status.status === 'completed') {
      toast.success(`File ${status.filename} uploaded and processed successfully`);
      // Switch to resources tab to show the new file
      setActiveTab('resources');
    } else if (status.status === 'failed') {
      toast.error(`Failed to process ${status.filename}: ${status.error}`);
    }
  };

  const handleResourceDeleted = (fileId: string) => {
    setUploadStatuses(prev => prev.filter(s => s.file_id !== fileId));
    toast.success('Resource deleted successfully');
  };

  const handleResourcesChanged = () => {
    // Refresh resources view
    console.log('Resources changed, refreshing...');
  };

  const handlePromptsChange = (prompts: any) => {
    console.log('Prompts updated:', prompts);
    // This could update the certification profile with new prompts
  };

  if (profilesLoading) {
    return (
      <Card className={className}>
        <CardContent className="flex items-center justify-center p-8">
          <div className="flex items-center space-x-2">
            <Database className="w-5 h-5 animate-pulse" />
            <span>Loading certification profiles...</span>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (certificationProfiles.length === 0) {
    return (
      <Card className={className}>
        <CardContent className="flex flex-col items-center justify-center p-8 text-center">
          <AlertCircle className="w-8 h-8 text-amber-500 mb-3" />
          <h3 className="font-semibold mb-2">No Certification Profiles Found</h3>
          <p className="text-sm text-muted-foreground mb-4">
            Create a certification profile first to upload knowledge base materials.
          </p>
          <Button
            variant="outline"
            onClick={() => window.location.href = '#certifications'}
            className="flex items-center space-x-2"
          >
            <Database className="w-4 h-4" />
            <span>Manage Certification Profiles</span>
            <ChevronRight className="w-4 h-4" />
          </Button>
        </CardContent>
      </Card>
    );
  }

  return (
    <Card className={className}>
      <CardHeader>
        <div className="flex items-start justify-between">
          <div>
            <CardTitle className="flex items-center space-x-2">
              <Upload className="w-5 h-5" />
              <span>Knowledge Base Upload</span>
            </CardTitle>
            <CardDescription>
              Upload exam guides, transcripts, and supplemental materials to enhance assessment generation
            </CardDescription>
          </div>
          <Badge variant="secondary">ChromaDB RAG</Badge>
        </div>

        {/* Profile Selection */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Certification Profile</label>
          <Select value={selectedProfileId} onValueChange={setSelectedProfileId}>
            <SelectTrigger>
              <SelectValue placeholder="Select a certification profile" />
            </SelectTrigger>
            <SelectContent>
              {certificationProfiles.map(profile => (
                <SelectItem key={profile.id} value={profile.id}>
                  {profile.name} • {profile.version}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {selectedProfile && (
            <div className="flex flex-wrap gap-1 mt-2">
              {selectedProfile.exam_domains.map(domain => (
                <Badge key={domain.name} variant="outline" className="text-xs">
                  {domain.name} ({domain.weight_percentage}%)
                </Badge>
              ))}
            </div>
          )}
        </div>
      </CardHeader>

      <CardContent>
        {!selectedProfileId ? (
          <div className="text-center py-8 text-muted-foreground">
            <Database className="w-8 h-8 mx-auto mb-2 opacity-50" />
            <p>Select a certification profile to start uploading files</p>
          </div>
        ) : (
          <Tabs value={activeTab} onValueChange={setActiveTab}>
            <TabsList className="grid w-full grid-cols-3">
              <TabsTrigger value="upload" className="flex items-center space-x-2">
                <Upload className="w-4 h-4" />
                <span>Upload Files</span>
              </TabsTrigger>
              <TabsTrigger value="resources" className="flex items-center space-x-2">
                <FileText className="w-4 h-4" />
                <span>Manage Resources</span>
              </TabsTrigger>
              <TabsTrigger value="prompts" className="flex items-center space-x-2">
                <Settings className="w-4 h-4" />
                <span>Custom Prompts</span>
              </TabsTrigger>
            </TabsList>

            <TabsContent value="upload" className="mt-6">
              <FileUploadZone
                certProfileId={selectedProfileId}
                onUploadComplete={handleFileUploadComplete}
                maxFiles={10}
                className="min-h-[300px]"
              />

              {uploadStatuses.length > 0 && (
                <div className="mt-6">
                  <h4 className="text-sm font-medium mb-3">Recent Uploads</h4>
                  <div className="space-y-2">
                    {uploadStatuses.slice(-3).map(status => (
                      <div key={status.file_id} className="flex items-center justify-between text-xs p-2 bg-muted rounded">
                        <span>{status.filename}</span>
                        <Badge variant={
                          status.status === 'completed' ? 'default' :
                          status.status === 'failed' ? 'destructive' :
                          'secondary'
                        }>
                          {status.status}
                        </Badge>
                      </div>
                    ))}
                  </div>
                </div>
              )}
            </TabsContent>

            <TabsContent value="resources" className="mt-6">
              <ResourceManager
                certProfileId={selectedProfileId}
                onResourceDeleted={handleResourceDeleted}
                onResourcesChanged={handleResourcesChanged}
              />
            </TabsContent>

            <TabsContent value="prompts" className="mt-6">
              <PromptEditor
                initialPrompts={{}}
                onPromptsChange={handlePromptsChange}
                certificationContext={selectedProfile ? {
                  name: selectedProfile.name,
                  domains: selectedProfile.exam_domains.map(d => d.name),
                  industryContext: selectedProfile.description || 'Professional certification'
                } : undefined}
              />
            </TabsContent>
          </Tabs>
        )}
      </CardContent>
    </Card>
  );
}