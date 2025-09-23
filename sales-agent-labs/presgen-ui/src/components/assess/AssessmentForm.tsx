'use client'

import { useEffect, useMemo, useState } from 'react'
import { useForm, useFieldArray } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { toast } from 'sonner'
import { Loader2, Plus, RefreshCw, Sparkles, Trash2 } from 'lucide-react'

import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'
import { Input } from '@/components/ui/input'
import { Textarea } from '@/components/ui/textarea'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { AssessmentWorkflowResponse, AssessmentFormSchema, AssessmentFormValues, AssessmentDifficultyOptions, CertificationProfile, DEFAULT_DOMAIN_ENTRY, DomainDistributionEntry } from '@/lib/assess-schemas'
import { fetchCertificationProfiles, requestAssessmentWorkflow } from '@/lib/assess-api'
import { MarkdownPreview } from '@/components/MarkdownPreview'
import { ServerResponseCard, ServerResponse } from '@/components/ServerResponseCard'
import { ApiError } from '@/lib/api'

interface AssessmentFormState {
  response: ServerResponse | null
  isSubmitting: boolean
}

const DEFAULT_VALUES: AssessmentFormValues = {
  certificationId: '',
  title: '',
  summaryMarkdown: '',
  difficulty: 'intermediate',
  questionCount: 20,
  passingScore: 70,
  timeLimitMinutes: 90,
  slideCount: 12,
  includeAvatar: false,
  domainDistribution: [DEFAULT_DOMAIN_ENTRY],
  notesMarkdown: '',
}

function toServerResponse(result: AssessmentWorkflowResponse): ServerResponse {
  return {
    ok: true,
    message: 'Assessment workflow submitted successfully',
    workflow_id: result.id,
    status: result.status,
    resume_token: result.resume_token,
    progress: result.progress,
    parameters: result.parameters,
    created_at: result.created_at,
    updated_at: result.updated_at,
  }
}

export function AssessmentForm() {
  const [certifications, setCertifications] = useState<CertificationProfile[]>([])
  const [certLoading, setCertLoading] = useState(true)
  const [certError, setCertError] = useState<string | null>(null)
  const [{ response, isSubmitting }, setFormState] = useState<AssessmentFormState>({
    response: null,
    isSubmitting: false,
  })

  const form = useForm<AssessmentFormValues>({
    resolver: zodResolver(AssessmentFormSchema),
    defaultValues: DEFAULT_VALUES,
    mode: 'onChange',
  })

  const {
    control,
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors, isValid },
  } = form

  const { fields, append, remove, replace } = useFieldArray({
    control,
    name: 'domainDistribution',
  })

  useEffect(() => {
    form.register('difficulty')
    form.register('includeAvatar')
  }, [form])

  const certificationId = watch('certificationId')
  const summaryMarkdown = watch('summaryMarkdown')
  const questionCount = watch('questionCount')
  const domainDistribution = watch('domainDistribution')

  const selectedCertification = useMemo(
    () => certifications.find((cert) => cert.id === certificationId),
    [certifications, certificationId]
  )

  const distributionTotal = domainDistribution.reduce((sum, entry) => sum + (Number(entry.questionCount) || 0), 0)
  const distributionDelta = questionCount - distributionTotal

  useEffect(() => {
    let isActive = true

    async function loadCertifications() {
      setCertLoading(true)
      setCertError(null)
      try {
        const profiles = await fetchCertificationProfiles()
        if (!isActive) return
        setCertifications(profiles)

        if (profiles.length > 0) {
          const initialId = certificationId || profiles[0].id
          setValue('certificationId', initialId, { shouldValidate: true })
          autofillDomains(profiles.find((p) => p.id === initialId) ?? profiles[0], questionCount, replace)
        }
      } catch (error) {
        if (!isActive) return
        console.error('Failed to load certification profiles', error)
        setCertError(error instanceof ApiError ? error.message : 'Unable to load certification profiles')
        toast.error('Failed to load certification profiles. Try again later.')
      } finally {
        if (isActive) {
          setCertLoading(false)
        }
      }
    }

    loadCertifications()

    return () => {
      isActive = false
    }
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const onSubmit = async (values: AssessmentFormValues) => {
    setFormState((prev) => ({ ...prev, isSubmitting: true, response: null }))
    try {
      const result = await requestAssessmentWorkflow(values)
      setFormState({ isSubmitting: false, response: toServerResponse(result) })
      toast.success('Assessment workflow submitted')
    } catch (error) {
      console.error('Assessment submission failed', error)
      if (error instanceof ApiError) {
        toast.error(error.message)
        setFormState({
          isSubmitting: false,
          response: {
            ok: false,
            error: error.message,
            status: error.status,
            details: error.response,
          },
        })
      } else if (error instanceof Error) {
        toast.error(error.message)
        setFormState({
          isSubmitting: false,
          response: {
            ok: false,
            error: error.message,
          },
        })
      } else {
        toast.error('Unexpected error while submitting assessment')
        setFormState({
          isSubmitting: false,
          response: {
            ok: false,
            error: 'Unexpected error while submitting assessment',
          },
        })
      }
    }
  }

  const handleAddDomain = () => {
    append({ domain: '', questionCount: 0 })
  }

  const handleRemoveDomain = (index: number) => {
    if (fields.length === 1) {
      toast.warning('At least one domain is required')
      return
    }
    remove(index)
  }

  const handleAutofillDomains = () => {
    if (!selectedCertification) {
      toast.error('Select a certification to autofill domains')
      return
    }
    autofillDomains(selectedCertification, questionCount, replace)
    toast.success('Domain distribution updated from certification profile')
  }

  return (
    <Card>
      <CardHeader>
        <div className="flex items-start justify-between gap-4">
          <div>
            <CardTitle className="flex items-center gap-2 text-xl">
              <Sparkles className="h-5 w-5 text-primary" />
              Launch Assessment Workflow
            </CardTitle>
            <CardDescription>
              Configure certification context, question mix, and supporting notes to kick off the PresGen-Assess workflow.
            </CardDescription>
          </div>
          <Badge variant="secondary">Week 1</Badge>
        </div>
      </CardHeader>
      <CardContent className="space-y-8">
        <form onSubmit={handleSubmit(onSubmit)} className="space-y-8">
          <section className="grid gap-6 md:grid-cols-2">
            <div className="space-y-2">
              <Label htmlFor="certificationId">Certification Profile *</Label>
              <Select
                value={certificationId}
                onValueChange={(value) => {
                  setValue('certificationId', value, { shouldValidate: true })
                  const profile = certifications.find((cert) => cert.id === value)
                  if (profile) {
                    autofillDomains(profile, questionCount, replace)
                  }
                }}
                disabled={certLoading || certifications.length === 0}
              >
                <SelectTrigger id="certificationId">
                  <SelectValue placeholder={certLoading ? 'Loading profiles…' : 'Select certification'} />
                </SelectTrigger>
                <SelectContent>
                  {certifications.map((cert) => (
                    <SelectItem key={cert.id} value={cert.id}>
                      {cert.name} · {cert.version}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {certError && <p className="text-sm text-destructive">{certError}</p>}
              {errors.certificationId && (
                <p className="text-sm text-destructive">{errors.certificationId.message}</p>
              )}
            </div>

            <div className="grid gap-2">
              <Label htmlFor="difficulty">Difficulty *</Label>
              <Select
                defaultValue={DEFAULT_VALUES.difficulty}
                onValueChange={(value) => setValue('difficulty', value as AssessmentFormValues['difficulty'], { shouldValidate: true })}
                value={watch('difficulty')}
              >
                <SelectTrigger id="difficulty">
                  <SelectValue placeholder="Select difficulty" />
                </SelectTrigger>
                <SelectContent>
                  {AssessmentDifficultyOptions.map((option) => (
                    <SelectItem key={option.value} value={option.value}>
                      {option.label}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
              {errors.difficulty && (
                <p className="text-sm text-destructive">{errors.difficulty.message}</p>
              )}
            </div>
          </section>

          <section className="grid gap-6">
            <div className="grid gap-2">
              <Label htmlFor="title">Assessment Title *</Label>
              <Input id="title" placeholder="Cloud Architecture Readiness Diagnostic" {...register('title')} />
              {errors.title && (
                <p className="text-sm text-destructive">{errors.title.message}</p>
              )}
            </div>

            <div className="grid md:grid-cols-2 gap-6">
              <div className="space-y-2">
                <Label htmlFor="questionCount">Question Count *</Label>
                <Input
                  id="questionCount"
                  type="number"
                  min={5}
                  max={50}
                  step={1}
                  {...register('questionCount', { valueAsNumber: true })}
                />
                {errors.questionCount && (
                  <p className="text-sm text-destructive">{errors.questionCount.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="passingScore">Passing Score (%) *</Label>
                <Input
                  id="passingScore"
                  type="number"
                  min={0}
                  max={100}
                  step={1}
                  {...register('passingScore', { valueAsNumber: true })}
                />
                {errors.passingScore && (
                  <p className="text-sm text-destructive">{errors.passingScore.message}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="timeLimitMinutes">Time Limit (minutes)</Label>
                <Input
                  id="timeLimitMinutes"
                  type="number"
                  min={10}
                  max={240}
                  step={5}
                  {...register('timeLimitMinutes')}
                />
                {errors.timeLimitMinutes && (
                  <p className="text-sm text-destructive">{errors.timeLimitMinutes.message as string}</p>
                )}
              </div>

              <div className="space-y-2">
                <Label htmlFor="slideCount">Slide Count *</Label>
                <Input
                  id="slideCount"
                  type="number"
                  min={5}
                  max={40}
                  step={1}
                  {...register('slideCount', { valueAsNumber: true })}
                />
                {errors.slideCount && (
                  <p className="text-sm text-destructive">{errors.slideCount.message}</p>
                )}
              </div>
            </div>
          </section>

          <section className="grid gap-4">
            <div className="flex items-center justify-between">
              <div>
                <h3 className="text-sm font-medium">Domain Distribution *</h3>
                <p className="text-xs text-muted-foreground">Ensure the sum matches the question count ({questionCount}).</p>
              </div>
              <div className="flex items-center gap-2">
                <Button type="button" variant="outline" size="sm" onClick={handleAutofillDomains}>
                  <RefreshCw className="mr-1 h-3 w-3" /> Autocomplete
                </Button>
                <Button type="button" variant="outline" size="sm" onClick={handleAddDomain}>
                  <Plus className="mr-1 h-3 w-3" /> Add Domain
                </Button>
              </div>
            </div>

            <div className="space-y-3">
              {fields.map((field, index) => (
                <div key={field.id} className="grid gap-3 rounded-lg border p-3 md:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_auto]">
                  <div className="space-y-2">
                    <Label htmlFor={`domain-${index}`}>Domain</Label>
                    <Input
                      id={`domain-${index}`}
                      placeholder="e.g., Design Resilient Architectures"
                      {...register(`domainDistribution.${index}.domain` as const)}
                    />
                    {errors.domainDistribution?.[index]?.domain && (
                      <p className="text-xs text-destructive">
                        {errors.domainDistribution[index]?.domain?.message}
                      </p>
                    )}
                  </div>

                  <div className="space-y-2">
                    <Label htmlFor={`domain-count-${index}`}>Questions</Label>
                    <Input
                      id={`domain-count-${index}`}
                      type="number"
                      min={0}
                      max={100}
                      step={1}
                      {...register(`domainDistribution.${index}.questionCount` as const, { valueAsNumber: true })}
                    />
                    {errors.domainDistribution?.[index]?.questionCount && (
                      <p className="text-xs text-destructive">
                        {errors.domainDistribution[index]?.questionCount?.message}
                      </p>
                    )}
                  </div>

                  <div className="flex items-end justify-end">
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => handleRemoveDomain(index)}
                      aria-label="Remove domain"
                    >
                      <Trash2 className="h-4 w-4" />
                    </Button>
                  </div>
                </div>
              ))}

              {errors.domainDistribution && !Array.isArray(errors.domainDistribution) && (
                <p className="text-sm text-destructive">{errors.domainDistribution.message as string}</p>
              )}

              {distributionDelta !== 0 && (
                <p className="text-sm text-amber-600 dark:text-amber-400">
                  Domain totals differ by {distributionDelta > 0 ? '+' : ''}{distributionDelta}. Adjust counts to reach {questionCount} questions.
                </p>
              )}
            </div>
          </section>

          <section className="grid gap-4">
            <div className="space-y-2">
              <Label htmlFor="summaryMarkdown">Assessment Context (Markdown) *</Label>
              <Textarea
                id="summaryMarkdown"
                minLength={30}
                className="min-h-32"
                placeholder="Outline learner background, focus areas, and any scenario-specific notes..."
                {...register('summaryMarkdown')}
              />
              {errors.summaryMarkdown && (
                <p className="text-sm text-destructive">{errors.summaryMarkdown.message}</p>
              )}
            </div>

            {summaryMarkdown.trim().length > 0 && (
              <div className="rounded-lg border bg-muted/50 p-3">
                <MarkdownPreview content={summaryMarkdown} />
              </div>
            )}

            <div className="space-y-2">
              <Label htmlFor="notesMarkdown">Internal Notes (optional)</Label>
              <Textarea
                id="notesMarkdown"
                className="min-h-24"
                placeholder="Add any internal guidance for reviewers or SMEs..."
                {...register('notesMarkdown')}
              />
              {errors.notesMarkdown && (
                <p className="text-sm text-destructive">{errors.notesMarkdown.message}</p>
              )}
            </div>
          </section>

          <section className="flex items-center justify-between rounded-lg border p-4">
            <div className="space-y-1">
              <Label className="text-base">Include Avatar Narration</Label>
              <p className="text-sm text-muted-foreground">
                Toggle on to queue PresGen-Avatar narration once slides are generated.
              </p>
            </div>
            <Switch
              checked={watch('includeAvatar')}
              onCheckedChange={(checked) => setValue('includeAvatar', checked, { shouldValidate: true })}
            />
          </section>

          <div className="flex items-center gap-3">
            <Button type="submit" disabled={isSubmitting || !isValid}>
              {isSubmitting && <Loader2 className="mr-2 h-4 w-4 animate-spin" />}
              Submit Assessment Request
            </Button>
            {!isValid && (
              <p className="text-sm text-muted-foreground">Complete required fields to enable submission.</p>
            )}
          </div>
        </form>

        <ServerResponseCard response={response} title="Assessment Workflow" />
      </CardContent>
    </Card>
  )
}

function autofillDomains(
  profile: CertificationProfile,
  questionCount: number,
  replaceFn: (data: DomainDistributionEntry[]) => void,
) {
  if (!profile.exam_domains || profile.exam_domains.length === 0) {
    replaceFn([{ ...DEFAULT_DOMAIN_ENTRY, questionCount }])
    return
  }

  const totalWeight = profile.exam_domains.reduce((sum, domain) => sum + domain.weight_percentage, 0)
  let remaining = questionCount

  const entries = profile.exam_domains.map((domain, index) => {
    if (index === profile.exam_domains.length - 1) {
      return {
        domain: domain.name,
        questionCount: Math.max(0, remaining),
      }
    }

    const weighted = Math.round((questionCount * domain.weight_percentage) / (totalWeight || 100))
    remaining -= weighted

    return {
      domain: domain.name,
      questionCount: Math.max(0, weighted),
    }
  })

  if (remaining !== 0 && entries.length > 0) {
    entries[entries.length - 1].questionCount = Math.max(0, entries[entries.length - 1].questionCount + remaining)
  }

  replaceFn(entries)
}
