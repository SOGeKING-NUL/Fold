# Bank Statement Analysis Project

## Overview
This project enables users to upload their bank statements (PDFs) and receive detailed spending analysis, including categorization of expenses, monthly income vs. expenditure comparison, and overspending alerts. The solution leverages AWS free tier services for OCR and storage, combined with OpenRouter APIs for powerful LLM-based analysis and summary generation.

## Architecture

### Components
- **Frontend**: React or Next.js web app hosted on AWS Amplify or S3+CloudFront for user uploads and report visualization.
- **Storage**: Amazon S3 to store uploaded bank statement PDFs and processed data.
- **OCR Processing**: AWS Lambda triggered by S3 events to run Amazon Textract for text and data extraction from PDFs.
- **Database**: Amazon DynamoDB to store parsed transaction data and LLM analysis results.
- **LLM Analysis**: OpenRouter API to call open-source LLMs for categorization, analysis, and summary generation.
- **Backend**: AWS Lambda functions to orchestrate Textract OCR, calls to OpenRouter, data processing, and API Gateway endpoints for frontend communication.
- **Notifications**: Optional Amazon SNS for overspending alerts.

### Workflow
1. User uploads bank statement PDF via the frontend.
2. PDF is stored in an S3 bucket, triggering a Lambda function.
3. Lambda calls Amazon Textract to perform OCR and extract structured document data.
4. Extracted data JSON is saved into S3 or directly stored in DynamoDB.
5. Another Lambda function sends extracted transaction data to OpenRouter API for LLM-based analysis and categorization.
6. Processed results with categorized expenses and summaries are saved in DynamoDB.
7. Frontend fetches analyzed data via API Gateway to display detailed reports.
8. Notifications about overspending may be sent using Amazon SNS.

## AWS Free Tier Usage
- **Amazon S3**: 5 GB storage free tier.
- **AWS Lambda**: 1 million requests and 400,000 GB-seconds compute per month.
- **Amazon Textract**: 1,000 pages per month free for text extraction.
- **Amazon DynamoDB**: 25 GB storage and 25 write/read units free per month.
- **API Gateway & Amplify**: Limited free tier usage for API requests and hosting.

## Setup Instructions

### 1. Frontend
- Create a React/Next.js app.
- Host on AWS Amplify or S3+CloudFront for static hosting.
- Implement upload UI to send PDFs to S3 bucket.

### 2. AWS Infrastructure
- Create an S3 bucket to store uploads.
- Set up Lambda functions:
  - Textract OCR processor triggered by S3 upload.
  - LLM orchestrator that calls OpenRouter API using extracted data.
- Create DynamoDB table for transactions and analysis storage.
- Configure API Gateway to expose endpoints for frontend data fetching.
- (Optional) Set up SNS Topic for notifications.

### 3. OpenRouter Integration
- Register with OpenRouter for API key.
- Use Lambda to send extracted data JSON to OpenRouter LLM.
- Receive categorization and analysis response.
- Store analysis results in DynamoDB.

## Development Tips
- Use AWS SDK in Lambda functions for Textract, DynamoDB, and S3 operations.
- Secure API Gateway with authentication for user data privacy.
- Batch Textract calls for multi-page PDFs to stay within free tier.
- Cache analysis results to minimize repeated LLM API calls.

## References
- [Amazon Textract Documentation](https://aws.amazon.com/textract/)
- [OpenRouter API](https://openrouter.ai)
- [AWS Free Tier Details](https://aws.amazon.com/free/)
- [Sample Textract Bank Statement Processor](https://github.com/aws-samples/textract-bank-statement-processor)

## License
This project is provided as-is for educational and development purposes.

