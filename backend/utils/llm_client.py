"""
LLM Client using Groq API
"""

import os
from typing import Optional, Dict, Any, List
from groq import Groq

from ..config import GROQ_API_KEY, GROQ_MODEL


class LLMClient:
    """Client for interacting with Groq LLM API"""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or GROQ_API_KEY
        self.model = model or GROQ_MODEL

        if not self.api_key:
            raise ValueError("GROQ_API_KEY not set. Please set it in .env file or pass it directly.")

        self.client = Groq(api_key=self.api_key)

    def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.3,
        max_tokens: int = 1024
    ) -> str:
        """Generate a response from the LLM"""
        messages = []

        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})

        messages.append({"role": "user", "content": prompt})

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"LLM Error: {e}")
            return ""

    def generate_json(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.1,
        max_tokens: int = 2048
    ) -> Dict[str, Any]:
        """Generate a JSON response from the LLM"""
        import json

        json_system = (system_prompt or "") + "\nRespond only with valid JSON, no additional text."

        response = self.generate(prompt, json_system, temperature, max_tokens)

        # Try to extract JSON from response
        try:
            # Handle markdown code blocks
            if "```json" in response:
                response = response.split("```json")[1].split("```")[0]
            elif "```" in response:
                response = response.split("```")[1].split("```")[0]

            return json.loads(response.strip())
        except json.JSONDecodeError:
            # Try to find JSON object in response
            try:
                start = response.find("{")
                end = response.rfind("}") + 1
                if start != -1 and end > start:
                    return json.loads(response[start:end])
            except:
                pass
            return {}

    def analyze_question(self, question: str, profile_fields: List[str]) -> Dict[str, Any]:
        """Analyze what fields a question is asking about"""
        prompt = f"""Analyze this recruiter question and determine which profile fields it's asking about.

Question: "{question}"

Available profile fields: {', '.join(profile_fields)}

Return JSON with:
- "relevant_fields": list of field names the question is asking about
- "question_type": one of "experience", "skills", "education", "preferences", "personal", "general"
- "sensitivity": "low", "medium", or "high"

JSON Response:"""

        return self.generate_json(prompt)
