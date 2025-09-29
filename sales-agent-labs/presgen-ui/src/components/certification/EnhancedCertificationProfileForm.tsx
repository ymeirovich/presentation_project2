'use client';

import React, { useState, useEffect, useCallback, useMemo } from 'react';
import { useForm, useFieldArray } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  Plus,
  Trash2,
  AlertCircle,
  CheckCircle,
  Save,
  X,
  Upload,
  Database,
  Wand2,
  FileText,
  Settings
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Switch } from '@/components/ui/switch';
import { toast } from 'sonner';
import { z } from 'zod';

// Import ChromaDB components
import FileUploadZone, { FileUploadStatus } from '@/components/file-upload/FileUploadZone';
import ResourceManager from '@/components/file-upload/ResourceManager';

// Import separated prompt components
import CertificationPromptEditor from '@/components/prompts/CertificationPromptEditor';
import KnowledgeBasePromptEditor from '@/components/prompts/KnowledgeBasePromptEditor';

// Import existing API and schemas
import {
  CertificationAPI,
  CertificationProfile,
  CertificationProfileCreate,
  CertificationProfileCreateSchema,
  createDefaultExamDomain,
  validateDomainWeights,
  calculateCompletionPercentage
} from '@/lib/certification-api';

interface EnhancedCertificationProfileFormProps {
  profile?: CertificationProfile;
  onSave?: (profile: CertificationProfile) => void;
  onCancel?: () => void;
  mode?: 'create' | 'edit';
}

interface FormData extends Omit<CertificationProfileCreate, 'exam_domains'> {
  // ChromaDB integration fields
  bundle_version?: string;
  assessment_prompt?: string;
  presentation_prompt?: string;
  gap_analysis_prompt?: string;
  resource_binding_enabled?: boolean;
  // Override exam_domains to allow string topics in form
  exam_domains: Array<{
    name: string;
    weight_percentage: number;
    topics: string | string[]; // Allow both string and string array
  }>;
}

export default function EnhancedCertificationProfileForm({
  profile,
  onSave,
  onCancel,
  mode = 'create'
}: EnhancedCertificationProfileFormProps) {
  console.log('EnhancedCertificationProfileForm profile:', profile);
  const [saving, setSaving] = useState(false);
  const [completionPercentage, setCompletionPercentage] = useState(0);
  const [activeTab, setActiveTab] = useState('basic');
  const [uploadedFiles, setUploadedFiles] = useState<FileUploadStatus[]>([]);
  const [collectionCreated, setCollectionCreated] = useState(false);
  const [resourceCount, setResourceCount] = useState(0);
  const [knowledgeBasePrompts, setKnowledgeBasePrompts] = useState<{
    document_ingestion_prompt?: string;
    context_retrieval_prompt?: string;
    semantic_search_prompt?: string;
    content_classification_prompt?: string;
  }>({});
  const [kbPromptsLoading, setKbPromptsLoading] = useState(false);

  // Load knowledge base prompts
  const loadKnowledgeBasePrompts = async (collectionName: string) => {
    if (!collectionName) return;

    console.log('🗂️ PROMPT_DEBUG: Loading knowledge base prompts for collection:', collectionName);
    setKbPromptsLoading(true);

    try {
      const response = await fetch(`/api/presgen-assess/knowledge-prompts/${collectionName}`);
      if (response.ok) {
        const kbPrompts = await response.json();
        console.log('🗂️ PROMPT_DEBUG: Loaded knowledge base prompts:', kbPrompts);
        setKnowledgeBasePrompts(kbPrompts);
      } else if (response.status === 404) {
        console.log('🗂️ PROMPT_DEBUG: No knowledge base prompts found for collection:', collectionName);
        setKnowledgeBasePrompts({});
      } else {
        console.error('🗂️ PROMPT_DEBUG: Failed to load knowledge base prompts:', response.status);
      }
    } catch (error) {
      console.error('🗂️ PROMPT_DEBUG: Error loading knowledge base prompts:', error);
    } finally {
      setKbPromptsLoading(false);
    }
  };

  // Save knowledge base prompts
  const saveKnowledgeBasePrompts = async (collectionName: string, prompts: any) => {
    if (!collectionName) return;

    console.log('🗂️ PROMPT_DEBUG: Saving knowledge base prompts for collection:', collectionName, prompts);

    try {
      // First try to update existing prompts
      let response = await fetch(`/api/presgen-assess/knowledge-prompts/${collectionName}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(prompts)
      });

      // If not found, create new prompts
      if (response.status === 404) {
        response = await fetch('/api/presgen-assess/knowledge-prompts/', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            collection_name: collectionName,
            certification_name: watch('name'),
            version: 'v1.0',
            is_active: true,
            ...prompts
          })
        });
      }

      if (response.ok) {
        const savedPrompts = await response.json();
        console.log('🗂️ PROMPT_DEBUG: Saved knowledge base prompts:', savedPrompts);
        setKnowledgeBasePrompts(savedPrompts);
        toast.success('Knowledge base prompts saved successfully');
      } else {
        console.error('🗂️ PROMPT_DEBUG: Failed to save knowledge base prompts:', response.status);
        toast.error('Failed to save knowledge base prompts');
      }
    } catch (error) {
      console.error('🗂️ PROMPT_DEBUG: Error saving knowledge base prompts:', error);
      toast.error('Error saving knowledge base prompts');
    }
  };

  // Enhanced default values with ChromaDB fields
  const defaultValues: FormData = profile ? {
    name: profile.name || 'Existing Certification Profile',
    version: profile.version || '1.0',
    provider: profile.provider || 'Enter Provider',
    description: profile.description || '',
    exam_code: profile.exam_code || '',
    passing_score: profile.passing_score || undefined,
    exam_duration_minutes: profile.exam_duration_minutes || undefined,
    question_count: profile.question_count || undefined,
    exam_domains: profile.exam_domains?.length > 0 ? profile.exam_domains.map(domain => ({
      ...domain,
      name: domain.name || 'Domain',
      weight_percentage: domain.weight_percentage || 1,
      topics: Array.isArray(domain.topics) ? domain.topics.join(', ') : (domain.topics || '')
    })) : [{
      name: 'Domain 1',
      weight_percentage: 100,
      topics: ''
    }],
    prerequisites: profile.prerequisites || [],
    recommended_experience: profile.recommended_experience || '',
    is_active: profile.is_active !== undefined ? profile.is_active : true,
    // ChromaDB fields
    bundle_version: profile.bundle_version || 'v1.0',
    assessment_prompt: profile.assessment_prompt || '',
    presentation_prompt: profile.presentation_prompt || '',
    gap_analysis_prompt: profile.gap_analysis_prompt || '',
    resource_binding_enabled: profile.resource_binding_enabled !== undefined ? profile.resource_binding_enabled : true
  } : {
    name: 'New Certification Profile',
    version: '1.0',
    provider: 'Enter Provider',
    description: '',
    exam_code: '',
    passing_score: undefined,
    exam_duration_minutes: undefined,
    question_count: undefined,
    exam_domains: [{
      name: 'Domain 1',
      weight_percentage: 100,
      topics: ''
    }],
    prerequisites: [],
    recommended_experience: '',
    is_active: true,
    // ChromaDB defaults
    bundle_version: 'v1.0',
    assessment_prompt: '',
    presentation_prompt: '',
    gap_analysis_prompt: '',
    resource_binding_enabled: true
  };

  // Create form-specific schema that accepts string topics
  const FormExamDomainSchema = z.object({
    name: z.string().min(1),
    weight_percentage: z.number().int().min(1).max(100),
    topics: z.string().or(z.array(z.string())).default('') // Allow string or array
  });

  const extendedSchema = CertificationProfileCreateSchema.omit({ exam_domains: true }).extend({
    // ChromaDB fields
    bundle_version: z.string().optional(),
    assessment_prompt: z.string().optional(),
    presentation_prompt: z.string().optional(),
    gap_analysis_prompt: z.string().optional(),
    resource_binding_enabled: z.boolean().optional(),
    // Form-specific exam domains with string topics
    exam_domains: z.array(FormExamDomainSchema).refine(
      (domains) => {
        const totalWeight = domains.reduce((sum, domain) => sum + domain.weight_percentage, 0);
        return totalWeight === 100;
      },
      { message: "Domain weights must sum to 100%" }
    )
  });

  const {
    register,
    control,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isValid }
  } = useForm<FormData>({
    resolver: zodResolver(extendedSchema),
    defaultValues,
    mode: 'onChange'
  });

  const { fields, append, remove } = useFieldArray({
    control,
    name: 'exam_domains'
  });

  const watchedFields = watch();

  // Debug form state
  useEffect(() => {
    console.log('=== Form Validation Debug ===');
    console.log('isValid:', isValid);
    console.log('errors:', errors);
    console.log('Current form values:', watchedFields);

    // Check domain weights specifically
    if (watchedFields.exam_domains?.length > 0) {
      const totalWeight = watchedFields.exam_domains.reduce((sum, domain) => sum + (domain.weight_percentage || 0), 0);
      console.log('Domain weights sum to:', totalWeight, '(should be 100)');

      watchedFields.exam_domains.forEach((domain, index) => {
        console.log(`Domain ${index + 1}:`, {
          name: domain.name || '(empty)',
          weight: domain.weight_percentage || 0
        });
      });
    }

    console.log('=== End Debug ===');
  }, [isValid, errors]);

  // Load knowledge base prompts when profile is available
  useEffect(() => {
    if (profile && profile.name && profile.version) {
      const collectionName = `${profile.name.toLowerCase().replace(/ /g, '_')}_v${profile.version}`;
      loadKnowledgeBasePrompts(collectionName);
    }
  }, [profile]);

  // Update completion percentage when form changes
  useEffect(() => {
    const basePercentage = calculateCompletionPercentage(watchedFields);

    // Add bonus points for ChromaDB integration
    let bonusPercentage = 0;
    if (resourceCount > 0) bonusPercentage += 10; // Files uploaded
    if (watchedFields.assessment_prompt?.trim()) bonusPercentage += 5;
    if (watchedFields.presentation_prompt?.trim()) bonusPercentage += 5;
    if (watchedFields.gap_analysis_prompt?.trim()) bonusPercentage += 5;

    setCompletionPercentage(Math.min(100, basePercentage + bonusPercentage));
  }, [watchedFields, resourceCount]);

  // Auto-balance domain weights
  const autoBalanceWeights = () => {
    const domains = watchedFields.exam_domains;
    if (domains.length === 0) return;

    const evenWeight = Math.floor(100 / domains.length);
    const remainder = 100 % domains.length;

    domains.forEach((domain, index) => {
      const weight = evenWeight + (index < remainder ? 1 : 0);
      setValue(`exam_domains.${index}.weight_percentage`, weight);
    });

    toast.success('Domain weights balanced automatically');
  };

  // Handle ChromaDB collection creation
  const handleCreateCollection = async () => {
    if (!profile?.id) return;

    try {
      const response = await fetch(`/api/presgen-assess/files/collections/${profile.id}/create`, {
        method: 'POST'
      });

      if (response.ok) {
        setCollectionCreated(true);
        toast.success('ChromaDB collection created successfully');
      } else {
        const error = await response.json();
        toast.error(error.error || 'Failed to create collection');
      }
    } catch (error) {
      toast.error('Failed to create ChromaDB collection');
      console.error('Collection creation error:', error);
    }
  };

  // Handle file uploads
  const handleFilesUploaded = (files: FileUploadStatus[]) => {
    setUploadedFiles(prev => [...prev, ...files]);
    setResourceCount(prev => prev + files.length);

    // Switch to resources tab to show uploaded files
    setActiveTab('resources');

    toast.success(`${files.length} file(s) uploaded successfully`);
  };

  // Handle resource deletion
  const handleResourceDeleted = (fileId: string) => {
    setUploadedFiles(prev => prev.filter(f => f.file_id !== fileId));
    setResourceCount(prev => prev - 1);
    toast.success('Resource deleted successfully');
  };

  // Legacy prompt handling functions removed - no longer needed with separated prompt components

  // Handle form submission
  const onSubmit = async (data: FormData) => {
    try {
      setSaving(true);

      // Transform topics from string to array for each domain
      const transformedData = {
        ...data,
        exam_domains: data.exam_domains.map(domain => ({
          ...domain,
          topics: typeof domain.topics === 'string'
            ? domain.topics.split(',').map(topic => topic.trim()).filter(topic => topic.length > 0)
            : domain.topics || []
        }))
      };

      // Remove empty ChromaDB prompt fields to avoid overriding saved prompts from Knowledge Base tab
      // Only include prompt fields if they have actual content
      const promptFields = ['assessment_prompt', 'presentation_prompt', 'gap_analysis_prompt', 'bundle_version', 'resource_binding_enabled'];
      promptFields.forEach(field => {
        if (field === 'resource_binding_enabled') {
          // Keep boolean fields as-is
          return;
        }
        if (field === 'bundle_version') {
          // Keep bundle_version if it's not the default
          if (transformedData[field] === 'v1.0') {
            delete transformedData[field];
          }
          return;
        }
        // Remove prompt fields if they're empty to avoid overriding saved prompts
        if (!transformedData[field] || transformedData[field].trim() === '') {
          delete transformedData[field];
        }
      });

      // Validate domain weights
      const validation = validateDomainWeights(transformedData.exam_domains);
      if (!validation.isValid) {
        toast.error(validation.error);
        return;
      }

      console.log('Submitting enhanced certification profile:', JSON.stringify(transformedData, null, 2));

      let result: CertificationProfile;

      if (mode === 'edit' && profile) {
        result = await CertificationAPI.update(profile.id, transformedData);
      } else {
        result = await CertificationAPI.create(transformedData);

        // Create ChromaDB collection for new profiles
        if (result.id) {
          setTimeout(async () => {
            try {
              await fetch(`/api/presgen-assess/files/collections/${result.id}/create`, {
                method: 'POST'
              });
              setCollectionCreated(true);
            } catch (error) {
              console.error('Failed to create collection:', error);
            }
          }, 1000);
        }
      }

      toast.success(`Certification profile ${mode === 'edit' ? 'updated' : 'created'} successfully`);
      onSave?.(result);

    } catch (error) {
      console.error('Error saving certification profile:', error);
      toast.error(error instanceof Error ? error.message : 'Failed to save certification profile');
    } finally {
      setSaving(false);
    }
  };

  const getCertificationContext = () => ({
    name: watchedFields.name || 'Certification',
    domains: watchedFields.exam_domains.map(d => d.name).filter(Boolean),
    industryContext: watchedFields.provider || 'Professional certification'
  });

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header with Progress */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-gray-900">
            {mode === 'edit' ? 'Edit' : 'Create'} Certification Profile
          </h2>
          <p className="text-gray-600">
            Configure your certification with advanced ChromaDB RAG integration
          </p>
        </div>

        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-600">Progress:</span>
            <Progress value={completionPercentage} className="w-24" />
            <span className="text-sm font-medium">{completionPercentage}%</span>
          </div>

          {resourceCount > 0 && (
            <Badge variant="outline" className="text-green-700 border-green-200">
              <FileText className="w-3 h-3 mr-1" />
              {resourceCount} files
            </Badge>
          )}
        </div>
      </div>

      <form onSubmit={handleSubmit(onSubmit)} className="space-y-6">
        <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
          <TabsList className="grid w-full grid-cols-4">
            <TabsTrigger value="basic" className="flex items-center space-x-2">
              <Settings className="w-4 h-4" />
              <span>Basic Info</span>
            </TabsTrigger>
            <TabsTrigger value="files" className="flex items-center space-x-2">
              <Upload className="w-4 h-4" />
              <span>File Upload</span>
            </TabsTrigger>
            <TabsTrigger value="resources" className="flex items-center space-x-2">
              <Database className="w-4 h-4" />
              <span>Resources</span>
              {resourceCount > 0 && (
                <Badge variant="secondary" className="ml-1 text-xs">
                  {resourceCount}
                </Badge>
              )}
            </TabsTrigger>
            <TabsTrigger value="prompts" className="flex items-center space-x-2">
              <Wand2 className="w-4 h-4" />
              <span>Prompts</span>
            </TabsTrigger>
          </TabsList>

          {/* Basic Information Tab */}
          <TabsContent value="basic" className="mt-6 space-y-6">
            <Card>
              <CardHeader>
                <CardTitle>Basic Information</CardTitle>
                <CardDescription>
                  Configure the fundamental properties of your certification profile
                </CardDescription>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="name">Certification Name *</Label>
                    <Input
                      id="name"
                      placeholder="e.g., AWS Solutions Architect Associate"
                      className={errors.name ? 'border-red-500' : ''}
                      {...register('name')}
                    />
                    {errors.name && (
                      <p className="text-sm text-red-600 mt-1">{errors.name.message}</p>
                    )}
                  </div>

                  <div>
                    <Label htmlFor="version">Version *</Label>
                    <Input
                      id="version"
                      placeholder="e.g., SAA-C03"
                      className={errors.version ? 'border-red-500' : ''}
                      {...register('version')}
                    />
                    {errors.version && (
                      <p className="text-sm text-red-600 mt-1">{errors.version.message}</p>
                    )}
                  </div>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div>
                    <Label htmlFor="provider">Provider *</Label>
                    <Input
                      id="provider"
                      placeholder="e.g., AWS, Microsoft, CompTIA"
                      className={errors.provider ? 'border-red-500' : ''}
                      {...register('provider')}
                    />
                    {errors.provider && (
                      <p className="text-sm text-red-600 mt-1">{errors.provider.message}</p>
                    )}
                  </div>

                  <div>
                    <Label htmlFor="exam_code">Exam Code</Label>
                    <Input
                      id="exam_code"
                      placeholder="e.g., SAA-C03"
                      {...register('exam_code')}
                    />
                  </div>
                </div>

                <div>
                  <Label htmlFor="description">Description</Label>
                  <Textarea
                    id="description"
                    placeholder="Brief description of this certification..."
                    className="min-h-[80px]"
                    {...register('description')}
                  />
                </div>

                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <Label htmlFor="passing_score">Passing Score (%)</Label>
                    <Input
                      id="passing_score"
                      type="number"
                      min="0"
                      max="100"
                      placeholder="e.g., 72"
                      {...register('passing_score', { valueAsNumber: true })}
                      className={errors.passing_score ? 'border-red-500' : ''}
                    />
                    {errors.passing_score && (
                      <p className="text-sm text-red-500 mt-1">{errors.passing_score.message}</p>
                    )}
                  </div>

                  <div>
                    <Label htmlFor="exam_duration_minutes">Duration (minutes)</Label>
                    <Input
                      id="exam_duration_minutes"
                      type="number"
                      min="1"
                      placeholder="e.g., 130"
                      {...register('exam_duration_minutes', { valueAsNumber: true })}
                    />
                  </div>

                  <div>
                    <Label htmlFor="question_count">Question Count</Label>
                    <Input
                      id="question_count"
                      type="number"
                      min="1"
                      placeholder="e.g., 65"
                      {...register('question_count', { valueAsNumber: true })}
                    />
                  </div>
                </div>

                {/* ChromaDB Settings */}
                <div className="border-t pt-4">
                  <h4 className="font-medium mb-3">ChromaDB Integration Settings</h4>
                  <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    <div>
                      <Label htmlFor="bundle_version">Bundle Version</Label>
                      <Input
                        id="bundle_version"
                        placeholder="v1.0"
                        {...register('bundle_version')}
                      />
                      <p className="text-xs text-gray-500 mt-1">
                        Version for knowledge base content bundles
                      </p>
                    </div>

                    <div className="flex items-center space-x-2 pt-6">
                      <Switch
                        id="resource_binding_enabled"
                        checked={watchedFields.resource_binding_enabled}
                        onCheckedChange={(checked) => setValue('resource_binding_enabled', checked)}
                      />
                      <Label htmlFor="resource_binding_enabled" className="text-sm">
                        Enable cascade delete for resources
                      </Label>
                    </div>
                  </div>
                </div>

                {/* Exam Domains */}
                <div className="border-t pt-4">
                  <div className="flex items-center justify-between mb-4">
                    <h4 className="font-medium">Exam Domains</h4>
                    <div className="flex items-center space-x-2">
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={autoBalanceWeights}
                        disabled={fields.length === 0}
                      >
                        Auto Balance
                      </Button>
                      <Button
                        type="button"
                        variant="outline"
                        size="sm"
                        onClick={() => append(createDefaultExamDomain())}
                      >
                        <Plus className="w-4 h-4 mr-1" />
                        Add Domain
                      </Button>
                    </div>
                  </div>

                  {/* Domain weight validation error */}
                  {errors.exam_domains && typeof errors.exam_domains.message === 'string' && (
                    <div className="bg-red-50 border border-red-200 rounded-lg p-3">
                      <p className="text-sm text-red-600 flex items-center">
                        <AlertCircle className="w-4 h-4 mr-2" />
                        {errors.exam_domains.message}
                      </p>
                    </div>
                  )}

                  <div className="space-y-4">
                    {fields.map((field, index) => (
                      <Card key={field.id} className="p-4">
                        <div className="flex items-start space-x-4">
                          <div className="flex-1 space-y-3">
                            <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                              <div className="md:col-span-2">
                                <Label htmlFor={`exam_domains.${index}.name`}>Domain Name *</Label>
                                <Input
                                  placeholder="e.g., Design Secure Architectures"
                                  className={errors.exam_domains?.[index]?.name ? 'border-red-500' : ''}
                                  {...register(`exam_domains.${index}.name`)}
                                />
                                {errors.exam_domains?.[index]?.name && (
                                  <p className="text-sm text-red-600 mt-1">
                                    {errors.exam_domains[index]?.name?.message}
                                  </p>
                                )}
                              </div>
                              <div>
                                <Label htmlFor={`exam_domains.${index}.weight_percentage`}>
                                  Weight (%) *
                                </Label>
                                <Input
                                  type="number"
                                  min="1"
                                  max="100"
                                  placeholder="30"
                                  className={errors.exam_domains?.[index]?.weight_percentage ? 'border-red-500' : ''}
                                  {...register(`exam_domains.${index}.weight_percentage`, { valueAsNumber: true })}
                                />
                                {errors.exam_domains?.[index]?.weight_percentage && (
                                  <p className="text-sm text-red-600 mt-1">
                                    {errors.exam_domains[index]?.weight_percentage?.message}
                                  </p>
                                )}
                              </div>
                            </div>

                            <div>
                              <Label htmlFor={`exam_domains.${index}.topics`}>Topics/Skills</Label>
                              <Textarea
                                placeholder="Enter topics separated by commas..."
                                className="min-h-[60px]"
                                {...register(`exam_domains.${index}.topics`)}
                              />
                            </div>
                          </div>

                          <Button
                            type="button"
                            variant="outline"
                            size="sm"
                            onClick={() => remove(index)}
                            disabled={fields.length === 1}
                            className="text-red-600 hover:text-red-700"
                          >
                            <Trash2 className="w-4 h-4" />
                          </Button>
                        </div>
                      </Card>
                    ))}
                  </div>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          {/* File Upload Tab */}
          <TabsContent value="files" className="mt-6">
            <Card>
              <CardHeader>
                <CardTitle>Upload Certification Resources</CardTitle>
                <CardDescription>
                  Upload exam guides, transcripts, and supplemental materials for ChromaDB RAG integration
                </CardDescription>
              </CardHeader>
              <CardContent>
                {profile?.id ? (
                  <FileUploadZone
                    certProfileId={profile.id}
                    onFilesUploaded={handleFilesUploaded}
                    maxFiles={20}
                    acceptedTypes={['.pdf', '.docx', '.txt', '.md']}
                    className="mb-6"
                  />
                ) : (
                  <div className="text-center py-8 text-gray-500">
                    <Upload className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                    <p>Save the certification profile first to enable file uploads</p>
                  </div>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          {/* Resources Management Tab */}
          <TabsContent value="resources" className="mt-6">
            {profile?.id ? (
              <ResourceManager
                certProfileId={profile.id}
                onResourceDeleted={handleResourceDeleted}
                onResourcesChanged={() => {
                  // Refresh resource count
                  setResourceCount(prev => prev);
                }}
              />
            ) : (
              <Card>
                <CardContent className="text-center py-8 text-gray-500">
                  <Database className="w-12 h-12 mx-auto mb-4 text-gray-300" />
                  <p>Save the certification profile first to manage resources</p>
                </CardContent>
              </Card>
            )}
          </TabsContent>

          {/* Prompts Configuration Tab */}
          <TabsContent value="prompts" className="mt-6">
            <div className="space-y-8">
              {/* Certification Profile Prompts */}
              <CertificationPromptEditor
                profileId={profile?.id}
                certificationName={watch('name')}
                initialPrompts={{
                  assessment_prompt: watch('assessment_prompt'),
                  presentation_prompt: watch('presentation_prompt'),
                  gap_analysis_prompt: watch('gap_analysis_prompt')
                }}
                onPromptsChange={(prompts) => {
                  console.log('🎯 FORM_DEBUG: Certification prompts changed, updating form values:', prompts);
                  setValue('assessment_prompt', prompts.assessment_prompt || '');
                  setValue('presentation_prompt', prompts.presentation_prompt || '');
                  setValue('gap_analysis_prompt', prompts.gap_analysis_prompt || '');
                }}
                certificationContext={getCertificationContext()}
              />

              {/* Knowledge Base Prompts */}
              <KnowledgeBasePromptEditor
                collectionName={`${watch('name')?.toLowerCase().replace(/ /g, '_')}_v${watch('version')}`}
                certificationName={watch('name')}
                initialPrompts={knowledgeBasePrompts}
                onPromptsChange={(kbPrompts) => {
                  console.log('🎯 PROMPT_DEBUG: Knowledge base prompts changed:', kbPrompts);
                  const collectionName = `${watch('name')?.toLowerCase().replace(/ /g, '_')}_v${watch('version')}`;
                  saveKnowledgeBasePrompts(collectionName, kbPrompts);
                }}
              />

              {/* Legacy Prompt Editor - DISABLED to prevent coupling issues */}
              <Card className="border-gray-200 bg-gray-50 opacity-50">
                <CardHeader>
                  <CardTitle className="text-gray-600 flex items-center">
                    <AlertCircle className="w-5 h-5 mr-2" />
                    Legacy Prompt Editor - DISABLED
                  </CardTitle>
                  <CardDescription className="text-gray-500">
                    This component has been disabled to prevent prompt coupling issues. Use the separated prompt editors above.
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-center py-8 text-gray-400">
                    <X className="w-12 h-12 mx-auto mb-4" />
                    <p>Legacy component disabled - use separated prompt editors above</p>
                  </div>
                </CardContent>
              </Card>
            </div>
          </TabsContent>
        </Tabs>

        {/* Validation Errors Debug Section */}
        {!isValid && Object.keys(errors).length > 0 && (
          <Card className="border-red-200 bg-red-50">
            <CardHeader>
              <CardTitle className="text-red-800 flex items-center">
                <AlertCircle className="w-5 h-5 mr-2" />
                Validation Errors
              </CardTitle>
              <CardDescription className="text-red-700">
                Please fix the following issues before saving:
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="space-y-2">
                {Object.entries(errors).map(([fieldName, error]) => (
                  <div key={fieldName} className="text-sm">
                    <span className="font-medium text-red-800">
                      {fieldName.replace(/_/g, ' ').replace(/([A-Z])/g, ' $1').toLowerCase()}:
                    </span>
                    <span className="text-red-700 ml-2">
                      {typeof error?.message === 'string'
                        ? error.message
                        : Array.isArray(error)
                        ? `${error.length} field errors`
                        : JSON.stringify(error) || 'Invalid value'
                      }
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Form Actions */}
        <div className="flex items-center justify-between pt-6 border-t">
          <div className="flex items-center space-x-2">
            {!isValid && (
              <div className="flex items-center text-red-600">
                <AlertCircle className="w-4 h-4 mr-1" />
                <span className="text-sm">Please fix validation errors above</span>
              </div>
            )}

            {isValid && completionPercentage === 100 && (
              <div className="flex items-center text-green-600">
                <CheckCircle className="w-4 h-4 mr-1" />
                <span className="text-sm">Ready to save</span>
              </div>
            )}
          </div>

          <div className="flex items-center space-x-3">
            <Button
              type="button"
              variant="outline"
              onClick={onCancel}
              disabled={saving}
            >
              <X className="w-4 h-4 mr-1" />
              Cancel
            </Button>

            <Button
              type="submit"
              disabled={!isValid || saving}
            >
              <Save className="w-4 h-4 mr-1" />
              {saving ? 'Saving...' : mode === 'edit' ? 'Update Profile' : 'Create Profile'}
            </Button>
          </div>
        </div>
      </form>
    </div>
  );
}