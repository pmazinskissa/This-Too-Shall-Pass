"""
Configuration settings for the Meeting Summarizer application.
"""
import os
from dotenv import load_dotenv

# Load environment variables from .env file
from dotenv import load_dotenv
import os

# Load .env file if it exists (development), otherwise use environment variables (production)
if os.path.exists('.env'):
    load_dotenv()

# Flask configuration
DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
SECRET_KEY = os.getenv('SECRET_KEY', 'your-secret-key-for-dev')
MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file upload size

# OpenAI API configuration
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_MODEL = os.getenv('OPENAI_MODEL', 'gpt-4.1')

# File paths
UPLOAD_FOLDER = os.path.join(os.getcwd(), 'uploads')
EXPORT_FOLDER = os.path.join(os.getcwd(), 'exports')

# Ensure required directories exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(EXPORT_FOLDER, exist_ok=True)

# Application constants
SUMMARY_STRUCTURE = {
    'executive_summary': 'A concise overview of the meeting.',
    'participants': [],
    'detailed_summary': [],
    'decisions_made': [],
    'actions_planned': [],
    'open_questions': [],
    'risks_mitigations': [],
    'key_quotes': [],
    'sentiment_analysis': 'Analysis of meeting tone and engagement.',
    'content_gaps': [],
    'terminology': []
}

# OpenAI prompt templates
SYSTEM_PROMPT_TEMPLATE = """
You are an expert in summarizing meeting transcripts. Your task is to analyze the meeting transcript 
and generate a comprehensive, structured summary following the exact format specified below. 
Your output should be in JSON format with the following sections:

1. executive_summary: A concise paragraph summarizing key points and outcomes
2. participants: List of participants with name, organization/title, and meeting role
3. detailed_summary: Detailed breakdown of the meeting with subsections
4. decisions_made: List of decisions with details and owners
5. actions_planned: List of actions with responsible parties, timelines, and notes
6. open_questions: Unresolved questions with context and owners
7. risks_mitigations: Identified risks with impact, mitigation, and owners
8. key_quotes: Notable quotes with attribution
9. sentiment_analysis: Brief analysis of the meeting's tone and engagement
10. content_gaps: Potential missing information or topics
11. terminology: Technical terms and acronyms mentioned with definitions

For any sections where information is not available in the transcript, include a placeholder note.
Focus on accuracy, clarity, and maintaining the original meaning.
"""

USER_PROMPT_TEMPLATE = """
Please summarize the following meeting transcript.

Meeting Title: {title}
Date: {date}
Duration: {duration}

Transcript:
{transcript}

Provide the summary in JSON format following the structure specified.
"""