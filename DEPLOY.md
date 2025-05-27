# Deployment Guide

This guide will help you deploy the Research Paper Insights Generator to the web using free services.

## Prerequisites

1. Sign up for free accounts on:
   - [Pinecone](https://www.pinecone.io/) - Free tier for vector database
   - [Hugging Face](https://huggingface.co/) - Free API access for embeddings and LLM
   - [Render](https://render.com/) - Free web service deployment

## Setup Steps

### 1. Get API Keys

1. **Pinecone API Key**:
   - Create a free account on Pinecone
   - Navigate to API Keys section
   - Create a new API key and note the API key and environment

2. **Hugging Face API Key**:
   - Sign up for a free Hugging Face account
   - Go to your profile > Settings > Access Tokens
   - Create a new token with read access

### 2. Configure Environment Variables

1. Update the `.env` file with your actual API keys:
   ```
   PINECONE_API_KEY=your-pinecone-api-key
   PINECONE_ENVIRONMENT=your-pinecone-environment
   HUGGINGFACE_API_KEY=your-huggingface-api-key
   ```

### 3. Deploy to Render (Free)

1. Push your code to a GitHub repository
2. Log in to Render
3. Click "New +" and select "Web Service"
4. Connect your GitHub repository
5. Configure the service:
   - Name: research-paper-assistant
   - Build Command: `pip install -r requirements.txt`
   - Start Command: `gunicorn main:app`
   - Add all the environment variables from your .env file
6. Click "Create Web Service"

Your application will be deployed and accessible at the URL provided by Render.

## Alternative Free Deployments

### Hugging Face Spaces

1. Create a new Space on Hugging Face
2. Choose Flask as the SDK
3. Upload your code and configure environment variables
4. Your app will be hosted on huggingface.co

### Google Cloud Run

Google Cloud offers a free tier that includes Cloud Run:
1. Set up a Google Cloud account
2. Enable Cloud Run API
3. Deploy your container using the Google Cloud CLI 