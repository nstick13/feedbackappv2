from typing import Dict
import json
import logging
from openai import OpenAI
import os

logger = logging.getLogger(__name__)
openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def initiate_user_conversation(user_input: str) -> Dict:
    prompt = f"""You are having a conversation with a user who wants to receive feedback. 
    Engage with them briefly to understand their needs and summarize the key points.

    User input: {user_input}

    Please respond with a valid JSON object using exactly this structure:
    {{
        "summary": "<summary of the user's feedback needs>"
    }}

    Requirements:
    - Provide a concise summary of the user's feedback needs
    - Return only valid JSON, no additional text
    """

    try:
        logger.info("Initiating user conversation for feedback needs")
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )

        content = response.choices[0].message.content
        logger.debug(f"Raw API response content: {content}")

        try:
            parsed_content = json.loads(content)
            logger.info("Successfully parsed user conversation summary")
            return parsed_content
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse API response as JSON: {e}")
            raise ValueError("Invalid JSON response from OpenAI API")

    except Exception as e:
        logger.error(f"Error initiating user conversation: {str(e)}")
        raise RuntimeError(f"Failed to initiate user conversation: {str(e)}")

def generate_feedback_prompts(topic: str) -> Dict:
    prompt = f"""Generate a structured set of questions for gathering feedback about: {topic}

Please respond with a valid JSON object using exactly this structure:
{{
    "introduction": "<opening context paragraph>",
    "questions": ["<question 1>", "<question 2>", "<question 3>"],
    "closing": "<final thoughts prompt paragraph>"
}}

Requirements:
- Keep questions focused and constructive
- Include 3-5 specific questions
- Make sure the introduction provides clear context
- Ensure the closing prompts for additional thoughts
- Return only valid JSON, no additional text
"""
    
    try:
        logger.info(f"Generating feedback prompts for topic: {topic}")
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        
        content = response.choices[0].message.content
        logger.debug(f"Raw API response content: {content}")
        
        try:
            parsed_content = json.loads(content)
            logger.info("Successfully parsed feedback prompts")
            return parsed_content
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse API response as JSON: {e}")
            raise ValueError("Invalid JSON response from OpenAI API")
            
    except Exception as e:
        logger.error(f"Error generating feedback prompts: {str(e)}")
        raise RuntimeError(f"Failed to generate feedback prompts: {str(e)}")

def analyze_feedback(feedback_content: str) -> Dict:
    prompt = f"""Analyze this feedback and extract key insights. 
Respond with a valid JSON object using exactly this structure:
{{
    "themes": ["<key theme 1>", "<key theme 2>"],
    "action_items": ["<actionable item 1>", "<actionable item 2>"],
    "summary": "<brief summary paragraph>"
}}

Analyze the following feedback:
{feedback_content}

Requirements:
- Extract 2-4 main themes
- Identify specific actionable items
- Provide a concise summary
- Return only valid JSON, no additional text
"""
    
    try:
        logger.info("Analyzing feedback content")
        response = openai_client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": prompt}]
        )
        
        content = response.choices[0].message.content
        logger.debug(f"Raw API response content: {content}")
        
        try:
            parsed_content = json.loads(content)
            logger.info("Successfully parsed feedback analysis")
            return parsed_content
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse API response as JSON: {e}")
            raise ValueError("Invalid JSON response from OpenAI API")
            
    except Exception as e:
        logger.error(f"Error analyzing feedback: {str(e)}")
        raise RuntimeError(f"Failed to analyze feedback: {str(e)}")

