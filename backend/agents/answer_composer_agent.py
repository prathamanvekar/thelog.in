"""
Answer Composer Agent
Generates responses strictly from grounding packet
"""

from typing import Dict, Any, Optional
from ..utils.llm_client import LLMClient
from ..config import GCI_LOW_THRESHOLD


class AnswerComposerAgent:
    """
    Agent that composes answers from grounding packet

    Input:
    - Grounding packet
    - GCI score
    - Original question

    Output:
    - Generated answer (or fallback)
    """

    FALLBACK_RESPONSES = {
        "no_info": "This information is not available in the candidate's profile.",
        "blocked": "The candidate has chosen not to disclose this information.",
        "partial": "Only limited information is available about this topic.",
        "low_coverage": "The candidate's profile does not contain sufficient information to answer this question."
    }

    def __init__(self):
        self.llm = LLMClient()

    def compose(
        self,
        question: str,
        grounding_packet: Dict[str, Any],
        gci_score: float,
        policy_decision: str,
        policy_reason: str = ""
    ) -> str:
        """
        Compose an answer from the grounding packet

        Returns the generated answer or a fallback response
        """
        # Handle blocked policy
        if policy_decision == "BLOCK":
            return self.FALLBACK_RESPONSES["blocked"]

        # Handle low coverage
        if gci_score < GCI_LOW_THRESHOLD:
            return self.FALLBACK_RESPONSES["low_coverage"]

        # Check if we have any relevant facts
        relevant_facts = grounding_packet.get("relevant_facts", [])
        source_data = grounding_packet.get("source_data", {})

        if not relevant_facts and not source_data:
            return self.FALLBACK_RESPONSES["no_info"]

        # Generate answer using LLM
        answer = self._generate_answer(question, grounding_packet, policy_decision)

        return answer

    def _generate_answer(
        self,
        question: str,
        grounding_packet: Dict[str, Any],
        policy_decision: str
    ) -> str:
        """Generate an answer using LLM"""

        system_prompt = """You are an AI assistant representing a job candidate's profile.

CRITICAL RULES:
1. ONLY use information explicitly provided in the grounding packet
2. NEVER infer, assume, or fabricate any information
3. If asked about something not in the data, say the information is not available
4. Speak in third person about "the candidate"
5. Be professional and concise
6. Do not reveal information that was not provided to you"""

        facts_text = self._format_grounding(grounding_packet)

        prompt = f"""Answer this recruiter question about a candidate using ONLY the provided facts.

Question: "{question}"

Available Information:
{facts_text}

Policy Note: {"Full information available" if policy_decision == "ALLOW" else "Some information may be restricted"}

Generate a professional, accurate response using only the facts provided.
If the available information doesn't fully answer the question, acknowledge the limitation.

Response:"""

        response = self.llm.generate(prompt, system_prompt, temperature=0.3)

        if not response:
            return self.FALLBACK_RESPONSES["no_info"]

        return response.strip()

    def _format_grounding(self, grounding_packet: Dict[str, Any]) -> str:
        """Format grounding packet for the prompt"""
        lines = []

        # Add relevant facts
        for fact in grounding_packet.get("relevant_facts", []):
            lines.append(f"• [{fact.get('category', 'info')}] {fact.get('fact', '')}")

        # Add summary if available
        if grounding_packet.get("summary"):
            lines.append(f"\nSummary: {grounding_packet['summary']}")

        # Add raw source data if available and no facts extracted
        source_data = grounding_packet.get("source_data", {})
        if source_data and not grounding_packet.get("relevant_facts"):
            lines.append("\nProfile Data:")
            for key, value in source_data.items():
                if value:
                    lines.append(f"• {key}: {self._summarize_value(value)}")

        return '\n'.join(lines) if lines else "No specific information available"

    def _summarize_value(self, value: Any) -> str:
        """Summarize a value for display"""
        if isinstance(value, list):
            if len(value) == 0:
                return "None listed"
            elif isinstance(value[0], dict):
                # List of experiences/education/projects
                summaries = []
                for item in value[:3]:  # Limit to 3
                    if "company" in item:
                        summaries.append(f"{item.get('title', '')} at {item.get('company', '')}")
                    elif "institution" in item:
                        summaries.append(f"{item.get('degree', '')} from {item.get('institution', '')}")
                    elif "name" in item:
                        summaries.append(item.get("name", ""))
                return "; ".join(summaries)
            else:
                return ", ".join(str(v) for v in value[:10])
        elif isinstance(value, dict):
            return ", ".join(f"{k}: {v}" for k, v in value.items() if v)
        else:
            return str(value)

    def generate_partial_answer(
        self,
        question: str,
        grounding_packet: Dict[str, Any],
        blocked_aspects: list
    ) -> str:
        """Generate a partial answer when some information is blocked"""

        system_prompt = """You are an AI assistant representing a job candidate's profile.
Only use provided information. Some topics are restricted and cannot be discussed."""

        prompt = f"""Answer this question with available information. Note that some aspects are restricted.

Question: "{question}"

Available Information:
{self._format_grounding(grounding_packet)}

Restricted Topics (do not discuss): {', '.join(blocked_aspects)}

Generate a helpful response using only available, unrestricted information.
Politely note if the question touches on restricted topics.

Response:"""

        response = self.llm.generate(prompt, system_prompt, temperature=0.3)

        if not response:
            return self.FALLBACK_RESPONSES["partial"]

        return response.strip()
