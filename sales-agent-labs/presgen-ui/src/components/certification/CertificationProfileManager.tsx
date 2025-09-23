'use client';

import React, { useState } from 'react';
import { Settings, ArrowLeft } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { CertificationProfile } from '@/lib/certification-api';
import CertificationProfileList from './CertificationProfileList';
import CertificationProfileForm from './CertificationProfileForm';
import CertificationProfileStats from './CertificationProfileStats';

type ViewMode = 'list' | 'create' | 'edit' | 'stats';

interface ViewState {
  mode: ViewMode;
  profile?: CertificationProfile;
}

export default function CertificationProfileManager() {
  const [viewState, setViewState] = useState<ViewState>({ mode: 'list' });

  // Navigation handlers
  const handleCreateNew = () => {
    setViewState({ mode: 'create' });
  };

  const handleEditProfile = (profile: CertificationProfile) => {
    setViewState({ mode: 'edit', profile });
  };

  const handleViewStatistics = (profile: CertificationProfile) => {
    setViewState({ mode: 'stats', profile });
  };

  const handleSelectProfile = (profile: CertificationProfile) => {
    // This could trigger assessment creation or other actions
    console.log('Selected profile:', profile);
    // For now, show statistics
    handleViewStatistics(profile);
  };

  const handleBackToList = () => {
    setViewState({ mode: 'list' });
  };

  const handleSaveProfile = (profile: CertificationProfile) => {
    // Return to list after successful save
    setViewState({ mode: 'list' });
  };

  // Render current view
  const renderCurrentView = () => {
    switch (viewState.mode) {
      case 'create':
        return (
          <CertificationProfileForm
            mode="create"
            onSave={handleSaveProfile}
            onCancel={handleBackToList}
          />
        );

      case 'edit':
        return (
          <CertificationProfileForm
            profile={viewState.profile}
            mode="edit"
            onSave={handleSaveProfile}
            onCancel={handleBackToList}
          />
        );

      case 'stats':
        return (
          <CertificationProfileStats
            profile={viewState.profile!}
            onClose={handleBackToList}
          />
        );

      case 'list':
      default:
        return (
          <CertificationProfileList
            onCreateNew={handleCreateNew}
            onEditProfile={handleEditProfile}
            onViewStatistics={handleViewStatistics}
            onSelectProfile={handleSelectProfile}
          />
        );
    }
  };

  // Get page title
  const getPageTitle = () => {
    switch (viewState.mode) {
      case 'create':
        return 'Create Certification Profile';
      case 'edit':
        return `Edit ${viewState.profile?.name}`;
      case 'stats':
        return `Statistics - ${viewState.profile?.name}`;
      case 'list':
      default:
        return 'Certification Profiles';
    }
  };

  // Show back button for non-list views
  const showBackButton = viewState.mode !== 'list';

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* Navigation breadcrumb */}
        {showBackButton && (
          <div className="mb-6">
            <Button
              variant="ghost"
              onClick={handleBackToList}
              className="flex items-center gap-2"
            >
              <ArrowLeft className="h-4 w-4" />
              Back to Profiles
            </Button>
          </div>
        )}

        {/* Page header for list view */}
        {viewState.mode === 'list' && (
          <div className="mb-8">
            <div className="flex items-center gap-3 mb-2">
              <Settings className="h-8 w-8 text-blue-600" />
              <h1 className="text-3xl font-bold text-gray-900">Certification Management</h1>
            </div>
            <p className="text-gray-600">
              Configure and manage certification profiles for assessments and gap analysis
            </p>
          </div>
        )}

        {/* Current view */}
        <div className="bg-white rounded-lg shadow-sm border">
          <div className="p-6">
            {renderCurrentView()}
          </div>
        </div>
      </div>
    </div>
  );
}