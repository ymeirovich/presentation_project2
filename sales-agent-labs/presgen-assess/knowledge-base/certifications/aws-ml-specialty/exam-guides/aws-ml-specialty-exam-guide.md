# AWS Certified Machine Learning - Specialty Exam Guide

## Domain 1: Data Engineering (20%)

### 1.1 Create data repositories for machine learning
- Identify data sources (e.g., content and location, primary sources such as user-generated content)
- Determine storage mediums (e.g., DB, Data Lake, S3, EFS, EBS)
- Create data ingestion pipelines (e.g., batch, streaming, real time)
- Store data in a data lake or data warehouse

### 1.2 Identify and implement a data-ingestion solution
- Data transformation services (e.g., AWS Glue)
- Data migration services (e.g., AWS DMS, AWS DataSync)
- Data lakes and data repositories (e.g., AWS Lake Formation)

### 1.3 Identify and implement a data-transformation solution
- Transforming data transit (ETL: Glue, EMR, AWS Batch)
- Handle missing data, corrupt data, stop words, etc.
- Organize, augment, and label data (e.g., Mechanical Turk)
- Data labeling tools (e.g., Amazon SageMaker Ground Truth)

## Domain 2: Exploratory Data Analysis (24%)

### 2.1 Sanitize and prepare data for modeling
- Identify and handle missing data, corrupt data, stop words, etc.
- Formatting, normalizing, augmenting, and scaling data
- Labeled data (e.g., supervised learning)

### 2.2 Perform feature engineering
- Identify and extract features from datasets
- Analyze and evaluate feature engineering concepts
- Implement feature engineering techniques

### 2.3 Analyze and visualize data for machine learning
- Graphing (e.g., scatter plot, time series, histogram, box plot)
- Interpreting descriptive statistics (e.g., correlation, summary statistics, p-value)
- Clustering (e.g., hierarchical, diagnosis, elbow method, cluster size)

## Domain 3: Modeling (36%)

### 3.1 Frame business problems as machine learning problems
- Determine when to use/when not to use ML
- Know the difference between supervised and unsupervised learning
- Selecting from among classification, regression, forecasting, clustering, recommendation, etc.

### 3.2 Select the appropriate model(s) for a given machine learning problem
- Xgboost, logistic regression, K-means, linear regression, decision trees, random forests, RNN, CNN, Ensemble methods, Transfer learning
- Express intuition behind models

### 3.3 Train machine learning models
- Train/validation/test dataset split
- Hyperparameter optimization
- Cross validation
- Regularization
  - Drop out
  - L1/L2
- Gradient descent/back propagation

### 3.4 Perform hyperparameter optimization
- Bayesian optimization
- Multi-armed bandit
- Grid/random search

### 3.5 Evaluate machine learning models
- Avoid overfitting/underfitting
- Metrics (AUC-ROC, accuracy, precision, recall, F1, confusion matrix)
- Cross validation
- Model fit (under fitting vs. over fitting)

## Domain 4: Machine Learning Implementation and Operations (20%)

### 4.1 Build machine learning solutions for performance, availability, scalability, resiliency, and fault tolerance
- AWS environment logging and monitoring
  - CloudWatch logs
  - CloudWatch monitoring
  - AWS CloudTrail logs
- Multiple AZ deployments
- Auto-scaling groups
- Application Load Balancers (ALB)
- AWS Global infrastructure (AZ, regions, edge locations)

### 4.2 Recommend and implement the appropriate machine learning services and features for a given problem
- ML on AWS (application services)
  - Amazon Polly, Amazon Lex, Amazon Transcribe
- AWS SageMaker
- AWS Deep Learning AMIs
- AWS Deep Learning containers
- Amazon Machine Learning

### 4.3 Apply basic AWS security practices to machine learning solutions
- AWS IAM
- S3 bucket policies
- Security groups
- VPCs
- Encryption in transit and at rest

### 4.4 Deploy and operationalize machine learning solutions
- Exposing endpoints and interacting with them
- A/B testing
- Retrain pipelines
- ML debugging and optimization
- Detect and mitigate drop in performance
- Monitor performance of the model

## Key AWS Services for Machine Learning

### Amazon SageMaker
- Fully managed machine learning service
- Built-in algorithms and frameworks
- Notebook instances for development
- Training jobs with automatic model tuning
- Real-time and batch inference endpoints
- Model monitoring and management

### AWS Glue
- Serverless ETL service
- Data catalog and schema discovery
- Job scheduling and monitoring
- Support for Apache Spark

### Amazon EMR
- Managed Hadoop and Spark clusters
- Big data processing and analytics
- Support for multiple frameworks (Spark, Hive, HBase, etc.)

### Amazon Kinesis
- Real-time data streaming
- Kinesis Data Streams, Data Firehose, Data Analytics
- Integration with machine learning services

### AWS Lambda
- Serverless compute for ML workflows
- Event-driven processing
- Integration with other AWS services

## Best Practices

1. **Data Preparation**
   - Clean and preprocess data thoroughly
   - Handle missing values appropriately
   - Feature scaling and normalization
   - Train/validation/test split

2. **Model Development**
   - Start with simple models
   - Use cross-validation
   - Hyperparameter tuning
   - Regularization techniques

3. **Model Evaluation**
   - Use appropriate metrics for the problem
   - Avoid overfitting
   - Test on unseen data
   - Monitor model performance in production

4. **Production Deployment**
   - A/B testing for model comparison
   - Monitoring and alerting
   - Automated retraining pipelines
   - Security and compliance considerations