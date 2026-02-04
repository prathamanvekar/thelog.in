"""
Resume Parser Service using LLM
"""

import os
import re
from typing import Dict, Any, Optional
from pathlib import Path

from ..utils.llm_client import LLMClient
from ..database.models import (
    CandidateProfile,
    Education,
    Experience,
    Project,
    JobPreferences
)


class ResumeParser:
    """Parse resumes using LLM"""

    def __init__(self):
        self.llm = LLMClient()

    def parse_pdf(self, file_path: str) -> str:
        """Extract text from PDF file"""
        try:
            import pdfplumber

            text = ""
            with pdfplumber.open(file_path) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text.strip()
        except Exception as e:
            print(f"PDF parsing error: {e}")
            return ""

    def parse_docx(self, file_path: str) -> str:
        """Extract text from DOCX file"""
        try:
            from docx import Document

            doc = Document(file_path)
            text = ""
            for para in doc.paragraphs:
                text += para.text + "\n"
            return text.strip()
        except Exception as e:
            print(f"DOCX parsing error: {e}")
            return ""

    def extract_text(self, file_path: str) -> str:
        """Extract text from resume file"""
        ext = Path(file_path).suffix.lower()

        if ext == '.pdf':
            return self.parse_pdf(file_path)
        elif ext in ['.docx', '.doc']:
            return self.parse_docx(file_path)
        elif ext == '.txt':
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read()
        else:
            raise ValueError(f"Unsupported file format: {ext}")

    def parse_resume_text(self, text: str) -> Dict[str, Any]:
        """Parse resume text using LLM to extract structured data"""

        system_prompt = """You are a resume parser. Extract structured information from the resume text.
Be accurate and only extract information that is explicitly stated.
If information is not available, use empty strings or empty lists."""

        prompt = f"""Parse the following resume and extract information in JSON format.

Resume Text:
{text}

Extract the following fields:
{{
    "name": "Full name",
    "email": "Email address",
    "phone": "Phone number",
    "location": "City, State or City, Country",
    "summary": "Professional summary or objective (1-2 sentences)",
    "skills": ["skill1", "skill2", ...],
    "education": [
        {{
            "institution": "University/College name",
            "degree": "Degree type (BS, MS, PhD, etc.)",
            "field_of_study": "Major/Field",
            "start_year": 2020,
            "end_year": 2024,
            "description": "Any additional details"
        }}
    ],
    "experience": [
        {{
            "company": "Company name",
            "title": "Job title",
            "location": "City, Country",
            "start_date": "Month Year or Year",
            "end_date": "Month Year or Present",
            "is_current": false,
            "description": "Job description",
            "highlights": ["achievement1", "achievement2"]
        }}
    ],
    "projects": [
        {{
            "name": "Project name",
            "description": "Brief description",
            "technologies": ["tech1", "tech2"],
            "url": "Project URL if available",
            "start_date": "",
            "end_date": ""
        }}
    ]
}}

Return only valid JSON:"""

        result = self.llm.generate_json(prompt, system_prompt)
        return result

    def parse_resume(self, file_path: str) -> CandidateProfile:
        """Parse resume file and return CandidateProfile"""
        text = self.extract_text(file_path)
        if not text:
            raise ValueError("Could not extract text from resume")

        data = self.parse_resume_text(text)

        # Convert to CandidateProfile
        profile = CandidateProfile(
            name=data.get("name", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            location=data.get("location", ""),
            summary=data.get("summary", ""),
            skills=data.get("skills", [])
        )

        # Parse education
        for edu_data in data.get("education", []):
            edu = Education(
                institution=edu_data.get("institution", ""),
                degree=edu_data.get("degree", ""),
                field_of_study=edu_data.get("field_of_study", ""),
                start_year=edu_data.get("start_year"),
                end_year=edu_data.get("end_year"),
                description=edu_data.get("description", "")
            )
            profile.education.append(edu)

        # Parse experience
        for exp_data in data.get("experience", []):
            exp = Experience(
                company=exp_data.get("company", ""),
                title=exp_data.get("title", ""),
                location=exp_data.get("location", ""),
                start_date=exp_data.get("start_date", ""),
                end_date=exp_data.get("end_date", ""),
                is_current=exp_data.get("is_current", False),
                description=exp_data.get("description", ""),
                highlights=exp_data.get("highlights", [])
            )
            profile.experience.append(exp)

        # Parse projects
        for proj_data in data.get("projects", []):
            proj = Project(
                name=proj_data.get("name", ""),
                description=proj_data.get("description", ""),
                technologies=proj_data.get("technologies", []),
                url=proj_data.get("url", ""),
                start_date=proj_data.get("start_date", ""),
                end_date=proj_data.get("end_date", "")
            )
            profile.projects.append(proj)

        return profile

    def parse_text_resume(self, text: str) -> CandidateProfile:
        """Parse resume from raw text"""
        data = self.parse_resume_text(text)

        profile = CandidateProfile(
            name=data.get("name", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            location=data.get("location", ""),
            summary=data.get("summary", ""),
            skills=data.get("skills", [])
        )

        for edu_data in data.get("education", []):
            edu = Education(
                institution=edu_data.get("institution", ""),
                degree=edu_data.get("degree", ""),
                field_of_study=edu_data.get("field_of_study", ""),
                start_year=edu_data.get("start_year"),
                end_year=edu_data.get("end_year"),
                description=edu_data.get("description", "")
            )
            profile.education.append(edu)

        for exp_data in data.get("experience", []):
            exp = Experience(
                company=exp_data.get("company", ""),
                title=exp_data.get("title", ""),
                location=exp_data.get("location", ""),
                start_date=exp_data.get("start_date", ""),
                end_date=exp_data.get("end_date", ""),
                is_current=exp_data.get("is_current", False),
                description=exp_data.get("description", ""),
                highlights=exp_data.get("highlights", [])
            )
            profile.experience.append(exp)

        for proj_data in data.get("projects", []):
            proj = Project(
                name=proj_data.get("name", ""),
                description=proj_data.get("description", ""),
                technologies=proj_data.get("technologies", []),
                url=proj_data.get("url", ""),
                start_date=proj_data.get("start_date", ""),
                end_date=proj_data.get("end_date", "")
            )
            profile.projects.append(proj)

        return profile
