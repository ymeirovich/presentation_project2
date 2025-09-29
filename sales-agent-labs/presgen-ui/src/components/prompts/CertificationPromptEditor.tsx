"use client";

import React, { useState, useEffect } from 'react';
import { User, RotateCcw, Copy, Check, Wand2, Info } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Label } from '@/components/ui/label';
import { Textarea } from '@/components/ui/textarea';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from '@/components/ui/tooltip';
import { cn } from '@/lib/utils';

interface CertificationPromptConfig {
  assessment_prompt?: string;
  presentation_prompt?: string;
  gap_analysis_prompt?: string;
}

interface CertificationPromptEditorProps {
  profileId?: string;
  certificationName?: string;
  initialPrompts?: CertificationPromptConfig;
  onPromptsChange: (prompts: CertificationPromptConfig) => void;
  certificationContext?: {
    name: string;
    domains: string[];
    industryContext: string;
  };
  className?: string;
}

const DEFAULT_CERT_PROMPTS = {
  assessment: `You are an expert assessment designer creating high-quality certification exam questions.

GENERATION REQUIREMENTS:
- Clarity: Questions must be unambiguous and clearly written
- Relevance: Directly aligned with certification objectives
- Difficulty Appropriateness: Matched to target competency level
- Discrimination: Effectively separates competent from non-competent candidates

COGNITIVE LEVEL DISTRIBUTION:
- Remember/Understand (30%): Foundational knowledge and comprehension
- Apply/Analyze (50%): Practical application and analysis
- Evaluate/Create (20%): Higher-order thinking and synthesis

Use the uploaded knowledge base content to ensure accuracy and generate {question_count} questions.`,

  presentation: `You are an expert instructional designer creating educational presentations for professional certification preparation.

PRESENTATION DESIGN PRINCIPLES:
- Learning Objectives Alignment: Clear, measurable objectives for each section
- Progressive Skill Building: From basic to advanced concepts
- Real-world Application: Practical implementation examples
- Engagement Strategies: Visual elements and interactive components

PERSONALIZATION FACTORS:
- Prioritize content based on identified learning gaps
- Adapt to different learning styles (Visual, Auditory, Kinesthetic)
- Progressive difficulty from current competency level

Create {slide_count} slides using the knowledge base materials and gap analysis insights.`,

  gap_analysis: `You are an expert educational assessment analyst specializing in multidimensional skill gap analysis for professional certifications.

ANALYSIS FRAMEWORK:

1. BLOOM'S TAXONOMY DEPTH ANALYSIS
   Evaluate cognitive performance across Remember/Understand/Apply/Analyze/Evaluate/Create levels

2. LEARNING STYLE & RETENTION INDICATORS
   Analyze Visual/Auditory/Kinesthetic/Multimodal learning preferences and retention patterns

3. METACOGNITIVE AWARENESS ASSESSMENT
   Evaluate self-assessment accuracy, uncertainty recognition, and strategy adaptation

4. TRANSFER LEARNING EVALUATION
   Assess near transfer, far transfer, and analogical reasoning capabilities

5. CERTIFICATION-SPECIFIC INSIGHTS
   Provide exam strategy readiness, industry context understanding, and professional competency alignment

OUTPUT REQUIREMENTS:
- Executive Summary with top 3 strengths and improvement priorities
- Detailed analysis for each dimension with specific evidence
- Actionable remediation recommendations with timelines
- Study strategy optimization tailored to learning profile

Provide comprehensive analysis with specific, actionable recommendations.`
};

const PROMPT_DESCRIPTIONS = {
  assessment: "Controls how assessment questions are generated for this specific certification profile",
  presentation: "Guides the creation of personalized learning presentations based on individual gap analysis",
  gap_analysis: "Defines how learning gaps are analyzed and personalized recommendations are provided"
};

const VARIABLE_EXAMPLES = {
  assessment: [
    '{certification_name}', '{domain_structure}', '{target_audience}',
    '{industry_context}', '{knowledge_base_context}', '{question_count}',
    '{user_profile}', '{difficulty_level}', '{focus_areas}'
  ],
  presentation: [
    '{gap_analysis_insights}', '{knowledge_base_context}', '{slide_count}',
    '{focus_areas}', '{certification_name}', '{audience_level}',
    '{learning_preferences}', '{weak_areas}', '{strong_areas}'
  ],
  gap_analysis: [
    '{certification_name}', '{exam_structure}', '{key_domains}',
    '{industry_context}', '{career_relevance}', '{assessment_results}',
    '{user_background}', '{learning_history}', '{performance_data}'
  ]
};

export default function CertificationPromptEditor({
  profileId,
  certificationName,
  initialPrompts = {},
  onPromptsChange,
  certificationContext,
  className
}: CertificationPromptEditorProps) {
  const [prompts, setPrompts] = useState<CertificationPromptConfig>({
    assessment_prompt: initialPrompts.assessment_prompt || '',
    presentation_prompt: initialPrompts.presentation_prompt || '',
    gap_analysis_prompt: initialPrompts.gap_analysis_prompt || ''
  });

  const [activeTab, setActiveTab] = useState('assessment');
  const [copiedStates, setCopiedStates] = useState<Record<string, boolean>>({});
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    const currentPrompts = {
      assessment_prompt: prompts.assessment_prompt,
      presentation_prompt: prompts.presentation_prompt,
      gap_analysis_prompt: prompts.gap_analysis_prompt
    };

    const initialValues = {
      assessment_prompt: initialPrompts.assessment_prompt || '',
      presentation_prompt: initialPrompts.presentation_prompt || '',
      gap_analysis_prompt: initialPrompts.gap_analysis_prompt || ''
    };

    const changed = JSON.stringify(currentPrompts) !== JSON.stringify(initialValues);
    setHasChanges(changed);

    console.log('🎯 CERT_PROMPT_DEBUG: Prompt state changed:', {
      profileId,
      certificationName,
      changed,
      currentPrompts: {
        assessment_length: currentPrompts.assessment_prompt?.length || 0,
        presentation_length: currentPrompts.presentation_prompt?.length || 0,
        gap_analysis_length: currentPrompts.gap_analysis_prompt?.length || 0
      },
      source: 'CertificationPromptEditor'
    });

    if (changed) {
      console.log('🎯 CERT_PROMPT_DEBUG: Triggering onPromptsChange callback');
      onPromptsChange(currentPrompts);
    }
  }, [prompts, initialPrompts, onPromptsChange, profileId, certificationName]);

  const handlePromptChange = (promptType: keyof CertificationPromptConfig, value: string) => {
    setPrompts(prev => ({
      ...prev,
      [promptType]: value
    }));
  };

  const resetToDefault = (promptType: 'assessment' | 'presentation' | 'gap_analysis') => {
    const defaultPrompt = DEFAULT_CERT_PROMPTS[promptType];
    const promptKey = `${promptType}_prompt` as keyof CertificationPromptConfig;

    setPrompts(prev => ({
      ...prev,
      [promptKey]: defaultPrompt
    }));
  };

  const copyToClipboard = async (text: string, key: string) => {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedStates(prev => ({ ...prev, [key]: true }));
      setTimeout(() => {
        setCopiedStates(prev => ({ ...prev, [key]: false }));
      }, 2000);
    } catch (err) {
      console.error('Failed to copy text:', err);
    }
  };

  const getCharacterCount = (text: string) => {
    return text.length;
  };

  const getWordCount = (text: string) => {
    return text.trim().split(/\s+/).filter(word => word.length > 0).length;
  };

  const renderPromptEditor = (
    promptType: 'assessment' | 'presentation' | 'gap_analysis',
    title: string,
    description: string
  ) => {
    const promptKey = `${promptType}_prompt` as keyof CertificationPromptConfig;
    const promptValue = prompts[promptKey] || '';
    const defaultPrompt = DEFAULT_CERT_PROMPTS[promptType];
    const isUsingDefault = promptValue === defaultPrompt;
    const isEmpty = promptValue.trim().length === 0;

    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <User className="w-5 h-5" />
              <CardTitle className="text-lg">{title}</CardTitle>
              {isUsingDefault && (
                <Badge variant="outline" className="text-green-700 border-green-200">
                  Default
                </Badge>
              )}
              {isEmpty && (
                <Badge variant="outline" className="text-yellow-700 border-yellow-200">
                  Empty
                </Badge>
              )}
            </div>

            <div className="flex items-center space-x-2">
              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => copyToClipboard(promptValue, promptType)}
                    >
                      {copiedStates[promptType] ? (
                        <Check className="w-4 h-4" />
                      ) : (
                        <Copy className="w-4 h-4" />
                      )}
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Copy prompt</TooltipContent>
                </Tooltip>
              </TooltipProvider>

              <TooltipProvider>
                <Tooltip>
                  <TooltipTrigger asChild>
                    <Button
                      type="button"
                      variant="outline"
                      size="sm"
                      onClick={() => resetToDefault(promptType)}
                    >
                      <RotateCcw className="w-4 h-4" />
                    </Button>
                  </TooltipTrigger>
                  <TooltipContent>Reset to default</TooltipContent>
                </Tooltip>
              </TooltipProvider>
            </div>
          </div>

          <p className="text-sm text-gray-600">{description}</p>
        </CardHeader>

        <CardContent className="space-y-4">
          <div>
            <Label htmlFor={`${promptType}-prompt`} className="text-sm font-medium">
              Prompt Content
            </Label>
            <Textarea
              id={`${promptType}-prompt`}
              value={promptValue}
              onChange={(e) => handlePromptChange(promptKey, e.target.value)}
              placeholder={`Enter your custom ${promptType} prompt or use the default...`}
              className="min-h-[200px] mt-2 font-mono text-sm"
            />

            <div className="flex items-center justify-between mt-2 text-xs text-gray-500">
              <span>
                {getWordCount(promptValue)} words • {getCharacterCount(promptValue)} characters
              </span>
            </div>
          </div>

          {/* Variable Examples */}
          <div className="space-y-2">
            <Label className="text-sm font-medium flex items-center">
              <Info className="w-4 h-4 mr-1" />
              Available Variables
            </Label>
            <div className="flex flex-wrap gap-1">
              {VARIABLE_EXAMPLES[promptType].map((variable) => (
                <Badge
                  key={variable}
                  variant="outline"
                  className="text-xs font-mono cursor-pointer"
                  onClick={() => {
                    const textarea = document.getElementById(`${promptType}-prompt`) as HTMLTextAreaElement;
                    if (textarea) {
                      const start = textarea.selectionStart;
                      const end = textarea.selectionEnd;
                      const currentValue = textarea.value;
                      const newValue = currentValue.substring(0, start) + variable + currentValue.substring(end);
                      handlePromptChange(promptKey, newValue);

                      // Restore cursor position
                      setTimeout(() => {
                        textarea.focus();
                        textarea.setSelectionRange(start + variable.length, start + variable.length);
                      }, 0);
                    }
                  }}
                >
                  {variable}
                </Badge>
              ))}
            </div>
            <p className="text-xs text-gray-500">
              Click on variables to insert them at cursor position
            </p>
          </div>

          {/* Certification Context Preview */}
          {certificationContext && (
            <div className="space-y-2">
              <Label className="text-sm font-medium">Certification Context</Label>
              <div className="p-3 bg-gray-50 rounded-md text-xs">
                <div className="space-y-1">
                  <div><strong>Name:</strong> {certificationContext.name}</div>
                  <div><strong>Domains:</strong> {certificationContext.domains.join(', ')}</div>
                  <div><strong>Industry:</strong> {certificationContext.industryContext}</div>
                  <div><strong>Scope:</strong> Individual certification profile (personalized)</div>
                </div>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    );
  };

  return (
    <div className={cn("space-y-6", className)}>
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold flex items-center">
            <User className="w-5 h-5 mr-2" />
            Certification Profile Prompts
          </h3>
          <p className="text-sm text-gray-600">
            Configure personalized prompts for assessment, presentation, and gap analysis
          </p>
        </div>

        {hasChanges && (
          <Badge variant="outline" className="text-blue-700 border-blue-200">
            Unsaved Changes
          </Badge>
        )}
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-3">
          <TabsTrigger value="assessment" className="text-sm">
            Assessment Generation
          </TabsTrigger>
          <TabsTrigger value="presentation" className="text-sm">
            Presentation Creation
          </TabsTrigger>
          <TabsTrigger value="gap_analysis" className="text-sm">
            Gap Analysis
          </TabsTrigger>
        </TabsList>

        <TabsContent value="assessment" className="mt-6">
          {renderPromptEditor(
            'assessment',
            'Assessment Generation Prompt',
            PROMPT_DESCRIPTIONS.assessment
          )}
        </TabsContent>

        <TabsContent value="presentation" className="mt-6">
          {renderPromptEditor(
            'presentation',
            'Presentation Creation Prompt',
            PROMPT_DESCRIPTIONS.presentation
          )}
        </TabsContent>

        <TabsContent value="gap_analysis" className="mt-6">
          {renderPromptEditor(
            'gap_analysis',
            'Gap Analysis Prompt',
            PROMPT_DESCRIPTIONS.gap_analysis
          )}
        </TabsContent>
      </Tabs>

      {/* Help Section */}
      <Card className="bg-green-50 border-green-200">
        <CardContent className="p-4">
          <div className="flex items-start space-x-3">
            <Info className="w-5 h-5 text-green-600 mt-0.5" />
            <div className="text-sm text-green-900">
              <p className="font-medium mb-2">Certification Profile Prompt Tips:</p>
              <ul className="space-y-1 list-disc list-inside">
                <li>These prompts are specific to this certification profile only</li>
                <li>Focus on personalized learning and assessment generation</li>
                <li>Use variables to insert dynamic user-specific content</li>
                <li>These prompts are separate from knowledge base operations</li>
                <li>Changes affect only this profile's generated content</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}