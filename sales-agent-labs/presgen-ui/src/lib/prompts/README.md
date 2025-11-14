# Custom Prompt System Architecture

## Overview
The PresGen-Assess system uses a sophisticated dual-layer prompt architecture designed to provide both system-wide defaults and certification-specific customizations for optimal learning outcomes.

## Prompt System Architecture

### Two-Layer Prompt System

#### Layer 1: Global Default Prompts (Knowledge Base Tab)
**Location**: `/src/lib/prompts/` directory
**Purpose**: System-wide default templates that provide comprehensive frameworks for all certifications
**Scope**: Universal, certification-agnostic best practices

These prompts serve as:
- **Master Templates**: Comprehensive frameworks covering all aspects of assessment, presentation, and gap analysis
- **Fallback System**: Used when certification-specific prompts are not defined
- **Quality Standards**: Establish baseline requirements and methodologies
- **Training Materials**: Help users understand prompt structure and possibilities

#### Layer 2: Certification-Specific Prompts (Profile Editor)
**Location**: Database fields within `certification_profiles` table
**Purpose**: Tailored prompts optimized for specific certification contexts
**Scope**: Highly targeted for particular exams, industries, and learning contexts

These prompts provide:
- **Contextual Optimization**: Certification-specific terminology, concepts, and requirements
- **Industry Focus**: Relevant scenarios, examples, and applications
- **Exam Alignment**: Direct mapping to specific exam objectives and question formats
- **Cultural Adaptation**: Appropriate for specific professional communities

## Detailed Comparison

### Knowledge Base Tab Prompts vs Certification Profile Prompts

| Aspect | Knowledge Base (Global) | Certification Profile (Specific) |
|--------|------------------------|-----------------------------------|
| **Scope** | Universal, all certifications | Single certification context |
| **Customization** | Template with placeholders | Fully customized content |
| **Usage** | Default/fallback behavior | Primary execution prompts |
| **Maintenance** | System administrators | Individual users/instructors |
| **Complexity** | Comprehensive frameworks | Focused implementations |
| **Examples** | Generic business scenarios | Certification-specific use cases |
| **Terminology** | Universal technical terms | Industry/vendor-specific language |
| **Updates** | System-wide updates | Per-certification updates |

### Prompt Hierarchy & Resolution

```
User Request → Assessment/Presentation/Gap Analysis
                    ↓
1. Check Certification Profile Custom Prompts
   - assessment_prompt (if exists)
   - presentation_prompt (if exists)
   - gap_analysis_prompt (if exists)
                    ↓
2. If custom prompt exists:
   → Use certification-specific prompt
                    ↓
3. If custom prompt is empty/null:
   → Fall back to global default prompt
                    ↓
4. Apply variable substitution:
   - {certification_name}
   - {student_level}
   - {domain_coverage_placeholder}
   - {knowledge_base_context}
```

## Prompt Enhancement Strategies

### Additional Concepts to Consider

#### Assessment Generation Enhancements
1. **Cognitive Load Theory Integration**
   - Intrinsic load: Core concept complexity
   - Extraneous load: Question presentation clarity
   - Germane load: Schema construction support

2. **Adaptive Assessment Features**
   - Dynamic difficulty adjustment
   - Prerequisite knowledge validation
   - Competency-based progression
   - Mastery learning integration

3. **Cultural & Accessibility Considerations**
   - Universal Design for Learning (UDL) principles
   - Multi-language support considerations
   - Cultural context adaptation
   - Learning disability accommodations

4. **Industry-Specific Elements**
   - Regulatory compliance requirements
   - Professional ethics scenarios
   - Current technology trends
   - Market dynamics integration

#### Presentation Creation Enhancements
1. **Neuroscience-Based Learning**
   - Spacing effect optimization
   - Interleaving practice integration
   - Retrieval practice scheduling
   - Elaborative interrogation techniques

2. **Engagement Psychology**
   - Intrinsic motivation activation
   - Flow state optimization
   - Social learning integration
   - Gamification elements

3. **Multi-Modal Learning Design**
   - Dual coding theory application
   - Sensory integration strategies
   - Attention management techniques
   - Cognitive overload prevention

4. **Professional Development Integration**
   - Career pathway alignment
   - Skill transferability emphasis
   - Industry networking opportunities
   - Continuous learning mindset

#### Gap Analysis Enhancements
1. **Advanced Learning Analytics**
   - Predictive performance modeling
   - Learning trajectory analysis
   - Competency network mapping
   - Time-to-mastery estimation

2. **Psychological Assessment Integration**
   - Growth mindset evaluation
   - Self-efficacy measurement
   - Attribution pattern analysis
   - Motivation factor assessment

3. **Social Learning Considerations**
   - Peer comparison analytics
   - Collaborative learning opportunities
   - Community engagement patterns
   - Mentorship potential identification

4. **Professional Context Integration**
   - Job role alignment analysis
   - Industry demand correlation
   - Career progression mapping
   - Skill gap prioritization

## Implementation Guidelines

### Creating Effective Custom Prompts

#### Assessment Generation Best Practices
1. **Domain-Specific Optimization**
   - Map questions directly to exam blueprints
   - Include vendor-specific terminology
   - Reference current industry standards
   - Address common implementation challenges

2. **Cognitive Complexity Calibration**
   - Balance across Bloom's taxonomy levels
   - Align with certification difficulty expectations
   - Include appropriate scenario complexity
   - Provide graduated challenge levels

#### Presentation Creation Best Practices
1. **Learning Objective Alignment**
   - Connect directly to certification competencies
   - Address practical application requirements
   - Include industry-relevant examples
   - Support transfer learning goals

2. **Engagement Strategy Optimization**
   - Incorporate certification community culture
   - Use industry-appropriate humor and references
   - Include motivational elements specific to career goals
   - Design for professional development outcomes

#### Gap Analysis Best Practices
1. **Multidimensional Assessment Design**
   - Include certification-specific competency models
   - Address industry skill requirements
   - Consider career progression needs
   - Integrate professional standards

2. **Personalization Framework Development**
   - Account for diverse professional backgrounds
   - Consider varying experience levels
   - Address specific learning constraints
   - Include cultural and linguistic considerations

## Variable System

### Available Template Variables
- `{certification_name}`: Full certification title
- `{certification_code}`: Exam code (e.g., "SAA-C03")
- `{student_level}`: Beginner/Intermediate/Advanced
- `{domain_coverage_placeholder}`: Exam domain weightings
- `{knowledge_base_context}`: Available learning resources
- `{learning_objectives}`: Specific competency targets
- `{time_constraints}`: Study timeline information
- `{industry_context}`: Professional application domain

### Dynamic Context Integration
The system automatically injects relevant context from:
- ChromaDB knowledge base content
- Uploaded certification materials
- Student performance history
- Assessment results and patterns
- Learning preference data

## Quality Assurance Framework

### Prompt Validation Criteria
1. **Pedagogical Soundness**: Based on learning science principles
2. **Industry Relevance**: Current and applicable to professional practice
3. **Certification Alignment**: Directly mapped to exam objectives
4. **Accessibility**: Inclusive of diverse learning needs
5. **Scalability**: Applicable across different student populations

### Continuous Improvement Process
1. **Performance Monitoring**: Track learning outcome effectiveness
2. **User Feedback Integration**: Incorporate instructor and student input
3. **Industry Updates**: Reflect changing professional requirements
4. **Research Integration**: Include latest educational technology findings

## Usage Examples

### Global Default Usage (Knowledge Base Tab)
```markdown
# When to use:
- Setting up system-wide standards
- Creating baseline templates
- Training new users on prompt structure
- Establishing quality benchmarks

# Example scenario:
- New certification added without custom prompts
- Fallback when specific prompts are incomplete
- System administrator training materials
```

### Certification-Specific Usage (Profile Editor)
```markdown
# When to use:
- Optimizing for specific exam requirements
- Addressing industry-unique terminology
- Incorporating vendor-specific features
- Tailoring to student population characteristics

# Example scenario:
- AWS certification with cloud-specific scenarios
- Cisco networking with vendor command syntax
- Project management with methodology-specific frameworks
```

This dual-layer architecture ensures both consistency and flexibility, enabling the system to provide high-quality educational experiences across diverse certification contexts while maintaining the ability to optimize for specific learning needs.