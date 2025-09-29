"use client";

import React, { useState, useEffect } from 'react';
import { Database, RotateCcw, Copy, Check, Wand2, Info, Upload } from 'lucide-react';
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

interface KnowledgeBasePromptConfig {
  document_ingestion_prompt?: string;
  context_retrieval_prompt?: string;
  semantic_search_prompt?: string;
  content_classification_prompt?: string;
}

interface KnowledgeBasePromptEditorProps {
  collectionName: string;
  certificationName?: string;
  initialPrompts?: KnowledgeBasePromptConfig;
  onPromptsChange: (prompts: KnowledgeBasePromptConfig) => void;
  className?: string;
}

const DEFAULT_KB_PROMPTS = {
  document_ingestion: `You are an expert document processor for professional certification knowledge bases.

INGESTION REQUIREMENTS:
- Accuracy: Preserve technical accuracy and specific terminology
- Structure: Maintain logical organization and hierarchical relationships
- Context: Capture domain-specific context and dependencies
- Standards: Follow certification body standards and best practices

PROCESSING GUIDELINES:
- Extract key concepts, definitions, and procedures
- Identify relationships between topics and subtopics
- Preserve code examples, diagrams, and reference materials
- Maintain version-specific information and updates

Process the following certification documents with focus on creating searchable, contextually rich knowledge segments.`,

  context_retrieval: `You are an expert context retrieval specialist for certification knowledge bases.

RETRIEVAL STRATEGY:
- Relevance: Match user queries to the most applicable knowledge segments
- Completeness: Include supporting context and prerequisites
- Accuracy: Ensure retrieved information is current and authoritative
- Specificity: Focus on certification-specific requirements and standards

CONTEXT ENRICHMENT:
- Include related concepts and dependencies
- Provide practical examples and use cases
- Reference official documentation and standards
- Highlight common pitfalls and best practices

Retrieve certification knowledge that directly addresses the user's question with comprehensive supporting context.`,

  semantic_search: `You are an expert semantic search engine for professional certification content.

SEARCH METHODOLOGY:
- Conceptual matching beyond keyword similarity
- Domain-specific understanding of terminology
- Hierarchical topic relationships
- Cross-domain knowledge connections

SEARCH OPTIMIZATION:
- Understanding of certification objectives and domains
- Recognition of practical vs. theoretical knowledge
- Awareness of skill progression and prerequisites
- Integration of hands-on experience requirements

Search the certification knowledge base for concepts, patterns, and solutions that semantically align with the user's intent and learning objectives.`,

  content_classification: `You are an expert content classifier for certification knowledge organization.

CLASSIFICATION FRAMEWORK:
- Domain categorization by certification objectives
- Skill level classification (foundational, intermediate, advanced)
- Content type identification (concept, procedure, example, reference)
- Learning objective alignment

ORGANIZATIONAL STRUCTURE:
- Primary domain assignment
- Secondary topic relationships
- Difficulty progression mapping
- Practical application categorization

Classify certification content to optimize knowledge discovery, learning progression, and exam preparation effectiveness.`
};

const PROMPT_DESCRIPTIONS = {
  document_ingestion: "Controls how documents are processed and ingested into the knowledge base",
  context_retrieval: "Defines how relevant context is retrieved when users ask questions",
  semantic_search: "Guides semantic search operations within the knowledge base",
  content_classification: "Manages how content is classified and organized in the knowledge base"
};

const VARIABLE_EXAMPLES = {
  document_ingestion: [
    '{certification_name}', '{collection_name}', '{document_type}',
    '{version}', '{domain_structure}', '{content_format}'
  ],
  context_retrieval: [
    '{user_query}', '{domain_context}', '{certification_objectives}',
    '{skill_level}', '{learning_path}', '{prerequisites}'
  ],
  semantic_search: [
    '{search_query}', '{knowledge_domains}', '{concept_relationships}',
    '{certification_scope}', '{practical_applications}', '{exam_topics}'
  ],
  content_classification: [
    '{content_type}', '{domain_categories}', '{skill_levels}',
    '{learning_objectives}', '{certification_structure}', '{topic_hierarchy}'
  ]
};

export default function KnowledgeBasePromptEditor({
  collectionName,
  certificationName,
  initialPrompts = {},
  onPromptsChange,
  className
}: KnowledgeBasePromptEditorProps) {
  const [prompts, setPrompts] = useState<KnowledgeBasePromptConfig>({
    document_ingestion_prompt: initialPrompts.document_ingestion_prompt || '',
    context_retrieval_prompt: initialPrompts.context_retrieval_prompt || '',
    semantic_search_prompt: initialPrompts.semantic_search_prompt || '',
    content_classification_prompt: initialPrompts.content_classification_prompt || ''
  });

  const [activeTab, setActiveTab] = useState('document_ingestion');
  const [copiedStates, setCopiedStates] = useState<Record<string, boolean>>({});
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    const currentPrompts = {
      document_ingestion_prompt: prompts.document_ingestion_prompt,
      context_retrieval_prompt: prompts.context_retrieval_prompt,
      semantic_search_prompt: prompts.semantic_search_prompt,
      content_classification_prompt: prompts.content_classification_prompt
    };

    const initialValues = {
      document_ingestion_prompt: initialPrompts.document_ingestion_prompt || '',
      context_retrieval_prompt: initialPrompts.context_retrieval_prompt || '',
      semantic_search_prompt: initialPrompts.semantic_search_prompt || '',
      content_classification_prompt: initialPrompts.content_classification_prompt || ''
    };

    const changed = JSON.stringify(currentPrompts) !== JSON.stringify(initialValues);
    setHasChanges(changed);

    console.log('🗂️ KB_PROMPT_DEBUG: Knowledge base prompt state changed:', {
      collectionName,
      certificationName,
      changed,
      currentPrompts: {
        ingestion_length: currentPrompts.document_ingestion_prompt?.length || 0,
        retrieval_length: currentPrompts.context_retrieval_prompt?.length || 0,
        search_length: currentPrompts.semantic_search_prompt?.length || 0,
        classification_length: currentPrompts.content_classification_prompt?.length || 0
      },
      source: 'KnowledgeBasePromptEditor'
    });

    if (changed) {
      console.log('🗂️ KB_PROMPT_DEBUG: Triggering onPromptsChange callback');
      onPromptsChange(currentPrompts);
    }
  }, [prompts, initialPrompts, onPromptsChange, collectionName, certificationName]);

  const handlePromptChange = (promptType: keyof KnowledgeBasePromptConfig, value: string) => {
    setPrompts(prev => ({
      ...prev,
      [promptType]: value
    }));
  };

  const resetToDefault = (promptType: 'document_ingestion' | 'context_retrieval' | 'semantic_search' | 'content_classification') => {
    const defaultPrompt = DEFAULT_KB_PROMPTS[promptType];
    const promptKey = `${promptType}_prompt` as keyof KnowledgeBasePromptConfig;

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
    promptType: 'document_ingestion' | 'context_retrieval' | 'semantic_search' | 'content_classification',
    title: string,
    description: string
  ) => {
    const promptKey = `${promptType}_prompt` as keyof KnowledgeBasePromptConfig;
    const promptValue = prompts[promptKey] || '';
    const defaultPrompt = DEFAULT_KB_PROMPTS[promptType];
    const isUsingDefault = promptValue === defaultPrompt;
    const isEmpty = promptValue.trim().length === 0;

    return (
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Database className="w-5 h-5" />
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
              placeholder={`Enter your custom ${promptType.replace('_', ' ')} prompt or use the default...`}
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

          {/* Collection Context */}
          <div className="space-y-2">
            <Label className="text-sm font-medium">Knowledge Base Context</Label>
            <div className="p-3 bg-gray-50 rounded-md text-xs">
              <div className="space-y-1">
                <div><strong>Collection:</strong> {collectionName}</div>
                {certificationName && (
                  <div><strong>Certification:</strong> {certificationName}</div>
                )}
                <div><strong>Purpose:</strong> Knowledge base operations (shared across all users)</div>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  };

  return (
    <div className={cn("space-y-6", className)}>
      <div className="flex items-center justify-between">
        <div>
          <h3 className="text-lg font-semibold flex items-center">
            <Database className="w-5 h-5 mr-2" />
            Knowledge Base Prompts Configuration
          </h3>
          <p className="text-sm text-gray-600">
            Configure how the knowledge base processes documents and retrieves information
          </p>
        </div>

        {hasChanges && (
          <Badge variant="outline" className="text-blue-700 border-blue-200">
            Unsaved Changes
          </Badge>
        )}
      </div>

      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="grid w-full grid-cols-4">
          <TabsTrigger value="document_ingestion" className="text-xs">
            Document Ingestion
          </TabsTrigger>
          <TabsTrigger value="context_retrieval" className="text-xs">
            Context Retrieval
          </TabsTrigger>
          <TabsTrigger value="semantic_search" className="text-xs">
            Semantic Search
          </TabsTrigger>
          <TabsTrigger value="content_classification" className="text-xs">
            Content Classification
          </TabsTrigger>
        </TabsList>

        <TabsContent value="document_ingestion" className="mt-6">
          {renderPromptEditor(
            'document_ingestion',
            'Document Ingestion Prompt',
            PROMPT_DESCRIPTIONS.document_ingestion
          )}
        </TabsContent>

        <TabsContent value="context_retrieval" className="mt-6">
          {renderPromptEditor(
            'context_retrieval',
            'Context Retrieval Prompt',
            PROMPT_DESCRIPTIONS.context_retrieval
          )}
        </TabsContent>

        <TabsContent value="semantic_search" className="mt-6">
          {renderPromptEditor(
            'semantic_search',
            'Semantic Search Prompt',
            PROMPT_DESCRIPTIONS.semantic_search
          )}
        </TabsContent>

        <TabsContent value="content_classification" className="mt-6">
          {renderPromptEditor(
            'content_classification',
            'Content Classification Prompt',
            PROMPT_DESCRIPTIONS.content_classification
          )}
        </TabsContent>
      </Tabs>

      {/* Help Section */}
      <Card className="bg-blue-50 border-blue-200">
        <CardContent className="p-4">
          <div className="flex items-start space-x-3">
            <Info className="w-5 h-5 text-blue-600 mt-0.5" />
            <div className="text-sm text-blue-900">
              <p className="font-medium mb-2">Knowledge Base Prompt Tips:</p>
              <ul className="space-y-1 list-disc list-inside">
                <li>These prompts affect all users of this certification's knowledge base</li>
                <li>Focus on how documents should be processed and knowledge retrieved</li>
                <li>Use variables to insert dynamic context during operations</li>
                <li>Test prompts with your actual certification content</li>
                <li>Changes will affect knowledge base behavior immediately</li>
              </ul>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}