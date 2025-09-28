"""
Assessment Prompt Service

Manages certification-specific prompts and templates for AI question generation.
Provides domain expertise and context-aware prompt engineering.
"""

import logging
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from enum import Enum

from src.common.enhanced_logging import get_enhanced_logger

logger = get_enhanced_logger(__name__)


class CertificationType(Enum):
    """Supported certification types."""
    AWS_SOLUTIONS_ARCHITECT = "aws_solutions_architect"
    AWS_DEVELOPER = "aws_developer"
    AWS_SYSOPS = "aws_sysops"
    AZURE_ARCHITECT = "azure_architect"
    GCP_ARCHITECT = "gcp_architect"
    GENERIC = "generic"


class DifficultyLevel(Enum):
    """Question difficulty levels."""
    BEGINNER = "beginner"
    INTERMEDIATE = "intermediate"
    ADVANCED = "advanced"
    EXPERT = "expert"


@dataclass
class DomainPromptTemplate:
    """Template for domain-specific question generation prompts."""
    domain: str
    certification_type: CertificationType
    difficulty_level: DifficultyLevel
    prompt_template: str
    context_keywords: List[str]
    learning_objectives: List[str]
    common_scenarios: List[str]


class AssessmentPromptService:
    """Manages certification-specific assessment prompts and templates."""

    def __init__(self):
        self.prompt_templates = self._initialize_prompt_templates()
        self.domain_expertise = self._initialize_domain_expertise()
        logger.info("📝 Assessment Prompt Service initialized with %d templates",
                   len(self.prompt_templates))

    async def get_certification_prompt(self, cert_type: str) -> str:
        """Retrieve specialized prompt for certification type."""

        cert_enum = self._parse_certification_type(cert_type)
        base_prompt = self._get_base_certification_prompt(cert_enum)

        logger.debug("Generated certification prompt for %s", cert_type)
        return base_prompt

    async def get_domain_prompt(
        self,
        domain: str,
        cert_type: str,
        difficulty: str
    ) -> str:
        """Get domain-specific prompt for question generation."""

        cert_enum = self._parse_certification_type(cert_type)
        diff_enum = self._parse_difficulty_level(difficulty)

        # Get domain-specific prompt template
        template_key = f"{cert_enum.value}_{domain.lower()}_{diff_enum.value}"

        if template_key in self.prompt_templates:
            template = self.prompt_templates[template_key]
            return self._build_domain_prompt(template)

        # Fallback to generic domain prompt
        return self._get_generic_domain_prompt(domain, difficulty)

    async def generate_domain_questions(
        self,
        domain: str,
        resources: List[str],
        count: int,
        difficulty: str,
        cert_type: str = "aws_solutions_architect"
    ) -> List[Dict[str, Any]]:
        """Generate domain-specific questions from resources."""

        logger.info("Generating %d questions for domain %s at %s level",
                   count, domain, difficulty)

        # Get domain expertise and context
        domain_context = self.domain_expertise.get(domain, {})

        # This would integrate with AI/LLM service for actual generation
        # For Sprint 4, we'll return contextually aware structured data

        questions = []
        for i in range(count):
            question_data = await self._generate_contextual_question(
                domain=domain,
                difficulty=difficulty,
                cert_type=cert_type,
                context=domain_context,
                question_number=i + 1
            )
            questions.append(question_data)

        return questions

    def _initialize_prompt_templates(self) -> Dict[str, DomainPromptTemplate]:
        """Initialize prompt templates for different certification domains."""

        templates = {}

        # AWS Solutions Architect - Security Domain
        templates["aws_solutions_architect_security_intermediate"] = DomainPromptTemplate(
            domain="Security",
            certification_type=CertificationType.AWS_SOLUTIONS_ARCHITECT,
            difficulty_level=DifficultyLevel.INTERMEDIATE,
            prompt_template="""
            Generate a multiple-choice question about AWS security for Solutions Architect level.
            Focus on: {focus_areas}
            Scenario: {scenario_context}

            Requirements:
            - Question should test practical application of security concepts
            - Include real-world scenario with business context
            - Options should be technically accurate and plausible
            - Correct answer should demonstrate security best practices
            - Include detailed explanation with AWS service references
            """,
            context_keywords=["IAM", "VPC Security", "Encryption", "Compliance", "KMS", "CloudTrail"],
            learning_objectives=[
                "Design secure access to AWS resources",
                "Design secure application tiers",
                "Select appropriate data security options"
            ],
            common_scenarios=[
                "Multi-tier web application security",
                "Cross-account access patterns",
                "Data encryption requirements",
                "Compliance and auditing needs"
            ]
        )

        # AWS Solutions Architect - Networking Domain
        templates["aws_solutions_architect_networking_intermediate"] = DomainPromptTemplate(
            domain="Networking",
            certification_type=CertificationType.AWS_SOLUTIONS_ARCHITECT,
            difficulty_level=DifficultyLevel.INTERMEDIATE,
            prompt_template="""
            Generate a multiple-choice question about AWS networking for Solutions Architect level.
            Focus on: {focus_areas}
            Scenario: {scenario_context}

            Requirements:
            - Question should test understanding of network design principles
            - Include scenarios with multiple AZs or regions
            - Options should reflect different networking approaches
            - Correct answer should demonstrate networking best practices
            - Include explanation of routing and connectivity concepts
            """,
            context_keywords=["VPC", "Subnets", "Route Tables", "NAT", "Load Balancers", "CloudFront"],
            learning_objectives=[
                "Design and implement VPC connectivity",
                "Design and implement elastic load balancing",
                "Design and implement DNS"
            ],
            common_scenarios=[
                "Hybrid connectivity requirements",
                "Multi-tier application networking",
                "Content delivery optimization",
                "Network segmentation and security"
            ]
        )

        # Add more templates for other domains and difficulty levels

        return templates

    def _initialize_domain_expertise(self) -> Dict[str, Dict[str, Any]]:
        """Initialize domain-specific expertise and context."""

        return {
            "Security": {
                "core_services": ["IAM", "KMS", "CloudTrail", "Config", "GuardDuty", "Security Hub"],
                "key_concepts": [
                    "Principle of least privilege",
                    "Defense in depth",
                    "Encryption at rest and in transit",
                    "Identity federation",
                    "Compliance frameworks"
                ],
                "common_patterns": [
                    "Cross-account access with assume roles",
                    "Service-to-service authentication",
                    "Data classification and protection",
                    "Incident response automation"
                ],
                "best_practices": [
                    "Use IAM roles instead of users for applications",
                    "Enable MFA for privileged accounts",
                    "Regular access reviews and rotation",
                    "Centralized logging and monitoring"
                ]
            },
            "Networking": {
                "core_services": ["VPC", "Route 53", "CloudFront", "Direct Connect", "Transit Gateway"],
                "key_concepts": [
                    "CIDR blocks and subnetting",
                    "Routing and route tables",
                    "Network ACLs vs Security Groups",
                    "Load balancing strategies",
                    "Content delivery networks"
                ],
                "common_patterns": [
                    "Multi-tier application architecture",
                    "Hybrid cloud connectivity",
                    "High availability across AZs",
                    "Global content distribution"
                ],
                "best_practices": [
                    "Use private subnets for application tiers",
                    "Implement proper network segmentation",
                    "Design for fault tolerance",
                    "Optimize for performance and cost"
                ]
            },
            "Storage": {
                "core_services": ["S3", "EBS", "EFS", "FSx", "Storage Gateway"],
                "key_concepts": [
                    "Storage classes and lifecycle policies",
                    "Performance optimization",
                    "Backup and disaster recovery",
                    "Data transfer optimization",
                    "Cost optimization strategies"
                ],
                "common_patterns": [
                    "Data lake architectures",
                    "Backup and archival strategies",
                    "Content distribution",
                    "Big data processing pipelines"
                ],
                "best_practices": [
                    "Choose appropriate storage class",
                    "Implement lifecycle policies",
                    "Enable versioning and backup",
                    "Monitor and optimize costs"
                ]
            },
            "Compute": {
                "core_services": ["EC2", "Lambda", "ECS", "EKS", "Auto Scaling"],
                "key_concepts": [
                    "Instance types and sizing",
                    "Auto scaling strategies",
                    "Serverless computing",
                    "Container orchestration",
                    "Cost optimization"
                ],
                "common_patterns": [
                    "Event-driven architectures",
                    "Microservices deployment",
                    "Batch processing workloads",
                    "High performance computing"
                ],
                "best_practices": [
                    "Right-size instances for workload",
                    "Use spot instances for fault-tolerant workloads",
                    "Implement proper monitoring",
                    "Design for elasticity"
                ]
            }
        }

    def _parse_certification_type(self, cert_type: str) -> CertificationType:
        """Parse certification type string to enum."""
        cert_mapping = {
            "aws": CertificationType.AWS_SOLUTIONS_ARCHITECT,
            "aws_solutions_architect": CertificationType.AWS_SOLUTIONS_ARCHITECT,
            "aws_developer": CertificationType.AWS_DEVELOPER,
            "aws_sysops": CertificationType.AWS_SYSOPS,
            "azure": CertificationType.AZURE_ARCHITECT,
            "gcp": CertificationType.GCP_ARCHITECT
        }

        return cert_mapping.get(cert_type.lower(), CertificationType.GENERIC)

    def _parse_difficulty_level(self, difficulty: str) -> DifficultyLevel:
        """Parse difficulty level string to enum."""
        diff_mapping = {
            "beginner": DifficultyLevel.BEGINNER,
            "intermediate": DifficultyLevel.INTERMEDIATE,
            "advanced": DifficultyLevel.ADVANCED,
            "expert": DifficultyLevel.EXPERT
        }

        return diff_mapping.get(difficulty.lower(), DifficultyLevel.INTERMEDIATE)

    def _get_base_certification_prompt(self, cert_type: CertificationType) -> str:
        """Get base prompt for certification type."""

        base_prompts = {
            CertificationType.AWS_SOLUTIONS_ARCHITECT: """
            You are an expert AWS Solutions Architect creating certification assessment questions.
            Focus on designing resilient, performant, secure, and cost-effective architectures.

            Key areas to emphasize:
            - Well-Architected Framework principles
            - Service selection and integration
            - Cost optimization strategies
            - Security best practices
            - Performance optimization
            - Operational excellence
            """,
            CertificationType.GENERIC: """
            You are creating technical assessment questions for cloud architecture.
            Focus on fundamental cloud computing concepts and best practices.
            """
        }

        return base_prompts.get(cert_type, base_prompts[CertificationType.GENERIC])

    def _build_domain_prompt(self, template: DomainPromptTemplate) -> str:
        """Build domain-specific prompt from template."""

        focus_areas = ", ".join(template.context_keywords)
        scenario_context = template.common_scenarios[0] if template.common_scenarios else "General scenario"

        return template.prompt_template.format(
            focus_areas=focus_areas,
            scenario_context=scenario_context
        )

    def _get_generic_domain_prompt(self, domain: str, difficulty: str) -> str:
        """Get generic domain prompt as fallback."""

        return f"""
        Generate a {difficulty} level multiple-choice question about {domain}.

        Requirements:
        - Question should test practical understanding
        - Include realistic scenario
        - Provide 4 plausible options
        - Include detailed explanation
        """

    async def _generate_contextual_question(
        self,
        domain: str,
        difficulty: str,
        cert_type: str,
        context: Dict[str, Any],
        question_number: int
    ) -> Dict[str, Any]:
        """Generate a contextual question using domain expertise."""

        # This is where we would integrate with AI/LLM service
        # For Sprint 4, return structured contextual data

        core_services = context.get("core_services", [])
        key_concepts = context.get("key_concepts", [])
        best_practices = context.get("best_practices", [])

        # Select focus areas for this question
        focus_service = core_services[question_number % len(core_services)] if core_services else domain
        focus_concept = key_concepts[question_number % len(key_concepts)] if key_concepts else "General concepts"

        return {
            "domain": domain,
            "difficulty": difficulty,
            "focus_service": focus_service,
            "focus_concept": focus_concept,
            "context_keywords": context.get("core_services", [])[:3],
            "learning_objective": f"Understand {focus_concept} in {domain}",
            "scenario_type": "practical_application"
        }