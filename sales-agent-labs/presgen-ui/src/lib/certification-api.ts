/**
 * API client for Certification Profile management
 */

import { z } from 'zod';

// Use Next.js API routes as proxy to PresGen-Assess backend
const API_BASE = '/api/presgen-assess';

// Zod schemas for validation (matching backend API schema)
export const ExamDomainSchema = z.object({
  name: z.string().min(1),
  weight_percentage: z.number().int().min(1).max(100),
  topics: z.array(z.string()).default([])
});

export const CertificationProfileSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1).max(255),
  version: z.string().min(1).max(100),
  provider: z.string(),
  description: z.string().optional().nullable(),
  exam_code: z.string().optional().nullable(),
  passing_score: z.number().optional().nullable(),
  exam_duration_minutes: z.number().optional().nullable(),
  question_count: z.number().optional().nullable(),
  exam_domains: z.array(ExamDomainSchema),
  prerequisites: z.array(z.string()),
  recommended_experience: z.string().optional().nullable(),
  is_active: z.boolean(),
  knowledge_base_path: z.string().optional(), // Optional since it's internal
  assessment_template: z.record(z.any()).optional().nullable(),
  created_at: z.string(), // Accept any datetime format
  updated_at: z.string(),  // Accept any datetime format
  // ChromaDB integration fields
  bundle_version: z.string().optional(),
  assessment_prompt: z.string().optional(),
  presentation_prompt: z.string().optional(),
  gap_analysis_prompt: z.string().optional(),
  resource_binding_enabled: z.boolean().optional()
});

export const CertificationProfileCreateSchema = z.object({
  name: z.string().min(1).max(255),
  version: z.string().min(1).max(100),
  provider: z.string().min(1).max(255),
  description: z.string().optional(),
  exam_code: z.string().max(50).optional(),
  passing_score: z.number().int().min(0).max(100).optional(),
  exam_duration_minutes: z.number().int().min(1).optional(),
  question_count: z.number().int().min(1).optional(),
  exam_domains: z.array(ExamDomainSchema).refine(
    (domains) => {
      const totalWeight = domains.reduce((sum, domain) => sum + domain.weight_percentage, 0);
      return totalWeight === 100;
    },
    { message: "Domain weights must sum to 100%" }
  ),
  prerequisites: z.array(z.string()).default([]),
  recommended_experience: z.string().optional(),
  assessment_template: z.record(z.any()).optional(),
  is_active: z.boolean().default(true),
  // ChromaDB integration fields
  bundle_version: z.string().optional(),
  assessment_prompt: z.string().optional(),
  presentation_prompt: z.string().optional(),
  gap_analysis_prompt: z.string().optional(),
  resource_binding_enabled: z.boolean().optional()
});

export const CertificationProfileUpdateSchema = CertificationProfileCreateSchema.partial();

export const ValidationResultSchema = z.object({
  profile_id: z.string().uuid(),
  validation_timestamp: z.string().datetime(),
  is_valid: z.boolean(),
  warnings: z.array(z.string()),
  errors: z.array(z.string()),
  recommendations: z.array(z.string())
});

export const StatisticsSchema = z.object({
  profile_info: z.object({
    name: z.string(),
    version: z.string(),
    created_at: z.string().datetime(),
    updated_at: z.string().datetime()
  }),
  exam_domains: z.object({
    total_domains: z.number(),
    domain_breakdown: z.array(z.object({
      domain: z.string(),
      weight: z.number(),
      subdomains_count: z.number(),
      skills_count: z.number()
    }))
  }),
  knowledge_base: z.object({
    path: z.string(),
    documents_count: z.number(),
    processing_status: z.string()
  }),
  assessments: z.object({
    total_assessments: z.number(),
    completed_assessments: z.number(),
    average_score: z.number()
  }),
  gap_analysis: z.object({
    total_analyses: z.number(),
    common_gaps: z.array(z.string()),
    improvement_trends: z.array(z.string())
  })
});

// Type exports
export type ExamDomain = z.infer<typeof ExamDomainSchema>;
export type CertificationProfile = z.infer<typeof CertificationProfileSchema>;
export type CertificationProfileCreate = z.infer<typeof CertificationProfileCreateSchema>;
export type CertificationProfileUpdate = z.infer<typeof CertificationProfileUpdateSchema>;
export type ValidationResult = z.infer<typeof ValidationResultSchema>;
export type Statistics = z.infer<typeof StatisticsSchema>;

// API functions
export class CertificationAPI {
  private static async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${API_BASE}/certifications${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
      console.error('API Error Details:');
      console.error('Status:', response.status);
      console.error('Status Text:', response.statusText);
      console.error('URL:', response.url);
      console.error('Error Response:', JSON.stringify(error, null, 2));

      // Get the actual error message
      let errorMessage = 'Unknown error';
      if (error.detail) {
        errorMessage = error.detail;
      } else if (error.message) {
        errorMessage = error.message;
      } else if (typeof error === 'string') {
        errorMessage = error;
      } else {
        errorMessage = `HTTP ${response.status}: ${response.statusText}`;
      }

      throw new Error(errorMessage);
    }

    // Handle empty responses (like 204 No Content for deletes)
    if (response.status === 204 || response.headers.get('content-length') === '0') {
      return null;
    }

    try {
      return response.json();
    } catch {
      // If response has no JSON content, return null
      return null;
    }
  }

  // List all certification profiles
  static async list(params: { skip?: number; limit?: number } = {}): Promise<CertificationProfile[]> {
    const query = new URLSearchParams();
    if (params.skip !== undefined) query.set('skip', params.skip.toString());
    if (params.limit !== undefined) query.set('limit', params.limit.toString());

    const queryString = query.toString();
    const endpoint = queryString ? `/?${queryString}` : '/';

    const profiles = await this.request<CertificationProfile[]>(endpoint);
    // Use safeParse to handle schema mismatches gracefully
    return profiles.map(profile => {
      const result = CertificationProfileSchema.safeParse(profile);
      if (result.success) {
        return result.data;
      } else {
        console.warn('Profile schema validation failed, using raw data:', result.error);
        return profile as CertificationProfile;
      }
    });
  }

  // Get single certification profile
  static async get(id: string): Promise<CertificationProfile> {
    const profile = await this.request<CertificationProfile>(`/${id}`);
    const result = CertificationProfileSchema.safeParse(profile);
    if (result.success) {
      return result.data;
    } else {
      console.warn('Profile schema validation failed, using raw data:', result.error);
      return profile as CertificationProfile;
    }
  }

  // Create new certification profile
  static async create(data: CertificationProfileCreate): Promise<CertificationProfile> {
    const validatedData = CertificationProfileCreateSchema.parse(data);
    const profile = await this.request<CertificationProfile>('/', {
      method: 'POST',
      body: JSON.stringify(validatedData),
    });
    const result = CertificationProfileSchema.safeParse(profile);
    if (result.success) {
      return result.data;
    } else {
      console.warn('Profile schema validation failed, using raw data:', result.error);
      return profile as CertificationProfile;
    }
  }

  // Update certification profile
  static async update(id: string, data: CertificationProfileUpdate): Promise<CertificationProfile> {
    const validatedData = CertificationProfileUpdateSchema.parse(data);
    const profile = await this.request<CertificationProfile>(`/${id}`, {
      method: 'PUT',
      body: JSON.stringify(validatedData),
    });
    const result = CertificationProfileSchema.safeParse(profile);
    if (result.success) {
      return result.data;
    } else {
      console.warn('Profile schema validation failed, using raw data:', result.error);
      return profile as CertificationProfile;
    }
  }

  // Delete certification profile
  static async delete(id: string): Promise<void> {
    await this.request(`/delete`, {
      method: 'POST',
      body: JSON.stringify({ id }),
    });
  }

  // Search certification profiles
  static async search(name: string): Promise<CertificationProfile[]> {
    const profiles = await this.request<CertificationProfile[]>(`/search/${encodeURIComponent(name)}`);
    return profiles.map(profile => {
      const result = CertificationProfileSchema.safeParse(profile);
      if (result.success) {
        return result.data;
      } else {
        console.warn('Profile schema validation failed, using raw data:', result.error);
        return profile as CertificationProfile;
      }
    });
  }

  // Duplicate certification profile
  static async duplicate(
    id: string,
    newName: string,
    newVersion: string
  ): Promise<CertificationProfile> {
    const query = new URLSearchParams({
      new_name: newName,
      new_version: newVersion
    });

    const profile = await this.request<CertificationProfile>(
      `/${id}/duplicate?${query.toString()}`,
      { method: 'POST' }
    );
    const result = CertificationProfileSchema.safeParse(profile);
    if (result.success) {
      return result.data;
    } else {
      console.warn('Profile schema validation failed, using raw data:', result.error);
      return profile as CertificationProfile;
    }
  }

  // Get certification profile statistics
  static async getStatistics(id: string): Promise<Statistics> {
    const stats = await this.request<Statistics>(`/${id}/statistics`);
    return StatisticsSchema.parse(stats);
  }

  // Validate certification profile
  static async validate(id: string): Promise<ValidationResult> {
    const validation = await this.request<ValidationResult>(`/${id}/validate`, {
      method: 'POST'
    });
    return ValidationResultSchema.parse(validation);
  }
}

// React hooks for certification profiles
export const useCertificationProfiles = () => {
  // This would typically use React Query or SWR for caching
  // For now, returning a simple wrapper
  return {
    list: CertificationAPI.list,
    get: CertificationAPI.get,
    create: CertificationAPI.create,
    update: CertificationAPI.update,
    delete: CertificationAPI.delete,
    search: CertificationAPI.search,
    duplicate: CertificationAPI.duplicate,
    getStatistics: CertificationAPI.getStatistics,
    validate: CertificationAPI.validate
  };
};

// Error handling helper
export class CertificationAPIError extends Error {
  constructor(
    message: string,
    public status?: number,
    public details?: unknown
  ) {
    super(message);
    this.name = 'CertificationAPIError';
  }
}

// Helper function to format exam domains for display
export const formatExamDomains = (domains: ExamDomain[]): string => {
  return domains
    .map(domain => `${domain.name} (${domain.weight_percentage}%)`)
    .join(', ');
};

// Helper function to validate domain weights
export const validateDomainWeights = (domains: ExamDomain[]): { isValid: boolean; error?: string } => {
  const totalWeight = domains.reduce((sum, domain) => sum + domain.weight_percentage, 0);

  if (totalWeight !== 100) {
    return {
      isValid: false,
      error: `Domain weights sum to ${totalWeight}%, must equal 100%`
    };
  }

  return { isValid: true };
};

// Helper function to create default exam domain
export const createDefaultExamDomain = (): ExamDomain => ({
  name: '',
  weight_percentage: 0,
  topics: []
});

// Helper function to calculate completion percentage
export const calculateCompletionPercentage = (profile: Partial<CertificationProfileCreate>): number => {
  let completed = 0;
  const total = 4; // name, version, domains, assessment_template

  if (profile.name && profile.name.trim()) completed++;
  if (profile.version && profile.version.trim()) completed++;
  if (profile.exam_domains && profile.exam_domains.length > 0) {
    const validation = validateDomainWeights(profile.exam_domains);
    if (validation.isValid) completed++;
  }
  if (profile.assessment_template) completed++;

  return Math.round((completed / total) * 100);
};