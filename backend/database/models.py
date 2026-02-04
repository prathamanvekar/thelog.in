"""
Data models for theLog.in
"""

from dataclasses import dataclass, field, asdict
from typing import List, Dict, Optional, Any
from datetime import datetime
import json


@dataclass
class Education:
    institution: str = ""
    degree: str = ""
    field_of_study: str = ""
    start_year: Optional[int] = None
    end_year: Optional[int] = None
    description: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "Education":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Experience:
    company: str = ""
    title: str = ""
    location: str = ""
    start_date: str = ""
    end_date: str = ""
    is_current: bool = False
    description: str = ""
    highlights: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "Experience":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class Project:
    name: str = ""
    description: str = ""
    technologies: List[str] = field(default_factory=list)
    url: str = ""
    start_date: str = ""
    end_date: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "Project":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class JobPreferences:
    desired_roles: List[str] = field(default_factory=list)
    preferred_locations: List[str] = field(default_factory=list)
    remote_preference: str = ""  # "remote", "hybrid", "onsite", "flexible"
    expected_salary: str = ""
    notice_period: str = ""
    willing_to_relocate: bool = False

    def to_dict(self) -> Dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict) -> "JobPreferences":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class CandidateProfile:
    id: Optional[int] = None
    slug: str = ""
    name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    summary: str = ""
    skills: List[str] = field(default_factory=list)
    education: List[Education] = field(default_factory=list)
    experience: List[Experience] = field(default_factory=list)
    projects: List[Project] = field(default_factory=list)
    job_preferences: Optional[JobPreferences] = None
    email_verified: bool = False
    created_at: Optional[str] = None
    updated_at: Optional[str] = None

    def to_dict(self) -> Dict:
        data = {
            "id": self.id,
            "slug": self.slug,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "location": self.location,
            "summary": self.summary,
            "skills": self.skills,
            "education": [e.to_dict() for e in self.education],
            "experience": [e.to_dict() for e in self.experience],
            "projects": [p.to_dict() for p in self.projects],
            "job_preferences": self.job_preferences.to_dict() if self.job_preferences else None,
            "email_verified": self.email_verified,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
        return data

    def to_json(self) -> str:
        return json.dumps(self.to_dict())

    @classmethod
    def from_dict(cls, data: Dict) -> "CandidateProfile":
        profile = cls(
            id=data.get("id"),
            slug=data.get("slug", ""),
            name=data.get("name", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            location=data.get("location", ""),
            summary=data.get("summary", ""),
            skills=data.get("skills", []),
            email_verified=data.get("email_verified", False),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at")
        )

        if "education" in data and data["education"]:
            profile.education = [Education.from_dict(e) for e in data["education"]]

        if "experience" in data and data["experience"]:
            profile.experience = [Experience.from_dict(e) for e in data["experience"]]

        if "projects" in data and data["projects"]:
            profile.projects = [Project.from_dict(p) for p in data["projects"]]

        if "job_preferences" in data and data["job_preferences"]:
            profile.job_preferences = JobPreferences.from_dict(data["job_preferences"])

        return profile


@dataclass
class PrivacyPolicy:
    id: Optional[int] = None
    profile_id: int = 0
    field_name: str = ""
    policy_type: str = "ALLOW"  # ALLOW, BLOCK, PARTIAL
    partial_config: Optional[Dict] = None
    created_at: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class LinkedProfile:
    id: Optional[int] = None
    profile_id: int = 0
    platform: str = ""  # linkedin, github, portfolio
    url: str = ""
    is_reachable: Optional[bool] = None
    last_checked: Optional[str] = None
    extracted_name: str = ""
    extracted_keywords: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict:
        data = asdict(self)
        data["extracted_keywords"] = self.extracted_keywords
        return data


@dataclass
class Interaction:
    id: Optional[int] = None
    profile_id: int = 0
    recruiter_question: str = ""
    policy_decision: str = ""
    grounding_packet: Dict = field(default_factory=dict)
    gci_score: float = 0.0
    generated_answer: str = ""
    verification_result: str = ""
    final_response: str = ""
    created_at: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class TrustworthinessScore:
    id: Optional[int] = None
    profile_id: int = 0
    total_score: float = 0.0
    trust_band: str = ""
    identity_score: float = 0.0
    consistency_score: float = 0.0
    internal_score: float = 0.0
    transparency_score: float = 0.0
    breakdown: Dict = field(default_factory=dict)
    reasons: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    last_verified: Optional[str] = None

    def to_dict(self) -> Dict:
        return asdict(self)
