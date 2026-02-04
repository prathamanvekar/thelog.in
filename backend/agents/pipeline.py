"""
Agent Pipeline - Orchestrates all agents
"""

from typing import Dict, Any, Optional
from dataclasses import dataclass

from ..database.db import Database
from ..database.models import CandidateProfile
from ..services.policy_service import PolicyService
from ..services.interaction_service import InteractionService
from ..services.trustworthiness_service import TrustworthinessService
from .router_policy_agent import RouterPolicyAgent
from .grounding_agent import GroundingAgent
from .answer_composer_agent import AnswerComposerAgent
from .output_verification_agent import OutputVerificationAgent


@dataclass
class PipelineResult:
    """Result of pipeline execution"""
    question: str
    policy_decision: str
    policy_reason: str
    grounding_packet: Dict[str, Any]
    gci_score: float
    generated_answer: str
    verification_result: str
    verification_issues: list
    final_response: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "question": self.question,
            "policy_decision": self.policy_decision,
            "policy_reason": self.policy_reason,
            "gci_score": self.gci_score,
            "verification_result": self.verification_result,
            "verification_issues": self.verification_issues,
            "final_response": self.final_response
        }


class AgentPipeline:
    """
    Multi-Agent Pipeline for processing recruiter questions

    Flow:
    1. Router & Policy Agent - Check privacy policies
    2. Grounding Agent - Extract relevant facts, compute GCI
    3. Answer Composer Agent - Generate response
    4. Output Verification Agent - Verify and finalize
    """

    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self.policy_service = PolicyService(self.db)
        self.interaction_service = InteractionService(self.db)
        self.trustworthiness_service = TrustworthinessService(self.db)

        # Initialize agents
        self.router_agent = RouterPolicyAgent(self.policy_service)
        self.grounding_agent = GroundingAgent()
        self.composer_agent = AnswerComposerAgent()
        self.verification_agent = OutputVerificationAgent()

    def process_question(
        self,
        profile_id: int,
        question: str
    ) -> PipelineResult:
        """
        Process a recruiter question through the full pipeline

        Returns PipelineResult with all intermediate and final outputs
        """
        # Get profile data
        profile = self.db.get_profile_by_id(profile_id)
        if not profile:
            return PipelineResult(
                question=question,
                policy_decision="ERROR",
                policy_reason="Profile not found",
                grounding_packet={},
                gci_score=0.0,
                generated_answer="",
                verification_result="FAIL",
                verification_issues=["Profile not found"],
                final_response="Unable to process request. Profile not found."
            )

        profile_data = profile.to_dict()

        # Step 1: Router & Policy Agent
        policy_decision, allowed_fields, policy_reason = self.router_agent.evaluate(
            profile_id, question
        )

        # If completely blocked, return early
        if policy_decision == "BLOCK":
            result = PipelineResult(
                question=question,
                policy_decision=policy_decision,
                policy_reason=policy_reason,
                grounding_packet={},
                gci_score=0.0,
                generated_answer="",
                verification_result="PASS",
                verification_issues=[],
                final_response="The candidate has chosen not to disclose this information."
            )
            self._log_interaction(profile_id, result)
            return result

        # Step 2: Grounding Agent
        grounding_packet, gci_score = self.grounding_agent.extract_grounding(
            question, profile_data, allowed_fields
        )

        # Step 3: Answer Composer Agent
        generated_answer = self.composer_agent.compose(
            question=question,
            grounding_packet=grounding_packet,
            gci_score=gci_score,
            policy_decision=policy_decision,
            policy_reason=policy_reason
        )

        # Step 4: Output Verification Agent
        blocked_fields = [f for f in self.router_agent.analyze_question(question).get("relevant_fields", [])
                        if f not in allowed_fields]

        verification_result, verification_issues, final_response = self.verification_agent.verify(
            answer=generated_answer,
            grounding_packet=grounding_packet,
            policy_decision=policy_decision,
            blocked_fields=blocked_fields
        )

        # Build result
        result = PipelineResult(
            question=question,
            policy_decision=policy_decision,
            policy_reason=policy_reason,
            grounding_packet=grounding_packet,
            gci_score=gci_score,
            generated_answer=generated_answer,
            verification_result=verification_result,
            verification_issues=verification_issues,
            final_response=final_response
        )

        # Log interaction
        self._log_interaction(profile_id, result)

        return result

    def _log_interaction(self, profile_id: int, result: PipelineResult):
        """Log the interaction for audit"""
        self.interaction_service.log_interaction(
            profile_id=profile_id,
            recruiter_question=result.question,
            policy_decision=result.policy_decision,
            grounding_packet=result.grounding_packet,
            gci_score=result.gci_score,
            generated_answer=result.generated_answer,
            verification_result=result.verification_result,
            final_response=result.final_response
        )

    def get_profile_with_trust_score(self, profile_id: int) -> Dict[str, Any]:
        """Get profile with trustworthiness score"""
        profile = self.db.get_profile_by_id(profile_id)
        if not profile:
            return {}

        # Get or compute trust score
        trust_score = self.trustworthiness_service.get_score(profile_id)
        if not trust_score:
            trust_score = self.trustworthiness_service.compute_score(profile_id)

        return {
            "profile": profile.to_dict(),
            "trustworthiness": trust_score.to_dict() if trust_score else None
        }

    def refresh_trust_score(self, profile_id: int) -> Dict[str, Any]:
        """Refresh and return trust score"""
        trust_score = self.trustworthiness_service.refresh_score(profile_id)
        return trust_score.to_dict()
