"""
Grounding Agent
Retrieves relevant profile data and computes coverage score
"""

from typing import Dict, Any, List, Tuple
from ..database.models import CandidateProfile
from ..utils.llm_client import LLMClient
from ..config import GCI_HIGH_THRESHOLD, GCI_LOW_THRESHOLD


class GroundingAgent:
    """
    Agent that extracts relevant facts from profile data

    Input:
    - Allowed question
    - Structured profile JSON
    - Allowed fields (from policy agent)

    Output:
    - Grounding packet (list of relevant facts)
    - Grounding Coverage Index (GCI)
    """

    def __init__(self):
        self.llm = LLMClient()

    def extract_grounding(
        self,
        question: str,
        profile_data: Dict[str, Any],
        allowed_fields: List[str]
    ) -> Tuple[Dict[str, Any], float]:
        """
        Extract relevant facts from profile data

        Returns:
        - grounding_packet: dict of relevant facts
        - gci_score: coverage score 0.0 to 1.0
        """
        # Filter profile data to only allowed fields
        filtered_data = self._filter_profile_data(profile_data, allowed_fields)

        if not filtered_data:
            return {}, 0.0

        # Use LLM to extract most relevant facts
        grounding_packet = self._extract_relevant_facts(question, filtered_data)

        # Compute coverage score
        gci_score = self._compute_gci(question, grounding_packet)

        return grounding_packet, gci_score

    def _filter_profile_data(
        self,
        profile_data: Dict[str, Any],
        allowed_fields: List[str]
    ) -> Dict[str, Any]:
        """Filter profile data to only include allowed fields"""
        filtered = {}

        # Field mapping for nested data
        field_mapping = {
            "experience": "experience",
            "skills": "skills",
            "education": "education",
            "projects": "projects",
            "summary": "summary",
            "name": "name",
            "location": "location",
            "job_preferences": "job_preferences",
            "remote_preference": "job_preferences",
            "notice_period": "job_preferences",
            "willing_to_relocate": "job_preferences"
        }

        for field in allowed_fields:
            mapped_field = field_mapping.get(field, field)

            if mapped_field in profile_data:
                value = profile_data[mapped_field]

                # Handle job_preferences sub-fields
                if mapped_field == "job_preferences" and value:
                    if field == "remote_preference":
                        filtered["remote_preference"] = value.get("remote_preference", "")
                    elif field == "notice_period":
                        filtered["notice_period"] = value.get("notice_period", "")
                    elif field == "willing_to_relocate":
                        filtered["willing_to_relocate"] = value.get("willing_to_relocate", False)
                    else:
                        filtered[mapped_field] = value
                else:
                    filtered[mapped_field] = value

        return filtered

    def _extract_relevant_facts(
        self,
        question: str,
        filtered_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Use LLM to extract most relevant facts for the question"""

        prompt = f"""Given this recruiter question and candidate profile data, extract ONLY the facts directly relevant to answering the question.

Question: "{question}"

Available Profile Data:
{self._format_profile_data(filtered_data)}

Extract and return a JSON object with relevant facts. Only include information that directly helps answer the question.
Be precise and factual. Do not infer or add any information not present in the data.

Return format:
{{
    "relevant_facts": [
        {{"category": "experience/skills/education/etc", "fact": "specific fact from data"}}
    ],
    "summary": "brief summary of available relevant information"
}}

JSON:"""

        result = self.llm.generate_json(prompt)

        if not result:
            # Fallback: return filtered data as-is
            return {"raw_data": filtered_data, "relevant_facts": [], "summary": ""}

        # Add the source data for verification
        result["source_data"] = filtered_data

        return result

    def _format_profile_data(self, data: Dict[str, Any]) -> str:
        """Format profile data for LLM prompt"""
        formatted = []

        for key, value in data.items():
            if isinstance(value, list):
                if value and isinstance(value[0], dict):
                    # List of dicts (experience, education, projects)
                    formatted.append(f"\n{key.upper()}:")
                    for i, item in enumerate(value, 1):
                        formatted.append(f"  {i}. {self._format_dict(item)}")
                else:
                    # Simple list (skills)
                    formatted.append(f"{key.upper()}: {', '.join(str(v) for v in value)}")
            elif isinstance(value, dict):
                formatted.append(f"{key.upper()}: {self._format_dict(value)}")
            else:
                formatted.append(f"{key.upper()}: {value}")

        return '\n'.join(formatted)

    def _format_dict(self, d: Dict) -> str:
        """Format a dict as a readable string"""
        parts = []
        for k, v in d.items():
            if v and v != "":
                if isinstance(v, list):
                    v = ', '.join(str(i) for i in v)
                parts.append(f"{k}: {v}")
        return ' | '.join(parts)

    def _compute_gci(
        self,
        question: str,
        grounding_packet: Dict[str, Any]
    ) -> float:
        """
        Compute Grounding Coverage Index

        This measures how well the available data can answer the question
        """
        relevant_facts = grounding_packet.get("relevant_facts", [])
        source_data = grounding_packet.get("source_data", {})

        # If no relevant facts extracted, low coverage
        if not relevant_facts and not source_data:
            return 0.0

        # Use LLM to estimate coverage
        prompt = f"""Rate how well the available facts can answer this question on a scale of 0.0 to 1.0.

Question: "{question}"

Available Facts:
{self._format_facts(grounding_packet)}

Rating criteria:
- 1.0: Complete information available to fully answer the question
- 0.7-0.9: Good coverage, can provide a substantial answer
- 0.4-0.6: Partial coverage, can provide a limited answer
- 0.1-0.3: Minimal relevant information
- 0.0: No relevant information

Return only a JSON object:
{{"coverage_score": 0.X, "reason": "brief explanation"}}

JSON:"""

        result = self.llm.generate_json(prompt)

        if result and "coverage_score" in result:
            score = float(result["coverage_score"])
            return max(0.0, min(1.0, score))

        # Fallback: estimate based on fact count
        fact_count = len(relevant_facts)
        if fact_count >= 3:
            return 0.8
        elif fact_count >= 1:
            return 0.5
        elif source_data:
            return 0.3
        else:
            return 0.0

    def _format_facts(self, grounding_packet: Dict[str, Any]) -> str:
        """Format facts for display"""
        lines = []

        for fact in grounding_packet.get("relevant_facts", []):
            lines.append(f"- [{fact.get('category', 'general')}] {fact.get('fact', '')}")

        if grounding_packet.get("summary"):
            lines.append(f"\nSummary: {grounding_packet['summary']}")

        return '\n'.join(lines) if lines else "No specific facts extracted"
