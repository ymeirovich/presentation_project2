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
  questionCount: z.coerce.number()
    .refine(Number.isInteger, { message: 'Question count must be an integer' })
    .min(0),
})

export const AssessmentFormSchema = z.object({
  certificationId: z.string().uuid('Select a certification profile'),
  learnerEmail: z.union([
    z.string().email('Please enter a valid email address'),
    z.literal(''),
  ]).transform((value) => (value === '' ? undefined : value)),
  title: z.string().min(3, 'Title must be at least 3 characters').max(200),
  summaryMarkdown: z.string().min(30, 'Provide at least 30 characters of context').max(4000),
  difficulty: z.enum(['beginner', 'intermediate', 'advanced']),
  questionCount: z.coerce.number()
    .refine(Number.isInteger, { message: 'Question count must be a whole number' })
    .min(5)
    .max(50),
  passingScore: z.coerce.number()
    .refine(Number.isInteger, { message: 'Passing score must be a whole number' })
    .min(0)
    .max(100),
  timeLimitMinutes: z.union([
    z.coerce.number()
      .refine(Number.isInteger, { message: 'Time limit must be a whole number' })
      .min(10)
      .max(240),
    z.literal(''),
  ]).transform((value) => (value === '' ? undefined : value)),
  slideCount: z.coerce.number()
    .refine(Number.isInteger, { message: 'Slide count must be a whole number' })
    .min(5)
    .max(40),
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
  parameters: z.record(z.string(), z.unknown()).optional(),
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

export const GeneratedContentUrlsSchema = z.object({
  form_url: z.string().optional().nullable(),
  form_edit_url: z.string().optional().nullable(),
  form_title: z.string().optional().nullable(),
}).partial().passthrough()

export const WorkflowOrchestrationStatusSchema = z.object({
  success: z.boolean().optional(),
  workflow_id: z.string().uuid().optional(),
  status: z.string().optional(),
  current_step: z.string().optional(),
  google_form_id: z.string().optional().nullable(),
  form_urls: GeneratedContentUrlsSchema.optional().nullable(),
}).passthrough()

export const WorkflowDetailSchema = z.object({
  id: z.string().uuid(),
  user_id: z.string(),
  certification_profile_id: z.string().uuid(),
  current_step: z.string(),
  execution_status: z.enum(['pending', 'in_progress', 'completed', 'failed', 'awaiting_completion']),
  workflow_type: z.string(),
  parameters: z.record(z.string(), z.unknown()).optional(),
  google_form_id: z.string().optional().nullable(),
  progress: z.number().int().min(0).max(100),
  created_at: z.string(),
  updated_at: z.string(),
  estimated_completion_at: z.string().nullable().optional(),
  completed_at: z.string().nullable().optional(),
  resume_token: z.string().nullable().optional(),
  error_message: z.string().nullable().optional(),
  step_execution_log: z.array(WorkflowStepSchema).optional(),
  generated_content_urls: GeneratedContentUrlsSchema.optional().nullable(),
})

export const WorkflowListResponseSchema = z.array(WorkflowDetailSchema)

export type WorkflowStep = z.infer<typeof WorkflowStepSchema>
export type WorkflowDetail = z.infer<typeof WorkflowDetailSchema>
export type WorkflowListResponse = z.infer<typeof WorkflowListResponseSchema>
export type GeneratedContentUrls = z.infer<typeof GeneratedContentUrlsSchema>
export type WorkflowOrchestrationStatus = z.infer<typeof WorkflowOrchestrationStatusSchema>

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

export const GapAnalysisSheetsExportSchema = z.object({
  success: z.boolean(),
  workflow_id: z.string().uuid(),
  spreadsheet_id: z.string().optional(),
  spreadsheet_url: z.string().url().optional(),
  spreadsheet_title: z.string().optional(),
  export_timestamp: z.string().optional(),
  mock_response: z.boolean().optional(),
  message: z.string().optional(),
  export_summary: z.any().optional(),
  additional_exports: z.any().optional(),
  instructions: z.array(z.string()).optional(),
})

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

// Sprint 1: Enhanced Gap Analysis Schemas

export const SkillGapSchema = z.object({
  skill_id: z.string(),
  skill_name: z.string(),
  exam_domain: z.string(),
  exam_subsection: z.string().nullable().optional(),
  severity: z.number().int().min(0).max(10),
  confidence_delta: z.number(),
  question_ids: z.array(z.string()),
})

export const Sprint1GapAnalysisResultSchema = z.object({
  workflow_id: z.string().uuid(),
  overall_score: z.number().min(0).max(100),
  total_questions: z.number().int(),
  correct_answers: z.number().int(),
  incorrect_answers: z.number().int(),
  skill_gaps: z.array(SkillGapSchema),
  performance_by_domain: z.record(z.string(), z.number()),
  text_summary: z.string(),
  charts_data: z.any().nullable().optional(),
  generated_at: z.string(),
})

export const ContentOutlineItemSchema = z.object({
  skill_id: z.string(),
  skill_name: z.string(),
  exam_domain: z.string(),
  exam_guide_section: z.string(),
  content_items: z.array(z.any()),
  rag_retrieval_score: z.number().min(0).max(1),
})

export const RecommendedCourseSchema = z.object({
  id: z.string().uuid(),
  workflow_id: z.string().uuid(),
  skill_id: z.string(),
  skill_name: z.string(),
  exam_domain: z.string(),
  exam_subsection: z.string().nullable().optional(),
  course_title: z.string(),
  course_description: z.string(),
  estimated_duration_minutes: z.number().int(),
  difficulty_level: z.enum(['beginner', 'intermediate', 'advanced']),
  learning_objectives: z.array(z.string()),
  content_outline: z.any(),
  generation_status: z.string(),
  priority: z.number().int(),
})

export const GapAnalysisSummarySchema = z.object({
  workflow_id: z.string().uuid(),
  overall_score: z.number().min(0).max(100),
  total_questions: z.number().int(),
  correct_answers: z.number().int(),
  incorrect_answers: z.number().int(),
  text_summary: z.string(),
  performance_by_domain: z.record(z.string(), z.number()),
  top_skill_gaps: z.array(SkillGapSchema),
  total_skill_gaps: z.number().int(),
  content_outlines_count: z.number().int(),
  recommended_courses_count: z.number().int(),
  charts_data: z.any(),
  generated_at: z.string(),
})

export type SkillGap = z.infer<typeof SkillGapSchema>
export type Sprint1GapAnalysisResult = z.infer<typeof Sprint1GapAnalysisResultSchema>
export type ContentOutlineItem = z.infer<typeof ContentOutlineItemSchema>
export type RecommendedCourse = z.infer<typeof RecommendedCourseSchema>
export type GapAnalysisSummary = z.infer<typeof GapAnalysisSummarySchema>
