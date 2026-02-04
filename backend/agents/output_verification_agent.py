"""
Output Verification Agent
Verifies response compliance with grounding and policy
"""

from typing import Dict, Any, Tuple, List
from ..utils.llm_client import LLMClient
from ..config import POLICY_BLOCK


class OutputVerificationAgent:
    """
    Agent that verifies generated answers

    Input:
    - Final answer
    - Grounding packet
    - Policy decision

    Output:
    - Verification result (PASS/FAIL)
    - Issues found
    - Corrected answer if needed
    """

    SAFE_FALLBACK = "This information is not available in the candidate's profile."

    def __init__(self):
        self.llm = LLMClient()

    def verify(
        self,
        answer: str,
        grounding_packet: Dict[str, Any],
        policy_decision: str,
        blocked_fields: List[str] = None
    ) -> Tuple[str, List[str], str]:
        """
        Verify the generated answer

        Returns:
        - result: "PASS" or "FAIL"
        - issues: list of issues found
        - final_answer: verified answer or fallback
        """
        blocked_fields = blocked_fields or []
        issues = []

        # Check 1: Policy compliance
        if not self._check_policy_compliance(answer, policy_decision, blocked_fields):
            issues.append("Policy violation: Answer may reveal restricted information")

        # Check 2: Grounding compliance
        grounding_issues = self._check_grounding_compliance(answer, grounding_packet)
        issues.extend(grounding_issues)

        # Check 3: Hallucination check
        hallucination_issues = self._check_hallucination(answer, grounding_packet)
        issues.extend(hallucination_issues)

        # Determine result
        if issues:
            result = "FAIL"
            # Return safe fallback for policy violations
            if any("Policy violation" in issue for issue in issues):
                final_answer = self.SAFE_FALLBACK
            else:
                # For grounding issues, try to use original answer with warning
                final_answer = answer
        else:
            result = "PASS"
            final_answer = answer

        return result, issues, final_answer

    def _check_policy_compliance(
        self,
        answer: str,
        policy_decision: str,
        blocked_fields: List[str]
    ) -> bool:
        """Check if answer complies with policy"""
        if policy_decision == POLICY_BLOCK:
            # Answer should be a fallback
            fallback_phrases = [
                "not available",
                "not disclosed",
                "confidential",
                "chosen not to",
                "restricted",
                "cannot share"
            ]
            return any(phrase in answer.lower() for phrase in fallback_phrases)

        # Check for blocked field mentions
        answer_lower = answer.lower()
        sensitive_patterns = {
            "salary": ["$", "salary", "compensation", "per annum", "lpa", "ctc"],
            "phone": ["phone", "call me at", "reach me at", "number"],
            "address": ["street", "apartment", "apt", "zip code"],
        }

        for field in blocked_fields:
            if field in sensitive_patterns:
                for pattern in sensitive_patterns[field]:
                    if pattern in answer_lower:
                        return False

        return True

    def _check_grounding_compliance(
        self,
        answer: str,
        grounding_packet: Dict[str, Any]
    ) -> List[str]:
        """Check if answer is grounded in the provided data"""
        issues = []

        relevant_facts = grounding_packet.get("relevant_facts", [])
        source_data = grounding_packet.get("source_data", {})

        if not relevant_facts and not source_data:
            # If no grounding data, answer should be a fallback
            if "not available" not in answer.lower() and "don't have" not in answer.lower():
                issues.append("Answer provided without sufficient grounding data")

        return issues

    def _check_hallucination(
        self,
        answer: str,
        grounding_packet: Dict[str, Any]
    ) -> List[str]:
        """Check for potential hallucinations"""
        issues = []

        # Use LLM to check for claims not in grounding
        source_data = grounding_packet.get("source_data", {})
        relevant_facts = grounding_packet.get("relevant_facts", [])

        if not source_data and not relevant_facts:
            return issues

        prompt = f"""Verify if this answer contains any information NOT present in the source data.

Answer to verify:
"{answer}"

Source Data:
{self._format_source_data(source_data)}

Extracted Facts:
{self._format_facts(relevant_facts)}

Return JSON:
{{
    "has_unsupported_claims": true/false,
    "unsupported_claims": ["list of claims not in source data"],
    "severity": "none/low/high"
}}

JSON:"""

        result = self.llm.generate_json(prompt)

        if result:
            if result.get("has_unsupported_claims") and result.get("severity") == "high":
                claims = result.get("unsupported_claims", [])
                for claim in claims[:2]:  # Limit to 2 issues
                    issues.append(f"Potential unsupported claim: {claim}")

        return issues

    def _format_source_data(self, source_data: Dict) -> str:
        """Format source data for verification prompt"""
        lines = []
        for key, value in source_data.items():
            if value:
                if isinstance(value, list):
                    lines.append(f"{key}: {len(value)} items")
                    for i, item in enumerate(value[:2]):
                        if isinstance(item, dict):
                            lines.append(f"  - {item}")
                else:
                    lines.append(f"{key}: {value}")
        return '\n'.join(lines) if lines else "No source data"

    def _format_facts(self, facts: List[Dict]) -> str:
        """Format facts for verification prompt"""
        if not facts:
            return "No facts extracted"
        return '\n'.join(f"- {f.get('fact', '')}" for f in facts)

    def enforce_fallback(self, issues: List[str]) -> str:
        """Determine appropriate fallback based on issues"""
        if any("Policy violation" in issue for issue in issues):
            return "The candidate has chosen not to disclose this information."
        elif any("grounding" in issue.lower() for issue in issues):
            return "This information is not available in the candidate's profile."
        else:
            return self.SAFE_FALLBACK
