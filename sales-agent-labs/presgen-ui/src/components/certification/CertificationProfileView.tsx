'use client';

import React from 'react';
import { CertificationProfile, formatExamDomains } from '@/lib/certification-api';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { X } from 'lucide-react';

interface CertificationProfileViewProps {
  profile: CertificationProfile;
  onClose: () => void;
}

export default function CertificationProfileView({ profile, onClose }: CertificationProfileViewProps) {
  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>{profile.name}</CardTitle>
            <CardDescription>Version {profile.version}</CardDescription>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </CardHeader>
        <CardContent className="space-y-6">
          <div className="space-y-2">
            <h3 className="font-semibold">Description</h3>
            <p className="text-sm text-gray-600">{profile.description || 'N/A'}</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div>
              <h4 className="font-semibold">Exam Code</h4>
              <p className="text-sm">{profile.exam_code || 'N/A'}</p>
            </div>
            <div>
              <h4 className="font-semibold">Passing Score</h4>
              <p className="text-sm">{profile.passing_score ? `${profile.passing_score}%` : 'N/A'}</p>
            </div>
            <div>
              <h4 className="font-semibold">Duration</h4>
              <p className="text-sm">{profile.exam_duration_minutes ? `${profile.exam_duration_minutes} minutes` : 'N/A'}</p>
            </div>
          </div>

          <div>
            <h4 className="font-semibold">Exam Domains</h4>
            <p className="text-sm">{formatExamDomains(profile.exam_domains)}</p>
          </div>

          <div>
            <h4 className="font-semibold">Custom Prompts</h4>
            <div className="space-y-2 mt-2">
              <div>
                <h5 className="text-sm font-medium">Assessment Prompt</h5>
                <p className="text-xs p-2 bg-gray-50 rounded">{profile.assessment_prompt || 'Not set'}</p>
              </div>
              <div>
                <h5 className="text-sm font-medium">Presentation Prompt</h5>
                <p className="text-xs p-2 bg-gray-50 rounded">{profile.presentation_prompt || 'Not set'}</p>
              </div>
              <div>
                <h5 className="text-sm font-medium">Gap Analysis Prompt</h5>
                <p className="text-xs p-2 bg-gray-50 rounded">{profile.gap_analysis_prompt || 'Not set'}</p>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
