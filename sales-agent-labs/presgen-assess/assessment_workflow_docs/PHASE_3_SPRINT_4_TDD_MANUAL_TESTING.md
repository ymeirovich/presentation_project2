# Sprint 4: AI Question Generation - TDD Manual Testing Plan
*Test-Driven Development Manual Testing for AI-Powered Assessment Generation*

## Overview

**Sprint 4 Goal**: Replace sample questions with AI-generated, contextually relevant assessments
**Testing Objective**: Validate AI question generation meets quality, performance, and integration requirements
**Testing Duration**: 2-3 hours comprehensive manual testing
**Prerequisites**: Sprint 4 implementation completed, test environment operational

---

## Pre-Test Setup & Verification

### **Environment Setup**
```bash
# Verify services are running
curl -X GET "http://localhost:8081/api/v1/monitoring/health"
# Expected: overall_status: "healthy"
(.venv) yitzchak@MacBookPro presgen-assess % curl -X GET "http://localhost:8081/api/v1/monitoring/health"
{"overall_status":"unhealthy","timestamp":"2025-09-27T20:48:32.557726","checks":[{"service_name":"system","status":"healthy","details":{"cpu_percent":6.6,"memory_percent":79.0,"memory_total_gb":16.0,"memory_available_gb":3.3607330322265625,"disk_percent":2.2771461200063996,"disk_total_gb":460.4317207336426,"disk_free_gb":309.5489921569824,"load_average":[2.72216796875,2.2744140625,2.30859375],"platform":"macOS-15.6.1-arm64-arm-64bit-Mach-O","python_version":"3.13.5 (main, Jun 11 2025, 15:36:57) [Clang 17.0.0 (clang-1700.0.13.3)]"},"timestamp":"2025-09-27T20:48:32.224976","response_time_ms":1009.1969999999999},{"service_name":"database","status":"healthy","details":{"total_workflows":18,"recent_workflows_24h":18,"connection_test":"passed","query_test":"passed"},"timestamp":"2025-09-27T20:48:32.241590","response_time_ms":16.528000000000002},{"service_name":"google_forms","status":"healthy","details":{"authentication_status":"valid","api_status":"available","service_initialized":true},"timestamp":"2025-09-27T20:48:32.517069","response_time_ms":275.409},{"service_name":"presgen_integration","status":"degraded","details":{"presgen_core_available":false,"presgen_core_url":"http://localhost:8001","fallback_mode_functional":true,"statistics":{"total_presgen_jobs":0,"fallback_jobs":0,"presgen_core_jobs":0,"presgen_core_available":false,"presgen_core_url":"http://localhost:8001","fallback_rate":0}},"timestamp":"2025-09-27T20:48:32.547400","response_time_ms":30.308999999999997},{"service_name":"workflow_system","status":"unhealthy","details":{"workflow_status_counts":{"initiated":1,"assessment_generated":0,"deployed_to_google":0,"awaiting_completion":4,"sheet_url_provided":0,"results_analyzed":0,"training_plan_generated":0,"course_outlines_generated":0,"presentations_generated":0,"avatar_videos_generated":0,"completed":0,"error":2},"stuck_workflows":0,"recent_error_count":2,"error_rate_percent":28.57142857142857,"total_workflows":7},"timestamp":"2025-09-27T20:48:32.557142","response_time_ms":9.727},{"service_name":"application","status":"healthy","details":{"log_files":{"log_count":11,"total_size_mb":0.2365245819091797,"writable":true,"status":"healthy"},"temp_directory":{"usage_percent":27.502457696293853,"total_gb":460.4317207336426,"free_gb":309.5489921569824,"status":"healthy"},"configuration":{"valid":true,"missing_settings":[],"settings_checked":1,"status":"valid"},"startup_time":"2025-09-27T20:48:32.557709"},"timestamp":"2025-09-27T20:48:32.557714","response_time_ms":0.527}],"summary":{"total_checks":6,"healthy_count":4,"degraded_count":1,"unhealthy_count":1,"health_percentage":66.66666666666666,"average_response_time_ms":223.61616666666666}}%  

# Check AI services availability
curl -X GET "http://localhost:8081/api/v1/assessment-engine/health"
# Expected: assessment engine and knowledge base healthy
(.venv) yitzchak@MacBookPro presgen-assess % curl -X GET "http://localhost:8081/api/v1/engine/health"
{"status":"healthy","engine_ready":true,"llm_service_connected":true,"knowledge_base_accessible":true,"timestamp":"2024-01-01T00:00:00Z"}%  

(.venv) yitzchak@MacBookPro presgen-assess % curl -X GET "http://localhost:8081/api/v1/ai-question-generator/health"
{"status":"healthy","service":"ai_question_generator","timestamp":"2025-09-27T20:00:00Z","capabilities":["contextual_question_generation","quality_validation","fallback_mechanism","domain_distribution"],"database_required":true,"dependencies":["assessment_engine","knowledge_base","llm_service"]}%                        
(.venv) yitzchak@MacBookPro presgen-assess % 

# Verify test certification profile exists
curl -X GET "http://localhost:8081/api/v1/certification-profiles/455dae60-065c-4038-b3df-6d769b955dbb"
# Expected: Valid certification profile with exam resources

(.venv) yitzchak@MacBookPro presgen-assess % curl -X GET "http://localhost:8081/api/v1/certifications/455dae60-065c-4038-b3df-6d769b955dbb"
{"name":"AWS Machine Learning Specialty","version":"MLS-C01","provider":"AWS","description":"AWS Certified Machine Learning - Specialty validates expertise in building, training, tuning, and deploying machine learning models on AWS.","exam_code":"MLS-C01","passing_score":72,"exam_duration_minutes":180,"question_count":65,"exam_domains":[{"name":"Data Engineering","weight_percentage":20,"topics":[]},{"name":"Exploratory Data Analysis","weight_percentage":24,"topics":[]},{"name":"Modeling","weight_percentage":36,"topics":[]},{"name":"Machine Learning Implementation and Operations","weight_percentage":20,"topics":[]}],"prerequisites":["AWS experience","Machine learning knowledge"],"recommended_experience":"1-2 years of hands-on experience developing and running ML workloads on AWS","is_active":true,"assessment_prompt":"You are an expert assessment designer creating high-quality certification exam questions.\n\nGENERATION REQUIREMENTS:\n- Clarity: Questions must be unambiguous and clearly written\n- Relevance: Directly aligned with certification objectives\n- Difficulty Appropriateness: Matched to target competency level\n- Discrimination: Effectively separates competent from non-competent candidates\n\nCOGNITIVE LEVEL DISTRIBUTION:\n- Remember/Understand (30%): Foundational knowledge and comprehension\n- Apply/Analyze (50%): Practical application and analysis\n- Evaluate/Create (20%): Higher-order thinking and synthesis\n\nUse the uploaded knowledge base content to ensure accuracy and generate {question_count} questions.","presentation_prompt":"You are an expert instructional designer creating educational presentations for professional certification preparation.\n\nPRESENTATION DESIGN PRINCIPLES:\n- Learning Objectives Alignment: Clear, measurable objectives for each section\n- Progressive Skill Building: From basic to advanced concepts\n- Real-world Application: Practical implementation examples\n- Engagement Strategies: Visual elements and interactive components\n\nPERSONALIZATION FACTORS:\n- Prioritize content based on identified learning gaps\n- Adapt to different learning styles (Visual, Auditory, Kinesthetic)\n- Progressive difficulty from current competency level\n\nCreate {slide_count} slides using the knowledge base materials and gap analysis insights.","gap_analysis_prompt":"You are an expert educational assessment analyst specializing in multidimensional skill gap analysis for professional certifications.\n\nANALYSIS FRAMEWORK:\n\n1. BLOOM'S TAXONOMY DEPTH ANALYSIS\n   Evaluate cognitive performance across Remember/Understand/Apply/Analyze/Evaluate/Create levels\n\n2. LEARNING STYLE & RETENTION INDICATORS\n   Analyze Visual/Auditory/Kinesthetic/Multimodal learning preferences and retention patterns\n\n3. METACOGNITIVE AWARENESS ASSESSMENT\n   Evaluate self-assessment accuracy, uncertainty recognition, and strategy adaptation\n\n4. TRANSFER LEARNING EVALUATION\n   Assess near transfer, far transfer, and analogical reasoning capabilities\n\n5. CERTIFICATION-SPECIFIC INSIGHTS\n   Provide exam strategy readiness, industry context understanding, and professional competency alignment\n\nOUTPUT REQUIREMENTS:\n- Executive Summary with top 3 strengths and improvement priorities\n- Detailed analysis for each dimension with specific evidence\n- Actionable remediation recommendations with timelines\n- Study strategy optimization tailored to learning profile\n\nProvide comprehensive analysis with specific, actionable recommendations.","id":"455dae60-065c-4038-b3df-6d769b955dbb","created_at":"2025-09-25T17:43:40","updated_at":"2025-09-26T18:57:33"}%  
```

### **Test Data Preparation**
- **Certification Profile**: AWS Solutions Architect (with exam guide resources)
- **User Profile**: "test_ai_user@example.com"
- **Domain Distribution**: {"Security": 6, "Networking": 8, "Storage": 6, "Compute": 4}
- **Difficulty Level**: "intermediate"
- **Question Count**: 24

---

## Test Suite 1: AI Question Generation Engine

### **Test 1.1: Basic AI Question Generation**
**Objective**: Verify AI question generator produces valid questions

**Test Steps**:
1. **Direct AI Service Test**:
   ```bash
   curl -X POST "http://localhost:8081/api/v1/ai-question-generator/generate" \
     -H "Content-Type: application/json" \
     -d '{
       "certification_profile_id": "455dae60-065c-4038-b3df-6d769b955dbb",
       "user_profile": "test_ai_user@example.com",
       "difficulty_level": "intermediate",
       "domain_distribution": {"Security": 6, "Networking": 8, "Storage": 6, "Compute": 4},
       "question_count": 24
     }'
   ```
(.venv) yitzchak@MacBookPro presgen-assess % curl -X POST "http://localhost:8081/api/v1/ai-question-generator/generate" \
     -H "Content-Type: application/json" \
     -d '{
       "certification_profile_id": "455dae60-065c-4038-b3df-6d769b955dbb",
       "user_profile": "test_ai_user@example.com",
       "difficulty_level": "intermediate",
       "domain_distribution": {"Security": 6, "Networking": 8, "Storage": 6, "Compute": 4},
       "question_count": 24
     }'
{"success":true,"assessment_data":{"questions":[{"id":"ai_security_1","question_text":"An organization wants to encrypt data at rest in their RDS MySQL database while maintaining the ability to perform automated backups. What is the most appropriate encryption solution?","question_type":"multiple_choice","options":["A) Use AWS KMS encryption with customer-managed keys","B) Implement application-level encryption before storing data","C) Use RDS encryption with AWS-managed keys","D) Enable file system encryption on the underlying EC2 instance"],"correct_answer":"A","domain":"Security","difficulty":"intermediate","explanation":"AWS KMS with customer-managed keys provides encryption at rest while maintaining compatibility with automated backups and point-in-time recovery features.","source_references":["RDS User Guide","AWS KMS Developer Guide"],"quality_score":9.125},{"id":"ai_security_2","question_text":"A company needs to ensure that only specific AWS services can access their S3 bucket containing sensitive customer data. Which approach provides the most secure and granular access control?","question_type":"multiple_choice","options":["A) Use bucket ACLs to grant access to specific AWS services","B) Create an IAM policy with condition keys to restrict access by AWS service","C) Use S3 bucket policies with Principal element specifying AWS services","D) Enable S3 Block Public Access and use pre-signed URLs"],"correct_answer":"B","domain":"Security","difficulty":"intermediate","explanation":"IAM policies with condition keys like aws:SourceService provide the most granular control over which AWS services can access resources. This approach follows the principle of least privilege.","source_references":["AWS IAM User Guide","S3 Security Best Practices"],"quality_score":9.125},{"id":"ai_security_3","question_text":"An organization wants to encrypt data at rest in their RDS MySQL database while maintaining the ability to perform automated backups. What is the most appropriate encryption solution?","question_type":"multiple_choice","options":["A) Use AWS KMS encryption with customer-managed keys","B) Implement application-level encryption before storing data","C) Use RDS encryption with AWS-managed keys","D) Enable file system encryption on the underlying EC2 instance"],"correct_answer":"A","domain":"Security","difficulty":"intermediate","explanation":"AWS KMS with customer-managed keys provides encryption at rest while maintaining compatibility with automated backups and point-in-time recovery features.","source_references":["RDS User Guide","AWS KMS Developer Guide"],"quality_score":9.125},{"id":"ai_security_4","question_text":"A company needs to ensure that only specific AWS services can access their S3 bucket containing sensitive customer data. Which approach provides the most secure and granular access control?","question_type":"multiple_choice","options":["A) Use bucket ACLs to grant access to specific AWS services","B) Create an IAM policy with condition keys to restrict access by AWS service","C) Use S3 bucket policies with Principal element specifying AWS services","D) Enable S3 Block Public Access and use pre-signed URLs"],"correct_answer":"B","domain":"Security","difficulty":"intermediate","explanation":"IAM policies with condition keys like aws:SourceService provide the most granular control over which AWS services can access resources. This approach follows the principle of least privilege.","source_references":["AWS IAM User Guide","S3 Security Best Practices"],"quality_score":9.125},{"id":"ai_security_5","question_text":"An organization wants to encrypt data at rest in their RDS MySQL database while maintaining the ability to perform automated backups. What is the most appropriate encryption solution?","question_type":"multiple_choice","options":["A) Use AWS KMS encryption with customer-managed keys","B) Implement application-level encryption before storing data","C) Use RDS encryption with AWS-managed keys","D) Enable file system encryption on the underlying EC2 instance"],"correct_answer":"A","domain":"Security","difficulty":"intermediate","explanation":"AWS KMS with customer-managed keys provides encryption at rest while maintaining compatibility with automated backups and point-in-time recovery features.","source_references":["RDS User Guide","AWS KMS Developer Guide"],"quality_score":9.125},{"id":"ai_security_6","question_text":"A company needs to ensure that only specific AWS services can access their S3 bucket containing sensitive customer data. Which approach provides the most secure and granular access control?","question_type":"multiple_choice","options":["A) Use bucket ACLs to grant access to specific AWS services","B) Create an IAM policy with condition keys to restrict access by AWS service","C) Use S3 bucket policies with Principal element specifying AWS services","D) Enable S3 Block Public Access and use pre-signed URLs"],"correct_answer":"B","domain":"Security","difficulty":"intermediate","explanation":"IAM policies with condition keys like aws:SourceService provide the most granular control over which AWS services can access resources. This approach follows the principle of least privilege.","source_references":["AWS IAM User Guide","S3 Security Best Practices"],"quality_score":9.125},{"id":"ai_networking_1","question_text":"A company has a VPC with CIDR 10.0.0.0/16 and wants to establish connectivity with their on-premises network (192.168.0.0/16) using VPN. What routing configuration is required?","question_type":"multiple_choice","options":["A) Add route 192.168.0.0/16 pointing to the VPN Gateway in all route tables","B) Enable route propagation from VPN Gateway to route tables","C) Configure static routes on the on-premises router only","D) Use the main route table and enable auto-propagation"],"correct_answer":"B","domain":"Networking","difficulty":"intermediate","explanation":"Route propagation automatically adds routes learned from VPN connections to route tables, ensuring proper connectivity without manual route management.","source_references":["VPN Documentation","Route Table Configuration Guide"],"quality_score":9.125},{"id":"ai_networking_2","question_text":"A web application running on EC2 instances in private subnets needs to access the internet for software updates while remaining secure. What is the most cost-effective solution?","question_type":"multiple_choice","options":["A) Deploy a NAT Gateway in each private subnet","B) Deploy a single NAT Gateway in a public subnet","C) Use a NAT Instance with auto-scaling","D) Create VPC endpoints for all required services"],"correct_answer":"B","domain":"Networking","difficulty":"intermediate","explanation":"A single NAT Gateway in a public subnet can serve multiple private subnets and is more cost-effective than multiple NAT Gateways while providing high availability.","source_references":["VPC User Guide","NAT Gateway Documentation"],"quality_score":9.125},{"id":"ai_networking_3","question_text":"A company has a VPC with CIDR 10.0.0.0/16 and wants to establish connectivity with their on-premises network (192.168.0.0/16) using VPN. What routing configuration is required?","question_type":"multiple_choice","options":["A) Add route 192.168.0.0/16 pointing to the VPN Gateway in all route tables","B) Enable route propagation from VPN Gateway to route tables","C) Configure static routes on the on-premises router only","D) Use the main route table and enable auto-propagation"],"correct_answer":"B","domain":"Networking","difficulty":"intermediate","explanation":"Route propagation automatically adds routes learned from VPN connections to route tables, ensuring proper connectivity without manual route management.","source_references":["VPN Documentation","Route Table Configuration Guide"],"quality_score":9.125},{"id":"ai_networking_4","question_text":"A web application running on EC2 instances in private subnets needs to access the internet for software updates while remaining secure. What is the most cost-effective solution?","question_type":"multiple_choice","options":["A) Deploy a NAT Gateway in each private subnet","B) Deploy a single NAT Gateway in a public subnet","C) Use a NAT Instance with auto-scaling","D) Create VPC endpoints for all required services"],"correct_answer":"B","domain":"Networking","difficulty":"intermediate","explanation":"A single NAT Gateway in a public subnet can serve multiple private subnets and is more cost-effective than multiple NAT Gateways while providing high availability.","source_references":["VPC User Guide","NAT Gateway Documentation"],"quality_score":9.125},{"id":"ai_networking_5","question_text":"A company has a VPC with CIDR 10.0.0.0/16 and wants to establish connectivity with their on-premises network (192.168.0.0/16) using VPN. What routing configuration is required?","question_type":"multiple_choice","options":["A) Add route 192.168.0.0/16 pointing to the VPN Gateway in all route tables","B) Enable route propagation from VPN Gateway to route tables","C) Configure static routes on the on-premises router only","D) Use the main route table and enable auto-propagation"],"correct_answer":"B","domain":"Networking","difficulty":"intermediate","explanation":"Route propagation automatically adds routes learned from VPN connections to route tables, ensuring proper connectivity without manual route management.","source_references":["VPN Documentation","Route Table Configuration Guide"],"quality_score":9.125},{"id":"ai_networking_6","question_text":"A web application running on EC2 instances in private subnets needs to access the internet for software updates while remaining secure. What is the most cost-effective solution?","question_type":"multiple_choice","options":["A) Deploy a NAT Gateway in each private subnet","B) Deploy a single NAT Gateway in a public subnet","C) Use a NAT Instance with auto-scaling","D) Create VPC endpoints for all required services"],"correct_answer":"B","domain":"Networking","difficulty":"intermediate","explanation":"A single NAT Gateway in a public subnet can serve multiple private subnets and is more cost-effective than multiple NAT Gateways while providing high availability.","source_references":["VPC User Guide","NAT Gateway Documentation"],"quality_score":9.125},{"id":"ai_networking_7","question_text":"A company has a VPC with CIDR 10.0.0.0/16 and wants to establish connectivity with their on-premises network (192.168.0.0/16) using VPN. What routing configuration is required?","question_type":"multiple_choice","options":["A) Add route 192.168.0.0/16 pointing to the VPN Gateway in all route tables","B) Enable route propagation from VPN Gateway to route tables","C) Configure static routes on the on-premises router only","D) Use the main route table and enable auto-propagation"],"correct_answer":"B","domain":"Networking","difficulty":"intermediate","explanation":"Route propagation automatically adds routes learned from VPN connections to route tables, ensuring proper connectivity without manual route management.","source_references":["VPN Documentation","Route Table Configuration Guide"],"quality_score":9.125},{"id":"ai_networking_8","question_text":"A web application running on EC2 instances in private subnets needs to access the internet for software updates while remaining secure. What is the most cost-effective solution?","question_type":"multiple_choice","options":["A) Deploy a NAT Gateway in each private subnet","B) Deploy a single NAT Gateway in a public subnet","C) Use a NAT Instance with auto-scaling","D) Create VPC endpoints for all required services"],"correct_answer":"B","domain":"Networking","difficulty":"intermediate","explanation":"A single NAT Gateway in a public subnet can serve multiple private subnets and is more cost-effective than multiple NAT Gateways while providing high availability.","source_references":["VPC User Guide","NAT Gateway Documentation"],"quality_score":9.125},{"id":"ai_storage_1","question_text":"An application requires a shared file system accessible from multiple EC2 instances across different AZs with POSIX compliance. Which storage solution meets these requirements?","question_type":"multiple_choice","options":["A) Amazon EBS with Multi-Attach enabled","B) Amazon EFS with General Purpose performance mode","C) Amazon S3 mounted using S3FS","D) Amazon FSx for Lustre"],"correct_answer":"B","domain":"Storage","difficulty":"intermediate","explanation":"Amazon EFS provides a shared, POSIX-compliant file system that can be accessed from multiple EC2 instances across different Availability Zones.","source_references":["EFS User Guide","EC2 Storage Options"],"quality_score":9.125},{"id":"ai_storage_2","question_text":"A media company needs to store video files with the following requirements: immediate access for 30 days, infrequent access for 6 months, and long-term archival. What S3 storage strategy minimizes costs?","question_type":"multiple_choice","options":["A) Store in S3 Standard and manually move files to different storage classes","B) Use S3 Intelligent-Tiering for automatic optimization","C) Configure S3 Lifecycle policies to transition between storage classes","D) Use S3 One Zone-IA for all files to reduce costs"],"correct_answer":"C","domain":"Storage","difficulty":"intermediate","explanation":"S3 Lifecycle policies automatically transition objects between storage classes based on age, optimizing costs without manual intervention: Standard → IA → Glacier → Deep Archive.","source_references":["S3 User Guide","S3 Storage Classes Documentation"],"quality_score":9.125},{"id":"ai_storage_3","question_text":"An application requires a shared file system accessible from multiple EC2 instances across different AZs with POSIX compliance. Which storage solution meets these requirements?","question_type":"multiple_choice","options":["A) Amazon EBS with Multi-Attach enabled","B) Amazon EFS with General Purpose performance mode","C) Amazon S3 mounted using S3FS","D) Amazon FSx for Lustre"],"correct_answer":"B","domain":"Storage","difficulty":"intermediate","explanation":"Amazon EFS provides a shared, POSIX-compliant file system that can be accessed from multiple EC2 instances across different Availability Zones.","source_references":["EFS User Guide","EC2 Storage Options"],"quality_score":9.125},{"id":"ai_storage_4","question_text":"A media company needs to store video files with the following requirements: immediate access for 30 days, infrequent access for 6 months, and long-term archival. What S3 storage strategy minimizes costs?","question_type":"multiple_choice","options":["A) Store in S3 Standard and manually move files to different storage classes","B) Use S3 Intelligent-Tiering for automatic optimization","C) Configure S3 Lifecycle policies to transition between storage classes","D) Use S3 One Zone-IA for all files to reduce costs"],"correct_answer":"C","domain":"Storage","difficulty":"intermediate","explanation":"S3 Lifecycle policies automatically transition objects between storage classes based on age, optimizing costs without manual intervention: Standard → IA → Glacier → Deep Archive.","source_references":["S3 User Guide","S3 Storage Classes Documentation"],"quality_score":9.125},{"id":"ai_storage_5","question_text":"An application requires a shared file system accessible from multiple EC2 instances across different AZs with POSIX compliance. Which storage solution meets these requirements?","question_type":"multiple_choice","options":["A) Amazon EBS with Multi-Attach enabled","B) Amazon EFS with General Purpose performance mode","C) Amazon S3 mounted using S3FS","D) Amazon FSx for Lustre"],"correct_answer":"B","domain":"Storage","difficulty":"intermediate","explanation":"Amazon EFS provides a shared, POSIX-compliant file system that can be accessed from multiple EC2 instances across different Availability Zones.","source_references":["EFS User Guide","EC2 Storage Options"],"quality_score":9.125},{"id":"ai_storage_6","question_text":"A media company needs to store video files with the following requirements: immediate access for 30 days, infrequent access for 6 months, and long-term archival. What S3 storage strategy minimizes costs?","question_type":"multiple_choice","options":["A) Store in S3 Standard and manually move files to different storage classes","B) Use S3 Intelligent-Tiering for automatic optimization","C) Configure S3 Lifecycle policies to transition between storage classes","D) Use S3 One Zone-IA for all files to reduce costs"],"correct_answer":"C","domain":"Storage","difficulty":"intermediate","explanation":"S3 Lifecycle policies automatically transition objects between storage classes based on age, optimizing costs without manual intervention: Standard → IA → Glacier → Deep Archive.","source_references":["S3 User Guide","S3 Storage Classes Documentation"],"quality_score":9.125},{"id":"ai_compute_1","question_text":"A microservices application needs to handle variable traffic with automatic scaling and minimal operational overhead. Which compute service is most appropriate?","question_type":"multiple_choice","options":["A) EC2 Auto Scaling Groups with Application Load Balancer","B) AWS Lambda with API Gateway","C) ECS with Fargate and Application Load Balancer","D) Elastic Beanstalk with Auto Scaling"],"correct_answer":"C","domain":"Compute","difficulty":"intermediate","explanation":"ECS with Fargate provides serverless containers with automatic scaling and load balancing, ideal for microservices with minimal operational overhead.","source_references":["ECS User Guide","Fargate User Guide"],"quality_score":9.125},{"id":"ai_compute_2","question_text":"A batch processing job needs to run every night and requires significant compute resources for 2-3 hours. The job can tolerate interruptions. What is the most cost-effective EC2 pricing model?","question_type":"multiple_choice","options":["A) On-Demand instances with scheduled scaling","B) Reserved Instances with scheduled capacity","C) Spot Instances with Spot Fleet","D) Dedicated Hosts with capacity reservations"],"correct_answer":"C","domain":"Compute","difficulty":"intermediate","explanation":"Spot Instances can provide up to 90% cost savings for fault-tolerant workloads. Spot Fleet ensures capacity across multiple instance types and AZs.","source_references":["EC2 Spot Instances Guide","Spot Fleet User Guide"],"quality_score":9.125},{"id":"ai_compute_3","question_text":"A microservices application needs to handle variable traffic with automatic scaling and minimal operational overhead. Which compute service is most appropriate?","question_type":"multiple_choice","options":["A) EC2 Auto Scaling Groups with Application Load Balancer","B) AWS Lambda with API Gateway","C) ECS with Fargate and Application Load Balancer","D) Elastic Beanstalk with Auto Scaling"],"correct_answer":"C","domain":"Compute","difficulty":"intermediate","explanation":"ECS with Fargate provides serverless containers with automatic scaling and load balancing, ideal for microservices with minimal operational overhead.","source_references":["ECS User Guide","Fargate User Guide"],"quality_score":9.125},{"id":"ai_compute_4","question_text":"A batch processing job needs to run every night and requires significant compute resources for 2-3 hours. The job can tolerate interruptions. What is the most cost-effective EC2 pricing model?","question_type":"multiple_choice","options":["A) On-Demand instances with scheduled scaling","B) Reserved Instances with scheduled capacity","C) Spot Instances with Spot Fleet","D) Dedicated Hosts with capacity reservations"],"correct_answer":"C","domain":"Compute","difficulty":"intermediate","explanation":"Spot Instances can provide up to 90% cost savings for fault-tolerant workloads. Spot Fleet ensures capacity across multiple instance types and AZs.","source_references":["EC2 Spot Instances Guide","Spot Fleet User Guide"],"quality_score":9.125}],"metadata":{"generation_time_ms":0,"total_questions":24,"domain_distribution":{"Security":6,"Networking":8,"Storage":6,"Compute":4},"quality_scores":{"relevance":9.2,"accuracy":9.5,"difficulty_calibration":8.8,"overall":9.125},"certification_name":"AWS Solutions Architect Associate","difficulty_level":"intermediate","correlation_id":"ai_gen_455dae60-065c-4038-b3df-6d769b955dbb_20250927_210217"}},"message":"AI question generation completed successfully"}%  


2. **Expected Results**:
   ```json
   {
     "success": true,
     "assessment_data": {
       "questions": [
         {
           "id": "q1",
           "question_text": "[Context-specific AWS question about VPC networking]",
           "question_type": "multiple_choice",
           "options": ["A) [Technical option]", "B) [Technical option]", "C) [Technical option]", "D) [Technical option]"],
           "correct_answer": "B",
           "domain": "Networking",
           "difficulty": "intermediate",
           "explanation": "[Detailed explanation with AWS documentation references]",
           "source_references": ["AWS VPC User Guide", "AWS Well-Architected Framework"]
         }
       ],
       "metadata": {
         "generation_time_ms": 45000,
         "total_questions": 24,
         "domain_distribution": {"Security": 6, "Networking": 8, "Storage": 6, "Compute": 4},
         "quality_scores": {
           "relevance": 9.2,
           "accuracy": 9.5,
           "difficulty_calibration": 8.8
         }
       }
     }
   }
   ```

3. **Validation Criteria**:
   - [ ] Response time < 2 minutes (120,000ms)
   - [ ] 24 questions generated matching domain distribution
   - [ ] Questions contain AWS-specific technical content (not generic)
   - [ ] Quality scores > 8.0 for all metrics
   - [ ] Source references included for each question

### **Test 1.2: Question Quality Validation**
**Objective**: Verify generated questions meet quality standards

**Manual Quality Checks**:
1. **Content Relevance** (Sample 5 questions):
   - [ ] Questions directly relate to AWS certification objectives
   - [ ] Technical content is accurate and current
   - [ ] Options are plausible and technically sound
   - [ ] Correct answers are definitively correct

2. **Difficulty Calibration**:
   - [ ] Intermediate questions require applied knowledge (not memorization)
   - [ ] Questions involve scenario-based problem solving
   - [ ] Options require understanding of AWS service interactions

3. **Domain Distribution Accuracy**:
   ```bash
   # Verify actual distribution matches requested
   echo "Expected: Security=6, Networking=8, Storage=6, Compute=4"
   echo "Actual: [Count questions by domain in response]"
   ```

### **Test 1.3: Error Handling & Fallback**
**Objective**: Test AI generation failure scenarios

**Test Steps**:
1. **Invalid Certification Profile**:
   ```bash
   curl -X POST "http://localhost:8081/api/v1/ai-question-generator/generate" \
     -H "Content-Type: application/json" \
     -d '{
       "certification_profile_id": "00000000-0000-0000-0000-000000000000",
       "user_profile": "test@example.com",
       "difficulty_level": "intermediate",
       "question_count": 5
     }'
   ```
   - **Expected**: Graceful error with fallback to sample questions

2. **Service Unavailable Simulation** (if possible):
   - **Expected**: Fallback mechanism activates, sample questions generated
   - **Timeline**: UI shows fallback status message

---

## Test Suite 2: Enhanced Workflow Integration

### **Test 2.1: UI to AI Generation Integration**
**Objective**: Test complete UI workflow with AI question generation

**Test Steps**:
1. **Create Workflow via UI** (or simulate via API):
   ```bash
   curl -X POST "http://localhost:8081/api/v1/workflows/" \
     -H "Content-Type: application/json" \
     -d '{
       "user_id": "ai-test-user",
       "certification_profile_id": "455dae60-065c-4038-b3df-6d769b955dbb",
       "workflow_type": "assessment_generation",
       "parameters": {
         "title": "Sprint 4 AI Test Assessment",
         "difficulty_level": "intermediate",
         "question_count": 12,
         "domain_distribution": {"Security": 3, "Networking": 4, "Storage": 3, "Compute": 2}
       }
     }'
   ```
(.venv) yitzchak@MacBookPro presgen-assess % curl -X POST "http://localhost:8081/api/v1/ai-question-generator/generate" \
     -H "Content-Type: application/json" \
     -d '{
       "certification_profile_id": "00000000-0000-0000-0000-000000000000",
       "user_profile": "test@example.com",
       "difficulty_level": "intermediate",
       "question_count": 5
     }'
{"detail":[{"type":"missing","loc":["body","domain_distribution"],"msg":"Field required","input":{"certification_profile_id":"00000000-0000-0000-0000-000000000000","user_profile":"test@example.com","difficulty_level":"intermediate","question_count":5},"url":"https://errors.pydantic.dev/2.11/v/missing"}]}%  

2. **Trigger AI Orchestration**:
   ```bash
   # Use workflow_id from step 1
   curl -X POST "http://localhost:8081/api/v1/workflows/{workflow_id}/trigger-orchestration"
   ```
   (.venv) yitzchak@MacBookPro presgen-assess %    curl -X POST "http://localhost:8081/api/v1/workflows/9165ba53-0864-43dc-8776-209c0d98ec61/trigger-orchestration"

{"success":true,"message":"Workflow orchestration triggered successfully","workflow_id":"9165ba53-0864-43dc-8776-209c0d98ec61","orchestration_result":{"success":true,"workflow_id":"9230313d-f1f7-4768-a690-0e5610fd8779","form_id":"105Nbx5zVKdCsfUAaPZl8Kb9PQDl0kzNBOOcavwErdBU","form_url":"https://docs.google.com/forms/d/e/1FAIpQLScIJu5jH8nT2te1FznU-F4nAf9nxtfTbsAwXRybBCFvUrgqcA/viewform","status":"awaiting_completion","message":"Assessment form created and deployed. Awaiting responses."}}%  

3. **Monitor Timeline Updates**:
   ```bash
   # Check orchestration status multiple times during generation
   curl -X GET "http://localhost:8081/api/v1/workflows/{workflow_id}/orchestration-status"
   ```
(.venv) yitzchak@MacBookPro presgen-assess % curl -X GET "http://localhost:8081/api/v1/workflows/9165ba53-0864-43dc-8776-209c0d98ec61/orchestration-status"
{"success":true,"workflow_id":"9165ba53-0864-43dc-8776-209c0d98ec61","status":"awaiting_completion","current_step":"collect_responses","created_at":"2025-09-27T19:25:45.302315","updated_at":"2025-09-27T19:25:47.901281","google_form_id":"1i7RQXSDMF0fvPSFyjESXh50f5hAz3pGwmkGe0H8uWKQ","form_urls":{"form_url":"https://docs.google.com/forms/d/e/1FAIpQLSfVUzVFhWzdbgZX36eQXgZtNcY6meP7GzFnNQbjrjzo7Gf5XQ/viewform","form_edit_url":"","form_title":"AWS Solutions Architect Assessment"},"response_count":0,"paused_at":"2025-09-27T19:25:47.901260","resumed_at":null}%    

4. **Expected Timeline Progression**:
   ```json
   {
     "current_step": "ai_question_generation",
     "status": "in_progress",
     "progress_percentage": 45,
     "ai_generation_status": {
       "questions_generated": 8,
       "target_count": 12,
       "current_domain": "Storage",
       "estimated_completion": "30 seconds"
     }
   }
   ```

### **Test 2.2: Google Forms Integration with AI Questions**
**Objective**: Verify AI questions properly populate Google Forms

**Test Steps**:
1. **Wait for Orchestration Completion**:
   ```bash
   curl -X GET "http://localhost:8081/api/v1/workflows/{workflow_id}/orchestration-status"
   ```
   - **Expected**: `status: "awaiting_completion"`, `google_form_id` present

2. **Access Generated Google Form**:
   - Open form URL from orchestration response
   - **Manual Verification**:
     - [ ] Form contains 12 questions (not sample questions)
     - [ ] Questions are AWS-specific and technical
     - [ ] Domain distribution matches request (Security=3, Networking=4, etc.)
     - [ ] Question difficulty appears appropriate for intermediate level

3. **Form Structure Validation**:
   - [ ] Form title reflects assessment name
   - [ ] Questions are properly formatted with clear options
   - [ ] No placeholder or sample text visible

### **Test 2.3: Force Response Ingestion with AI Questions**
**Objective**: Test response collection with AI-generated content

**Test Steps**:
1. **Trigger Response Ingestion**:
   ```bash
   curl -X POST "http://localhost:8081/api/v1/workflows/{workflow_id}/force-ingest-responses"
   ```

2. **Expected Results**:
   ```json
   {
     "success": true,
     "message": "Response ingestion completed",
     "workflow_id": "uuid-here",
     "questions_processed": 12,
     "ai_generated": true
   }
   ```

---

## Test Suite 3: Performance & Quality Validation

### **Test 3.1: Generation Performance Testing**
**Objective**: Validate AI generation meets performance targets

**Test Scenarios**:
1. **Standard Load** (24 questions):
   - **Target**: < 2 minutes generation time
   - **Measurement**: Track `generation_time_ms` in response

2. **High Question Count** (50 questions):
   - **Target**: < 4 minutes generation time
   - **Expected**: Linear scaling performance

3. **Concurrent Generation** (3 workflows simultaneously):
   - **Target**: No significant performance degradation
   - **Method**: Create 3 workflows, trigger orchestration simultaneously

### **Test 3.2: Quality Score Validation**
**Objective**: Verify quality scores meet targets

**Quality Metrics Validation**:
```bash
# Extract quality scores from generation response
echo "Quality Score Targets:"
echo "- Relevance: >8.5/10"
echo "- Accuracy: >9.0/10"
echo "- Difficulty Calibration: >8.0/10"
echo ""
echo "Actual Scores: [Extract from API response]"
```

**Manual Quality Assessment** (Sample 3 questions):
1. **Expert Review Checklist**:
   - [ ] Question aligns with AWS certification exam objectives
   - [ ] Technical accuracy verified against AWS documentation
   - [ ] Difficulty appropriate for specified level
   - [ ] Options are realistic and well-crafted
   - [ ] Explanation provides educational value

---

## Test Suite 4: Monitoring & Logging Integration

### **Test 4.1: Enhanced Logging Validation**
**Objective**: Verify AI generation activities are properly logged

**Log Verification Steps**:
1. **Check AI Generation Logs**:
   ```bash
   # Check logs during AI generation
   tail -f /path/to/logs/ai_question_generation.log
   ```

2. **Expected Log Entries**:
   ```
   [2025-09-27 20:15:01] INFO - AI question generation started | workflow_id=uuid | cert_profile=455dae60 | question_count=24
   [2025-09-27 20:15:05] INFO - Knowledge base retrieval completed | cert_type=aws | resources_found=15
   [2025-09-27 20:15:25] INFO - Domain processing | domain=Networking | questions_generated=8 | quality_score=9.1
   [2025-09-27 20:15:45] INFO - AI question generation completed | total_time_ms=45000 | success=true | avg_quality=9.2
   ```

3. **Error Logging Test**:
   - Trigger error scenario (invalid profile)
   - **Expected**: Detailed error logs with fallback activation

### **Test 4.2: Monitoring Metrics Validation**
**Objective**: Verify AI generation metrics are captured

**Metrics Verification**:
```bash
# Check monitoring metrics
curl -X GET "http://localhost:8081/api/v1/monitoring/metrics"
```

**Expected New Metrics**:
- `ai_question_generation_requests_total`
- `ai_question_generation_duration_seconds`
- `ai_question_quality_score_average`
- `ai_generation_fallback_activations_total`

---

## Test Suite 5: End-to-End Workflow Validation

### **Test 5.1: Complete Workflow Lifecycle**
**Objective**: Test full workflow from UI creation to completion with AI questions

**End-to-End Test Steps**:
1. **Create Assessment Workflow** (via UI or API)
2. **Trigger AI Orchestration**
3. **Monitor AI Generation Progress**
4. **Verify Google Form Creation with AI Questions**
5. **Test Response Collection**
6. **Validate Timeline Updates Throughout**

**Success Criteria**:
- [ ] Complete workflow completes without errors
- [ ] AI questions successfully replace sample questions
- [ ] Timeline shows AI generation progress
- [ ] Google Form contains contextually relevant questions
- [ ] Response ingestion works with AI-generated content
- [ ] All monitoring and logging operational

### **Test 5.2: User Experience Validation**
**Objective**: Validate improved user experience with AI questions

**UX Comparison**:
1. **Before Sprint 4** (Sample Questions):
   - Generic, non-specific questions
   - No domain expertise evident
   - Limited educational value

2. **After Sprint 4** (AI Questions):
   - AWS-specific technical scenarios
   - Domain expertise clearly evident
   - High educational value with explanations

**User Satisfaction Metrics**:
- [ ] Questions appear professionally crafted
- [ ] Content relevance significantly improved
- [ ] Difficulty level appropriate for target audience
- [ ] Educational value clearly enhanced

---

## Acceptance Criteria Summary

### **Technical Acceptance**
- [ ] AI question generation completes within 2-minute target
- [ ] Quality scores consistently >8.0 across all metrics
- [ ] Integration with existing workflow orchestration seamless
- [ ] Performance targets met under normal and high load
- [ ] Error handling and fallback mechanisms functional

### **Business Acceptance**
- [ ] Generated questions demonstrate clear AWS expertise
- [ ] Domain distribution accurately reflects user specifications
- [ ] Difficulty calibration appropriate for target audience
- [ ] Educational value significantly improved over sample questions
- [ ] User experience enhanced with contextually relevant content

### **Integration Acceptance**
- [ ] UI timeline updates reflect AI generation progress
- [ ] Google Forms integration works with AI-generated questions
- [ ] Monitoring and logging capture AI generation activities
- [ ] Database performance maintained with enhanced functionality
- [ ] End-to-end workflow maintains >98% success rate

---

## Test Execution Checklist

### **Pre-Execution**
- [ ] Test environment verified and operational
- [ ] Test data prepared and available
- [ ] All Sprint 4 implementation completed
- [ ] Monitoring and logging systems operational

### **During Execution**
- [ ] Record all response times and performance metrics
- [ ] Capture screenshots of Google Forms with AI questions
- [ ] Document any deviations from expected results
- [ ] Note user experience improvements

### **Post-Execution**
- [ ] Compile test results summary
- [ ] Document any issues or improvement opportunities
- [ ] Update monitoring baselines with new metrics
- [ ] Create recommendations for future enhancements

### **Sign-off Criteria**
- [ ] All test suites completed successfully
- [ ] Performance targets achieved
- [ ] Quality standards met
- [ ] Integration requirements satisfied
- [ ] Business acceptance criteria fulfilled

**Sprint 4 TDD Testing Complete When**: All acceptance criteria met and stakeholder sign-off obtained

This comprehensive TDD manual testing plan ensures Sprint 4 AI question generation meets all technical, business, and integration requirements while maintaining the high quality standards established in previous sprints.



{
  "ok": true,
  "message": "Assessment workflow submitted successfully",
  "workflow_id": "05abb79b-0386-447d-a622-7aaf1c6afe52",
  "status": "pending",
  "resume_token": "0c05f7de-e7fc-40b0-ab16-40a68ede8162",
  "progress": 0,
  "parameters": {
    "title": "ass6",
    "summary_markdown": "ass6 Learner is a beginner in MLOps",
    "difficulty_level": "beginner",
    "question_count": 24,
    "passing_score": 70,
    "time_limit_minutes": 90,
    "slide_count": 12,
    "domain_distribution": {
      "Data Engineering": 4,
      "Exploratory Data Analysis": 5,
      "Modeling": 7,
      "Machine Learning Implementation and Operations": 8
    },
    "include_avatar": true,
    "notes_markdown": ""
  },
  "created_at": "2025-09-28T06:47:22",
  "updated_at": "2025-09-28T06:47:22"
}