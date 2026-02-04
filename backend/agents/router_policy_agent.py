"""
Router & Policy Agent
Evaluates questions against privacy rules
"""

from typing import Dict, Any, Tuple, List
from ..database.models import CandidateProfile
from ..services.policy_service import PolicyService
from ..utils.llm_client import LLMClient
from ..config import POLICY_ALLOW, POLICY_BLOCK, POLICY_PARTIAL


class RouterPolicyAgent:
    """
    Agent that routes questions and enforces privacy policies

    Input:
    - Recruiter question
    - Candidate-defined privacy rules

    Output:
    - Policy decision: ALLOW / BLOCK / PARTIAL
    - Relevant fields that the question is asking about
    - Reason for decision
    """

    # Mapping of sensitive topics to fields
    TOPIC_TO_FIELDS = {
        "salary": ["salary", "expected_salary", "compensation"],
        "compensation": ["salary", "expected_salary", "compensation"],
        "money": ["salary", "expected_salary", "compensation"],
        "pay": ["salary", "expected_salary", "compensation"],
        "phone": ["phone"],
        "contact": ["phone", "email", "address"],
        "address": ["address", "location"],
        "age": ["age", "date_of_birth"],
        "personal": ["phone", "email", "address", "age"],
    }

    def __init__(self, policy_service: PolicyService):
        self.policy_service = policy_service
        self.llm = LLMClient()

    def analyze_question(self, question: str) -> Dict[str, Any]:
        """Analyze question to determine relevant fields"""
        # Available fields
        all_fields = [
            "name", "email", "phone", "location", "address", "summary",
            "skills", "education", "experience", "projects",
            "job_preferences", "remote_preference", "expected_salary",
            "salary", "notice_period", "willing_to_relocate"
        ]

        prompt = f"""Analyze this recruiter question about a job candidate:

Question: "{question}"

Determine which profile fields are relevant to answer this question.
Available fields: {', '.join(all_fields)}

Return JSON with:
{{
    "relevant_fields": ["field1", "field2"],
    "question_intent": "brief description of what the question is asking",
    "is_sensitive": true/false (if asking about salary, personal contact, etc.)
}}

JSON:"""

        result = self.llm.generate_json(prompt)

        # Fallback if LLM fails
        if not result:
            result = {
                "relevant_fields": self._detect_fields_rule_based(question),
                "question_intent": "general inquiry",
                "is_sensitive": self._is_sensitive_question(question)
            }

        return result

    def _detect_fields_rule_based(self, question: str) -> List[str]:
        """Rule-based field detection as fallback"""
        question_lower = question.lower()
        fields = []

        # Experience related
        if any(w in question_lower for w in ["experience", "work", "job", "role", "position", "company", "employer"]):
            fields.append("experience")

        # Skills related
        if any(w in question_lower for w in ["skill", "technology", "programming", "language", "framework", "tool"]):
            fields.append("skills")

        # Education related
        if any(w in question_lower for w in ["education", "degree", "university", "college", "school", "study"]):
            fields.append("education")

        # Projects related
        if any(w in question_lower for w in ["project", "portfolio", "built", "created", "developed"]):
            fields.append("projects")

        # Job preferences
        if any(w in question_lower for w in ["remote", "location", "relocate", "work from", "hybrid", "onsite"]):
            fields.append("job_preferences")

        # Salary (sensitive)
        if any(w in question_lower for w in ["salary", "compensation", "pay", "money", "ctc", "package"]):
            fields.append("salary")
            fields.append("expected_salary")

        # Contact (sensitive)
        if any(w in question_lower for w in ["phone", "call", "number", "contact"]):
            fields.append("phone")

        if any(w in question_lower for w in ["email", "mail", "reach"]):
            fields.append("email")

        # Summary/general
        if any(w in question_lower for w in ["about", "tell me", "background", "summary", "overview"]):
            fields.append("summary")

        # If no specific fields detected, assume general professional info
        if not fields:
            fields = ["experience", "skills", "summary"]

        return fields

    def _is_sensitive_question(self, question: str) -> bool:
        """Check if question is about sensitive topics"""
        question_lower = question.lower()
        sensitive_keywords = [
            "salary", "compensation", "pay", "money", "ctc", "package",
            "phone", "number", "call",
            "address", "live", "residence",
            "age", "old", "birth",
            "personal", "private"
        ]
        return any(kw in question_lower for kw in sensitive_keywords)

    def evaluate(
        self,
        profile_id: int,
        question: str
    ) -> Tuple[str, List[str], str]:
        """
        Evaluate question against privacy policies

        Returns:
        - policy_decision: ALLOW / BLOCK / PARTIAL
        - allowed_fields: list of fields allowed to use
        - reason: explanation of decision
        """
        # Analyze question
        analysis = self.analyze_question(question)
        relevant_fields = analysis.get("relevant_fields", [])

        if not relevant_fields:
            return POLICY_ALLOW, [], "General inquiry with no specific field requirements"

        # Check policy for each relevant field
        blocked_fields = []
        partial_fields = []
        allowed_fields = []

        for field in relevant_fields:
            policy_type, _ = self.policy_service.check_field_allowed(profile_id, field)

            if policy_type == POLICY_BLOCK:
                blocked_fields.append(field)
            elif policy_type == POLICY_PARTIAL:
                partial_fields.append(field)
            else:
                allowed_fields.append(field)

        # Determine overall decision
        if all(f in blocked_fields for f in relevant_fields):
            # All relevant fields are blocked
            decision = POLICY_BLOCK
            reason = f"This question asks about blocked information: {', '.join(blocked_fields)}"
        elif any(f in blocked_fields for f in relevant_fields):
            # Some fields blocked
            decision = POLICY_PARTIAL
            reason = f"Some requested information is restricted. Available: {', '.join(allowed_fields + partial_fields)}"
        elif partial_fields:
            decision = POLICY_PARTIAL
            reason = f"Limited information available for: {', '.join(partial_fields)}"
        else:
            decision = POLICY_ALLOW
            reason = "All requested information is available"
            allowed_fields = relevant_fields

        return decision, allowed_fields, reason

    def get_policy_explanation(
        self,
        profile_id: int,
        blocked_field: str
    ) -> str:
        """Get explanation for why a field is blocked"""
        policy_type, _ = self.policy_service.check_field_allowed(profile_id, blocked_field)

        explanations = {
            "salary": "Salary information is kept confidential by the candidate.",
            "expected_salary": "Expected compensation is kept confidential by the candidate.",
            "phone": "Contact phone number is not disclosed publicly.",
            "address": "Physical address is not disclosed for privacy reasons.",
            "email": "Direct email contact is restricted.",
        }

        return explanations.get(
            blocked_field,
            f"Information about {blocked_field} is restricted by the candidate's privacy settings."
        )
