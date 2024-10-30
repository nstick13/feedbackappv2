from typing import Dict
import json
from openai import OpenAI
import os

openai_client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

def generate_feedback_prompts(topic: str) -> Dict:
    prompt = f"""Generate a structured set of questions for gathering feedback about: {topic}
    Return as JSON with the following structure:
    {{
        "introduction": "opening context",
        "questions": ["question1", "question2", ...],
        "closing": "final thoughts prompt"
    }}
    Keep it focused and constructive."""
    
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)

def analyze_feedback(feedback_content: str) -> Dict:
    prompt = f"""Analyze this feedback and provide:
    1. Key themes
    2. Action items
    3. Summary
    Return as JSON structure.
    Feedback: {feedback_content}"""
    
    response = openai_client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        response_format={"type": "json_object"}
    )
    
    return json.loads(response.choices[0].message.content)
