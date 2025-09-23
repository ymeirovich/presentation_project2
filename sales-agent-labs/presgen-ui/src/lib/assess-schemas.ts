import { z } from 'zod'

export const CertificationDomainSchema = z.object({
  name: z.string(),
  weight_percentage: z.number().int(),
  topics: z.array(z.string()),
})

export const CertificationProfileSchema = z.object({
  id: z.string().uuid(),
  name: z.string(),
  version: z.string(),
  provider: z.string(),
  description: z.string().nullable().optional(),
  exam_code: z.string().nullable().optional(),
  passing_score: z.number().int().nullable().optional(),
  exam_duration_minutes: z.number().int().nullable().optional(),
  question_count: z.number().int().nullable().optional(),
  exam_domains: z.array(CertificationDomainSchema),
})

export type CertificationProfile = z.infer<typeof CertificationProfileSchema>
export type CertificationDomain = z.infer<typeof CertificationDomainSchema>

export const DomainDistributionEntrySchema = z.object({
  domain: z.string().min(1, 'Domain name is required'),
  questionCount: z.coerce.number({ invalid_type_error: 'Enter a number' })
    .int('Question count must be an integer')
    .min(0, 'Question count cannot be negative'),
})

export const AssessmentFormSchema = z.object({
  certificationId: z.string().uuid('Select a certification profile'),
  title: z.string().min(3, 'Title must be at least 3 characters').max(200),
  summaryMarkdown: z.string().min(30, 'Provide at least 30 characters of context').max(4000),
  difficulty: z.enum(['beginner', 'intermediate', 'advanced']),
  questionCount: z.coerce.number({ invalid_type_error: 'Question count is required' })
    .int('Question count must be a whole number')
    .min(5, 'Minimum 5 questions')
    .max(50, 'Maximum 50 questions'),
  passingScore: z.coerce.number({ invalid_type_error: 'Passing score is required' })
    .int('Passing score must be a whole number')
    .min(0, 'Minimum passing score is 0%')
    .max(100, 'Maximum passing score is 100%'),
  timeLimitMinutes: z.union([
    z.coerce.number({ invalid_type_error: 'Enter a number or leave blank' })
      .int('Time limit must be a whole number')
      .min(10, 'Minimum 10 minutes')
      .max(240, 'Maximum 240 minutes'),
    z.literal(''),
  ]).transform((value) => (value === '' ? undefined : value)),
  slideCount: z.coerce.number({ invalid_type_error: 'Slide count is required' })
    .int('Slide count must be a whole number')
    .min(5, 'Minimum 5 slides')
    .max(40, 'Maximum 40 slides'),
  includeAvatar: z.boolean().default(false),
  domainDistribution: z.array(DomainDistributionEntrySchema).min(1, 'Add at least one domain'),
  notesMarkdown: z.string().max(4000, 'Maximum 4000 characters').optional().default(''),
}).superRefine((data, ctx) => {
  const total = data.domainDistribution.reduce((sum, entry) => sum + entry.questionCount, 0)
  if (total !== data.questionCount) {
    ctx.addIssue({
      code: z.ZodIssueCode.custom,
      path: ['domainDistribution'],
      message: `Domain counts (${total}) must equal total question count (${data.questionCount})`,
    })
  }
})

export type AssessmentFormValues = z.infer<typeof AssessmentFormSchema>
export type DomainDistributionEntry = z.infer<typeof DomainDistributionEntrySchema>

export const AssessmentWorkflowResponseSchema = z.object({
  id: z.string().uuid(),
  status: z.string(),
  workflow_type: z.string(),
  resume_token: z.string().nullable().optional(),
  progress: z.number().int(),
  created_at: z.string(),
  updated_at: z.string(),
  parameters: z.record(z.unknown()).optional(),
})

export type AssessmentWorkflowResponse = z.infer<typeof AssessmentWorkflowResponseSchema>

// Extended workflow schemas for timeline and management
export const WorkflowStepSchema = z.object({
  step: z.string(),
  status: z.enum(['pending', 'in_progress', 'completed', 'failed']),
  started_at: z.string().nullable().optional(),
  completed_at: z.string().nullable().optional(),
  error_message: z.string().nullable().optional(),
  duration_seconds: z.number().nullable().optional(),
})

export const WorkflowDetailSchema = z.object({
  id: z.string().uuid(),
  user_id: z.string(),
  certification_profile_id: z.string().uuid(),
  current_step: z.string(),
  execution_status: z.enum(['pending', 'in_progress', 'completed', 'failed', 'awaiting_completion']),
  workflow_type: z.string(),
  parameters: z.record(z.unknown()).optional(),
  progress: z.number().int().min(0).max(100),
  created_at: z.string(),
  updated_at: z.string(),
  estimated_completion_at: z.string().nullable().optional(),
  completed_at: z.string().nullable().optional(),
  resume_token: z.string().nullable().optional(),
  error_message: z.string().nullable().optional(),
  step_execution_log: z.array(WorkflowStepSchema).optional(),
})

export const WorkflowListResponseSchema = z.array(WorkflowDetailSchema)

export type WorkflowStep = z.infer<typeof WorkflowStepSchema>
export type WorkflowDetail = z.infer<typeof WorkflowDetailSchema>
export type WorkflowListResponse = z.infer<typeof WorkflowListResponseSchema>

export interface AssessmentRequestPayload {
  user_id: string
  certification_profile_id: string
  workflow_type: 'assessment_generation'
  parameters: Record<string, unknown>
}

export interface WorkflowStatusUpdate {
  status: string
  progress?: number
  error_message?: string
}

export const DEFAULT_DOMAIN_ENTRY: DomainDistributionEntry = {
  domain: 'General',
  questionCount: 5,
}

export const AssessmentDifficultyOptions = [
  { value: 'beginner', label: 'Beginner' },
  { value: 'intermediate', label: 'Intermediate' },
  { value: 'advanced', label: 'Advanced' },
] as const

// Gap Analysis Schemas
export const BloomTaxonomyLevelSchema = z.object({
  level: z.enum(['remember', 'understand', 'apply', 'analyze', 'evaluate', 'create']),
  label: z.string(),
  score: z.number().min(0).max(100),
  question_count: z.number().int().min(0),
  correct_count: z.number().int().min(0),
})

export const DomainPerformanceSchema = z.object({
  domain: z.string(),
  score: z.number().min(0).max(100),
  question_count: z.number().int().min(0),
  correct_count: z.number().int().min(0),
  confidence_score: z.number().min(0).max(100),
  overconfidence_ratio: z.number().min(0),
  bloom_levels: z.array(BloomTaxonomyLevelSchema),
})

export const LearningGapSchema = z.object({
  domain: z.string(),
  gap_severity: z.enum(['low', 'medium', 'high', 'critical']),
  confidence_gap: z.number(),
  skill_gap: z.number().min(0).max(100),
  recommended_study_hours: z.number().min(0),
  priority_topics: z.array(z.string()),
  remediation_resources: z.array(z.object({
    title: z.string(),
    type: z.enum(['article', 'video', 'practice', 'documentation']),
    url: z.string().url(),
    estimated_time_minutes: z.number().int().min(0),
  })),
})

export const GapAnalysisResultSchema = z.object({
  workflow_id: z.string().uuid(),
  overall_score: z.number().min(0).max(100),
  overall_confidence: z.number().min(0).max(100),
  overconfidence_indicator: z.boolean(),
  domain_performance: z.array(DomainPerformanceSchema),
  learning_gaps: z.array(LearningGapSchema),
  bloom_taxonomy_breakdown: z.array(BloomTaxonomyLevelSchema),
  recommended_study_plan: z.object({
    total_estimated_hours: z.number().min(0),
    priority_domains: z.array(z.string()),
    study_sequence: z.array(z.string()),
  }),
  generated_at: z.string(),
})

export type BloomTaxonomyLevel = z.infer<typeof BloomTaxonomyLevelSchema>
export type DomainPerformance = z.infer<typeof DomainPerformanceSchema>
export type LearningGap = z.infer<typeof LearningGapSchema>
export type GapAnalysisResult = z.infer<typeof GapAnalysisResultSchema>

export const BLOOM_TAXONOMY_LEVELS = [
  { value: 'remember', label: 'Remember', color: '#e3f2fd' },
  { value: 'understand', label: 'Understand', color: '#bbdefb' },
  { value: 'apply', label: 'Apply', color: '#90caf9' },
  { value: 'analyze', label: 'Analyze', color: '#64b5f6' },
  { value: 'evaluate', label: 'Evaluate', color: '#42a5f5' },
  { value: 'create', label: 'Create', color: '#2196f3' },
] as const

export const GAP_SEVERITY_COLORS = {
  low: '#4caf50',
  medium: '#ff9800',
  high: '#f44336',
  critical: '#d32f2f',
} as const
