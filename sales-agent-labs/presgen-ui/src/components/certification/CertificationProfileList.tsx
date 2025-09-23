'use client';

import React, { useState, useEffect } from 'react';
import { Search, Plus, MoreHorizontal, Copy, BarChart3, CheckCircle, AlertCircle, Trash2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { toast } from 'sonner';
import { CertificationAPI, CertificationProfile, formatExamDomains } from '@/lib/certification-api';

interface CertificationProfileListProps {
  onSelectProfile?: (profile: CertificationProfile) => void;
  onCreateNew?: () => void;
  onEditProfile?: (profile: CertificationProfile) => void;
  onViewStatistics?: (profile: CertificationProfile) => void;
}

export default function CertificationProfileList({
  onSelectProfile,
  onCreateNew,
  onEditProfile,
  onViewStatistics
}: CertificationProfileListProps) {
  const [profiles, setProfiles] = useState<CertificationProfile[]>([]);
  const [filteredProfiles, setFilteredProfiles] = useState<CertificationProfile[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [loading, setLoading] = useState(true);
  const [deleteDialog, setDeleteDialog] = useState<{ open: boolean; profile?: CertificationProfile }>({
    open: false
  });

  // Load certification profiles
  const loadProfiles = async () => {
    try {
      setLoading(true);
      const data = await CertificationAPI.list();
      setProfiles(data);
      setFilteredProfiles(data);
    } catch (error) {
      console.error('Failed to load certification profiles:', error);
      toast.error('Failed to load certification profiles');
    } finally {
      setLoading(false);
    }
  };

  // Filter profiles based on search query
  useEffect(() => {
    if (!searchQuery.trim()) {
      setFilteredProfiles(profiles);
    } else {
      const filtered = profiles.filter(profile =>
        profile.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
        profile.version.toLowerCase().includes(searchQuery.toLowerCase()) ||
        profile.exam_domains.some(domain =>
          domain.name.toLowerCase().includes(searchQuery.toLowerCase())
        )
      );
      setFilteredProfiles(filtered);
    }
  }, [searchQuery, profiles]);

  useEffect(() => {
    loadProfiles();
  }, []);

  // Handle duplicate profile
  const handleDuplicate = async (profile: CertificationProfile) => {
    try {
      const newName = `${profile.name} (Copy)`;
      const newVersion = `${profile.version}-copy`;

      await CertificationAPI.duplicate(profile.id, newName, newVersion);
      toast.success('Profile duplicated successfully');
      loadProfiles(); // Reload the list
    } catch (error) {
      console.error('Failed to duplicate profile:', error);
      toast.error('Failed to duplicate profile');
    }
  };

  // Handle delete profile
  const handleDelete = async (profile: CertificationProfile) => {
    try {
      await CertificationAPI.delete(profile.id);
      toast.success('Profile deleted successfully');
      setDeleteDialog({ open: false });
      loadProfiles(); // Reload the list
    } catch (error) {
      console.error('Failed to delete profile:', error);
      toast.error('Failed to delete profile');
    }
  };

  // Handle validate profile
  const handleValidate = async (profile: CertificationProfile) => {
    try {
      const validation = await CertificationAPI.validate(profile.id);

      if (validation.is_valid) {
        toast.success('Profile validation passed ✅');
      } else {
        const errorMessage = validation.errors.length > 0
          ? `Validation failed: ${validation.errors[0]}`
          : 'Profile validation failed';
        toast.error(errorMessage);
      }
    } catch (error) {
      console.error('Failed to validate profile:', error);
      toast.error('Failed to validate profile');
    }
  };

  // Format creation date
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  // Get status badge based on profile completeness
  const getStatusBadge = (profile: CertificationProfile) => {
    const hasTemplate = profile.assessment_template && Object.keys(profile.assessment_template).length > 0;
    const hasSubdomains = profile.exam_domains.some(domain => domain.subdomains.length > 0);

    if (hasTemplate && hasSubdomains) {
      return <Badge variant="default" className="bg-green-100 text-green-800">Complete</Badge>;
    } else if (profile.exam_domains.length > 0) {
      return <Badge variant="secondary">Basic</Badge>;
    } else {
      return <Badge variant="destructive">Incomplete</Badge>;
    }
  };

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="flex justify-between items-center">
          <h2 className="text-2xl font-bold">Certification Profiles</h2>
          <Button disabled>
            <Plus className="h-4 w-4 mr-2" />
            Create Profile
          </Button>
        </div>

        <div className="grid gap-4">
          {[1, 2, 3].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader>
                <div className="h-4 bg-gray-200 rounded w-1/3"></div>
                <div className="h-3 bg-gray-200 rounded w-1/2"></div>
              </CardHeader>
              <CardContent>
                <div className="h-3 bg-gray-200 rounded w-full"></div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold">Certification Profiles</h2>
          <p className="text-gray-600">Manage certification profiles and assessment configurations</p>
        </div>
        <Button onClick={onCreateNew}>
          <Plus className="h-4 w-4 mr-2" />
          Create Profile
        </Button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
        <Input
          placeholder="Search profiles by name, version, or domain..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Profile List */}
      {filteredProfiles.length === 0 ? (
        <Card>
          <CardContent className="py-12 text-center">
            <div className="text-gray-500">
              {searchQuery ? 'No profiles match your search.' : 'No certification profiles found.'}
            </div>
            {!searchQuery && (
              <Button className="mt-4" onClick={onCreateNew}>
                <Plus className="h-4 w-4 mr-2" />
                Create Your First Profile
              </Button>
            )}
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4">
          {filteredProfiles.map((profile) => (
            <Card key={profile.id} className="hover:shadow-md transition-shadow">
              <CardHeader className="pb-3">
                <div className="flex justify-between items-start">
                  <div>
                    <CardTitle className="text-lg">{profile.name}</CardTitle>
                    <CardDescription>
                      Version {profile.version} • Created {formatDate(profile.created_at)}
                    </CardDescription>
                  </div>
                  <div className="flex items-center gap-2">
                    {getStatusBadge(profile)}
                    <DropdownMenu>
                      <DropdownMenuTrigger asChild>
                        <Button variant="ghost" size="sm">
                          <MoreHorizontal className="h-4 w-4" />
                        </Button>
                      </DropdownMenuTrigger>
                      <DropdownMenuContent align="end">
                        <DropdownMenuItem onClick={() => onSelectProfile?.(profile)}>
                          Select Profile
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => onEditProfile?.(profile)}>
                          Edit Profile
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleDuplicate(profile)}>
                          <Copy className="h-4 w-4 mr-2" />
                          Duplicate
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => onViewStatistics?.(profile)}>
                          <BarChart3 className="h-4 w-4 mr-2" />
                          View Statistics
                        </DropdownMenuItem>
                        <DropdownMenuItem onClick={() => handleValidate(profile)}>
                          <CheckCircle className="h-4 w-4 mr-2" />
                          Validate
                        </DropdownMenuItem>
                        <DropdownMenuSeparator />
                        <DropdownMenuItem
                          onClick={() => setDeleteDialog({ open: true, profile })}
                          className="text-red-600 focus:text-red-600"
                        >
                          <Trash2 className="h-4 w-4 mr-2" />
                          Delete
                        </DropdownMenuItem>
                      </DropdownMenuContent>
                    </DropdownMenu>
                  </div>
                </div>
              </CardHeader>
              <CardContent>
                <div className="space-y-2">
                  <div>
                    <span className="text-sm font-medium text-gray-600">Exam Domains ({profile.exam_domains.length}):</span>
                    <p className="text-sm text-gray-800">
                      {formatExamDomains(profile.exam_domains)}
                    </p>
                  </div>
                  <div className="flex items-center gap-4 text-xs text-gray-500">
                    <span>Knowledge Base: {profile.knowledge_base_path}</span>
                    <span>•</span>
                    <span>Updated {formatDate(profile.updated_at)}</span>
                  </div>
                </div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Delete Confirmation Dialog */}
      <Dialog open={deleteDialog.open} onOpenChange={(open) => setDeleteDialog({ open })}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Delete Certification Profile</DialogTitle>
            <DialogDescription>
              Are you sure you want to delete "{deleteDialog.profile?.name}"? This action cannot be undone
              and will remove all associated assessments and data.
            </DialogDescription>
          </DialogHeader>
          <DialogFooter>
            <Button variant="outline" onClick={() => setDeleteDialog({ open: false })}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={() => deleteDialog.profile && handleDelete(deleteDialog.profile)}
            >
              Delete
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </div>
  );
}