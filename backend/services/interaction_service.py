"""
Interaction Service - Logs and manages interactions
"""

from typing import List, Optional, Dict, Any
from datetime import datetime

from ..database.db import Database
from ..database.models import Interaction


class InteractionService:
    """Service for managing recruiter-profile interactions"""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()

    def log_interaction(
        self,
        profile_id: int,
        recruiter_question: str,
        policy_decision: str,
        grounding_packet: Dict[str, Any],
        gci_score: float,
        generated_answer: str,
        verification_result: str,
        final_response: str
    ) -> int:
        """Log an interaction"""
        interaction = Interaction(
            profile_id=profile_id,
            recruiter_question=recruiter_question,
            policy_decision=policy_decision,
            grounding_packet=grounding_packet,
            gci_score=gci_score,
            generated_answer=generated_answer,
            verification_result=verification_result,
            final_response=final_response
        )
        return self.db.log_interaction(interaction)

    def get_interactions(self, profile_id: int, limit: int = 50) -> List[Interaction]:
        """Get interactions for a profile"""
        return self.db.get_interactions(profile_id, limit)

    def get_interaction_stats(self, profile_id: int) -> Dict[str, Any]:
        """Get interaction statistics"""
        return self.db.get_interaction_stats(profile_id)

    def get_recent_questions(self, profile_id: int, limit: int = 10) -> List[str]:
        """Get recent questions for a profile"""
        interactions = self.get_interactions(profile_id, limit)
        return [i.recruiter_question for i in interactions]

    def get_interaction_summary(self, profile_id: int) -> Dict[str, Any]:
        """Get a summary of interactions"""
        stats = self.get_interaction_stats(profile_id)
        interactions = self.get_interactions(profile_id, 10)

        return {
            "total_interactions": stats.get("total_interactions", 0),
            "avg_gci": round(stats.get("avg_gci", 0), 2),
            "verifier_pass_rate": round(stats.get("verifier_pass_rate", 1.0), 2),
            "recent_questions": [
                {
                    "question": i.recruiter_question,
                    "policy_decision": i.policy_decision,
                    "gci_score": round(i.gci_score, 2),
                    "verification_result": i.verification_result,
                    "created_at": i.created_at
                }
                for i in interactions
            ]
        }
