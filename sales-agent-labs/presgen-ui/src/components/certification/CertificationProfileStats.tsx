'use client';

import React, { useState, useEffect } from 'react';
import { BarChart3, Users, FileText, TrendingUp, Calendar, Target, CheckCircle, AlertTriangle } from 'lucide-react';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Button } from '@/components/ui/button';
import { toast } from 'sonner';
import {
  CertificationAPI,
  CertificationProfile,
  Statistics,
  ValidationResult
} from '@/lib/certification-api';

interface CertificationProfileStatsProps {
  profile: CertificationProfile;
  onClose?: () => void;
}

interface StatCard {
  title: string;
  value: string | number;
  description: string;
  icon: React.ReactNode;
  variant?: 'default' | 'success' | 'warning' | 'error';
}

export default function CertificationProfileStats({
  profile,
  onClose
}: CertificationProfileStatsProps) {
  const [statistics, setStatistics] = useState<Statistics | null>(null);
  const [validation, setValidation] = useState<ValidationResult | null>(null);
  const [loading, setLoading] = useState(true);

  // Load statistics and validation
  const loadData = async () => {
    try {
      setLoading(true);
      const [statsData, validationData] = await Promise.all([
        CertificationAPI.getStatistics(profile.id),
        CertificationAPI.validate(profile.id)
      ]);
      setStatistics(statsData);
      setValidation(validationData);
    } catch (error) {
      console.error('Failed to load profile statistics:', error);
      toast.error('Failed to load profile statistics');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [profile.id]);

  // Format date for display
  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Get validation status color
  const getValidationColor = (isValid: boolean) => {
    return isValid ? 'text-green-600' : 'text-red-600';
  };

  // Generate stat cards
  const getStatCards = (): StatCard[] => {
    if (!statistics) return [];

    return [
      {
        title: 'Total Domains',
        value: statistics.exam_domains.total_domains,
        description: 'Configured assessment domains',
        icon: <Target className="h-5 w-5" />,
        variant: statistics.exam_domains.total_domains >= 3 ? 'success' : 'warning'
      },
      {
        title: 'Knowledge Base',
        value: statistics.knowledge_base.documents_count,
        description: 'Documents in knowledge base',
        icon: <FileText className="h-5 w-5" />,
        variant: statistics.knowledge_base.documents_count > 0 ? 'success' : 'warning'
      },
      {
        title: 'Total Assessments',
        value: statistics.assessments.total_assessments,
        description: 'Assessments completed',
        icon: <Users className="h-5 w-5" />,
        variant: 'default'
      },
      {
        title: 'Average Score',
        value: statistics.assessments.average_score > 0
          ? `${Math.round(statistics.assessments.average_score)}%`
          : 'N/A',
        description: 'Average assessment score',
        icon: <TrendingUp className="h-5 w-5" />,
        variant: statistics.assessments.average_score >= 70 ? 'success' : 'warning'
      },
      {
        title: 'Gap Analyses',
        value: statistics.gap_analysis.total_analyses,
        description: 'Completed gap analyses',
        icon: <BarChart3 className="h-5 w-5" />,
        variant: 'default'
      },
      {
        title: 'Created',
        value: formatDate(statistics.profile_info.created_at),
        description: 'Profile creation date',
        icon: <Calendar className="h-5 w-5" />,
        variant: 'default'
      }
    ];
  };

  if (loading) {
    return (
      <div className="space-y-6">
        <div className="flex justify-between items-center">
          <div>
            <h2 className="text-2xl font-bold">Profile Statistics</h2>
            <p className="text-gray-600">Loading statistics for {profile.name}...</p>
          </div>
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3, 4, 5, 6].map((i) => (
            <Card key={i} className="animate-pulse">
              <CardHeader className="pb-2">
                <div className="h-4 bg-gray-200 rounded w-1/2"></div>
              </CardHeader>
              <CardContent>
                <div className="h-8 bg-gray-200 rounded w-1/3 mb-2"></div>
                <div className="h-3 bg-gray-200 rounded w-2/3"></div>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>
    );
  }

  const statCards = getStatCards();

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold">Profile Statistics</h2>
          <p className="text-gray-600">
            Detailed analytics for {profile.name} v{profile.version}
          </p>
        </div>
        <Button variant="outline" onClick={onClose}>
          Close
        </Button>
      </div>

      {/* Validation Status */}
      {validation && (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              {validation.is_valid ? (
                <CheckCircle className="h-5 w-5 text-green-600" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-red-600" />
              )}
              Validation Status
            </CardTitle>
            <CardDescription>
              Profile validation completed at {formatDate(validation.validation_timestamp)}
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-2">
              <Badge
                variant={validation.is_valid ? 'default' : 'destructive'}
                className={validation.is_valid ? 'bg-green-100 text-green-800' : ''}
              >
                {validation.is_valid ? 'Valid' : 'Invalid'}
              </Badge>
            </div>

            {validation.errors.length > 0 && (
              <div>
                <h4 className="font-medium text-red-600 mb-2">Errors:</h4>
                <ul className="list-disc list-inside space-y-1 text-sm text-red-600">
                  {validation.errors.map((error, index) => (
                    <li key={index}>{error}</li>
                  ))}
                </ul>
              </div>
            )}

            {validation.warnings.length > 0 && (
              <div>
                <h4 className="font-medium text-yellow-600 mb-2">Warnings:</h4>
                <ul className="list-disc list-inside space-y-1 text-sm text-yellow-600">
                  {validation.warnings.map((warning, index) => (
                    <li key={index}>{warning}</li>
                  ))}
                </ul>
              </div>
            )}

            {validation.recommendations.length > 0 && (
              <div>
                <h4 className="font-medium text-blue-600 mb-2">Recommendations:</h4>
                <ul className="list-disc list-inside space-y-1 text-sm text-blue-600">
                  {validation.recommendations.map((rec, index) => (
                    <li key={index}>{rec}</li>
                  ))}
                </ul>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Statistics Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {statCards.map((stat, index) => (
          <Card key={index}>
            <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
              <CardTitle className="text-sm font-medium">{stat.title}</CardTitle>
              <div className={`
                ${stat.variant === 'success' ? 'text-green-600' : ''}
                ${stat.variant === 'warning' ? 'text-yellow-600' : ''}
                ${stat.variant === 'error' ? 'text-red-600' : ''}
                ${stat.variant === 'default' ? 'text-gray-600' : ''}
              `}>
                {stat.icon}
              </div>
            </CardHeader>
            <CardContent>
              <div className="text-2xl font-bold">{stat.value}</div>
              <p className="text-xs text-gray-600">{stat.description}</p>
            </CardContent>
          </Card>
        ))}
      </div>

      {/* Domain Breakdown */}
      {statistics && (
        <Card>
          <CardHeader>
            <CardTitle>Domain Breakdown</CardTitle>
            <CardDescription>
              Detailed information about each exam domain
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-4">
              {statistics.exam_domains.domain_breakdown.map((domain, index) => (
                <div key={index} className="border rounded-lg p-4">
                  <div className="flex justify-between items-center mb-2">
                    <h4 className="font-medium">{domain.domain}</h4>
                    <Badge variant="outline">{domain.weight}%</Badge>
                  </div>
                  <div className="grid grid-cols-2 gap-4 text-sm text-gray-600">
                    <div>
                      <span className="font-medium">Topics:</span> {domain.subdomains_count || 0}
                    </div>
                    <div>
                      <span className="font-medium">Skills:</span> {domain.skills_count || 0}
                    </div>
                  </div>
                  <Progress
                    value={domain.weight}
                    className="mt-2"
                    max={100}
                  />
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      )}

      {/* Knowledge Base Info */}
      {statistics && (
        <Card>
          <CardHeader>
            <CardTitle>Knowledge Base Information</CardTitle>
            <CardDescription>
              Current status of the knowledge base for this certification
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="space-y-2">
              <div className="flex justify-between">
                <span className="text-sm font-medium">Path:</span>
                <span className="text-sm text-gray-600">{statistics.knowledge_base.path}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm font-medium">Documents:</span>
                <span className="text-sm text-gray-600">{statistics.knowledge_base.documents_count}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-sm font-medium">Status:</span>
                <Badge
                  variant={statistics.knowledge_base.processing_status === 'ready' ? 'default' : 'secondary'}
                  className={statistics.knowledge_base.processing_status === 'ready' ? 'bg-green-100 text-green-800' : ''}
                >
                  {statistics.knowledge_base.processing_status}
                </Badge>
              </div>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  );
}