'use client';

import React, { useState, useEffect } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Plus, Trash2, AlertCircle, CheckCircle, Save, X } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { toast } from 'sonner';
import {
  CertificationAPI,
  CertificationProfile,
  CertificationProfileCreate,
  CertificationProfileCreateSchema,
  createDefaultExamDomain,
  validateDomainWeights,
  calculateCompletionPercentage
} from '@/lib/certification-api';

interface CertificationProfileFormProps {
  profile?: CertificationProfile;
  onSave?: (profile: CertificationProfile) => void;
  onCancel?: () => void;
  mode?: 'create' | 'edit';
}

export default function CertificationProfileForm({
  profile,
  onSave,
  onCancel,
  mode = 'create'
}: CertificationProfileFormProps) {
  const [saving, setSaving] = useState(false);
  const [completionPercentage, setCompletionPercentage] = useState(0);

  const defaultValues = profile ? {
    name: profile.name,
    version: profile.version,
    provider: profile.provider || '',
    description: profile.description || '',
    exam_code: profile.exam_code || '',
    passing_score: profile.passing_score || undefined,
    exam_duration_minutes: profile.exam_duration_minutes || undefined,
    question_count: profile.question_count || undefined,
    exam_domains: profile.exam_domains.map(domain => ({
      ...domain,
      topics: domain.topics || []
    })),
    prerequisites: profile.prerequisites || [],
    recommended_experience: profile.recommended_experience || '',
    is_active: profile.is_active !== undefined ? profile.is_active : true
  } : {
    name: '',
    version: '1.0',
    provider: '',
    description: '',
    exam_code: '',
    passing_score: undefined,
    exam_duration_minutes: undefined,
    question_count: undefined,
    exam_domains: [createDefaultExamDomain()],
    prerequisites: [],
    recommended_experience: '',
    is_active: true
  };

  const {
    register,
    control,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isValid }
  } = useForm<CertificationProfileCreate>({
    resolver: zodResolver(CertificationProfileCreateSchema),
    defaultValues,
    mode: 'onChange'
  });

  // Early return if form is not initialized properly
  if (!register || !control) {
    return (
      <div className="space-y-6">
        <div className="flex justify-center items-center py-8">
          <div className="text-gray-500">Loading form...</div>
        </div>
      </div>
    );
  }

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'exam_domains'
  });

  // Ensure fields is properly initialized
  if (!fields) {
    return (
      <div className="space-y-6">
        <div className="flex justify-center items-center py-8">
          <div className="text-gray-500">Loading field array...</div>
        </div>
      </div>
    );
  }

  const watchedFields = watch();

  // Update completion percentage when form changes
  useEffect(() => {
    const percentage = calculateCompletionPercentage(watchedFields);
    setCompletionPercentage(percentage);
  }, [watchedFields]);

  // Handle form submission
  const onSubmit = async (data: CertificationProfileCreate) => {
    try {
      setSaving(true);

      // Ensure all domains have topics array properly set
      const processedData = {
        ...data,
        exam_domains: data.exam_domains.map(domain => ({
          ...domain,
          topics: domain.topics || []
        }))
      };

      console.log('Submitting certification profile data:', JSON.stringify(processedData, null, 2));

      // Manual Zod validation
      try {
        const validatedData = CertificationProfileCreateSchema.parse(processedData);
        data = validatedData;
      } catch (zodError: any) {
        console.error('Zod validation error:', zodError);
        toast.error(zodError.errors?.[0]?.message || 'Validation failed');
        return;
      }

      // Validate domain weights
      const validation = validateDomainWeights(data.exam_domains);
      if (!validation.isValid) {
        toast.error(validation.error);
        return;
      }

      let savedProfile: CertificationProfile;

      if (mode === 'edit' && profile) {
        savedProfile = await CertificationAPI.update(profile.id, data);
        toast.success('Profile updated successfully');
      } else {
        savedProfile = await CertificationAPI.create(data);
        toast.success('Profile created successfully');
      }

      onSave?.(savedProfile);
    } catch (error) {
      console.error('Failed to save profile:', error);

      // Extract meaningful error message
      let errorMessage = `Failed to ${mode === 'edit' ? 'update' : 'create'} profile`;
      if (error instanceof Error) {
        errorMessage = error.message;
      }

      console.error('Error details:', errorMessage);
      toast.error(errorMessage);
    } finally {
      setSaving(false);
    }
  };

  // Add new exam domain
  const addExamDomain = () => {
    append(createDefaultExamDomain());
  };

  // Remove exam domain
  const removeExamDomain = (index: number) => {
    if (fields.length > 1) {
      remove(index);
    } else {
      toast.error('At least one exam domain is required');
    }
  };

  // Auto-balance domain weights
  const autoBalanceWeights = () => {
    const domainCount = fields.length;
    const equalWeight = Math.floor(100 / domainCount);
    const remainder = 100 % domainCount;

    fields.forEach((_, index) => {
      const weight = index < remainder ? equalWeight + 1 : equalWeight;
      setValue(`exam_domains.${index}.weight_percentage`, weight);
    });

    toast.success('Domain weights auto-balanced');
  };

  // Get current total weight
  const getCurrentTotalWeight = () => {
    return watchedFields.exam_domains?.reduce(
      (sum, domain) => sum + (domain.weight_percentage || 0),
      0
    ) || 0;
  };

  const totalWeight = getCurrentTotalWeight();
  const isWeightValid = totalWeight === 100;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex justify-between items-center">
        <div>
          <h2 className="text-2xl font-bold">
            {mode === 'edit' ? 'Edit' : 'Create'} Certification Profile
          </h2>
          <p className="text-gray-600">
            Configure assessment domains and knowledge requirements
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Badge variant={completionPercentage === 100 ? 'default' : 'secondary'}>
            {completionPercentage}% Complete
          </Badge>
          <Progress value={completionPercentage} className="w-20" />
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        {/* Basic Information */}
        <Card>
          <CardHeader>
            <CardTitle>Certification Information</CardTitle>
            <CardDescription>
              Define the certification details and exam parameters
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="name">Certification Name *</Label>
                <Input
                  id="name"
                  {...register('name')}
                  placeholder="e.g., AWS Solutions Architect"
                  className={errors.name ? 'border-red-500' : ''}
                />
                {errors.name && (
                  <p className="text-sm text-red-500 mt-1">{errors.name.message}</p>
                )}
              </div>
              <div>
                <Label htmlFor="version">Version *</Label>
                <Input
                  id="version"
                  {...register('version')}
                  placeholder="e.g., 2023"
                  className={errors.version ? 'border-red-500' : ''}
                />
                {errors.version && (
                  <p className="text-sm text-red-500 mt-1">{errors.version.message}</p>
                )}
              </div>
            </div>
            <div>
              <Label htmlFor="provider">Provider *</Label>
              <Input
                id="provider"
                {...register('provider')}
                placeholder="e.g., AWS, Microsoft, Google"
                className={errors.provider ? 'border-red-500' : ''}
              />
              {errors.provider && (
                <p className="text-sm text-red-500 mt-1">{errors.provider.message}</p>
              )}
            </div>
            <div>
              <Label htmlFor="description">Description</Label>
              <Textarea
                id="description"
                {...register('description')}
                placeholder="Describe the certification and its objectives"
                rows={3}
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="exam_code">Exam Code</Label>
                <Input
                  id="exam_code"
                  {...register('exam_code')}
                  placeholder="e.g., SAA-C03"
                />
              </div>
              <div>
                <Label htmlFor="passing_score">Passing Score (%)</Label>
                <Input
                  id="passing_score"
                  type="number"
                  min="0"
                  max="100"
                  {...register('passing_score', { valueAsNumber: true })}
                  placeholder="e.g., 72"
                  className={errors.passing_score ? 'border-red-500' : ''}
                />
                {errors.passing_score && (
                  <p className="text-sm text-red-500 mt-1">{errors.passing_score.message}</p>
                )}
              </div>
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div>
                <Label htmlFor="exam_duration_minutes">Exam Duration (minutes)</Label>
                <Input
                  id="exam_duration_minutes"
                  type="number"
                  min="1"
                  {...register('exam_duration_minutes', { valueAsNumber: true })}
                  placeholder="e.g., 130"
                />
              </div>
              <div>
                <Label htmlFor="question_count">Question Count</Label>
                <Input
                  id="question_count"
                  type="number"
                  min="1"
                  {...register('question_count', { valueAsNumber: true })}
                  placeholder="e.g., 65"
                />
              </div>
            </div>
          </CardContent>
        </Card>

        {/* Exam Domains */}
        <Card>
          <CardHeader>
            <div className="flex justify-between items-center">
              <div>
                <CardTitle>Exam Domains</CardTitle>
                <CardDescription>
                  Define assessment domains and their weights (must total 100%)
                </CardDescription>
              </div>
              <div className="flex items-center gap-2">
                <Badge
                  variant={isWeightValid ? 'default' : 'destructive'}
                  className="flex items-center gap-1"
                >
                  {isWeightValid ? (
                    <CheckCircle className="h-3 w-3" />
                  ) : (
                    <AlertCircle className="h-3 w-3" />
                  )}
                  {totalWeight}%
                </Badge>
                <Button
                  type="button"
                  variant="outline"
                  size="sm"
                  onClick={autoBalanceWeights}
                >
                  Auto-Balance
                </Button>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {fields.map((field, index) => (
              <div key={field.id} className="border rounded-lg p-4 space-y-3">
                <div className="flex justify-between items-center">
                  <h4 className="font-medium">Domain {index + 1}</h4>
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    onClick={() => removeExamDomain(index)}
                    disabled={fields.length === 1}
                  >
                    <Trash2 className="h-4 w-4" />
                  </Button>
                </div>

                <div className="grid grid-cols-3 gap-3">
                  <div className="col-span-2">
                    <Label htmlFor={`domain-name-${index}`}>Domain Name *</Label>
                    <Input
                      id={`domain-name-${index}`}
                      {...register(`exam_domains.${index}.name`)}
                      placeholder="e.g., Design Resilient Architectures"
                      className={errors.exam_domains?.[index]?.name ? 'border-red-500' : ''}
                    />
                    {errors.exam_domains?.[index]?.name && (
                      <p className="text-sm text-red-500 mt-1">
                        {errors.exam_domains[index]?.name?.message}
                      </p>
                    )}
                  </div>
                  <div>
                    <Label htmlFor={`domain-weight-${index}`}>Weight % *</Label>
                    <Input
                      id={`domain-weight-${index}`}
                      type="number"
                      min="0"
                      max="100"
                      {...register(`exam_domains.${index}.weight_percentage`, {
                        valueAsNumber: true
                      })}
                      placeholder="25"
                      className={errors.exam_domains?.[index]?.weight_percentage ? 'border-red-500' : ''}
                    />
                    {errors.exam_domains?.[index]?.weight_percentage && (
                      <p className="text-sm text-red-500 mt-1">
                        {errors.exam_domains[index]?.weight_percentage?.message}
                      </p>
                    )}
                  </div>
                </div>

                <div>
                  <Label htmlFor={`domain-topics-${index}`}>Topics (comma-separated)</Label>
                  <Input
                    id={`domain-topics-${index}`}
                    {...register(`exam_domains.${index}.topics_input`)}
                    placeholder="e.g., Scalability, Fault Tolerance, Disaster Recovery"
                    onChange={(e) => {
                      const topics = e.target.value.split(',').map(s => s.trim()).filter(Boolean);
                      setValue(`exam_domains.${index}.topics`, topics);
                    }}
                    defaultValue={field.topics?.join(', ') || ''}
                  />
                </div>
              </div>
            ))}

            <Button
              type="button"
              variant="outline"
              onClick={addExamDomain}
              className="w-full"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Exam Domain
            </Button>

            {errors.exam_domains && (
              <div className="flex items-center gap-2 text-red-600 text-sm">
                <AlertCircle className="h-4 w-4" />
                <span>Please ensure all domain weights sum to 100%</span>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Assessment Template */}
        <Card>
          <CardHeader>
            <CardTitle>Assessment Template (Optional)</CardTitle>
            <CardDescription>
              Custom assessment configuration in JSON format
            </CardDescription>
          </CardHeader>
          <CardContent>
            <Textarea
              {...register('assessment_template', {
                setValueAs: (value) => {
                  if (!value || value.trim() === '') return undefined;
                  try {
                    return JSON.parse(value);
                  } catch {
                    return value; // Let validation handle the error
                  }
                }
              })}
              placeholder='{"question_count": 65, "time_limit_minutes": 130, "difficulty_distribution": {"easy": 0.2, "medium": 0.6, "hard": 0.2}}'
              rows={4}
              className="font-mono text-sm"
            />
            <p className="text-xs text-gray-500 mt-1">
              Leave empty to use default assessment settings
            </p>
          </CardContent>
        </Card>

        {/* Actions */}
        <div className="flex justify-end gap-3">
          <Button type="button" variant="outline" onClick={onCancel}>
            <X className="h-4 w-4 mr-2" />
            Cancel
          </Button>
          <Button
            type="submit"
            disabled={saving || !isValid || !isWeightValid}
          >
            {saving ? (
              <>
                <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
                Saving...
              </>
            ) : (
              <>
                <Save className="h-4 w-4 mr-2" />
                {mode === 'edit' ? 'Update' : 'Create'} Profile
              </>
            )}
          </Button>
        </div>
      </form>
    </div>
  );
}