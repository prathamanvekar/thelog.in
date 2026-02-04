"""
Trustworthiness Service - Computes Profile Trustworthiness Score (PTS)
"""

from typing import Dict, List, Optional, Tuple
from datetime import datetime

from ..database.db import Database
from ..database.models import TrustworthinessScore, CandidateProfile, LinkedProfile
from ..services.policy_service import PolicyService
from ..utils.text_utils import TextUtils
from ..config import (
    PTS_IDENTITY_MAX,
    PTS_CONSISTENCY_MAX,
    PTS_INTERNAL_MAX,
    PTS_TRANSPARENCY_MAX,
    TRUST_BAND_HIGH,
    TRUST_BAND_MEDIUM
)


class TrustworthinessService:
    """Service for computing Profile Trustworthiness Score"""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()
        self.policy_service = PolicyService(db)

    def compute_score(self, profile_id: int) -> TrustworthinessScore:
        """Compute the full trustworthiness score for a profile"""
        profile = self.db.get_profile_by_id(profile_id)
        if not profile:
            raise ValueError(f"Profile not found: {profile_id}")

        linked_profiles = self.db.get_linked_profiles(profile_id)
        interaction_stats = self.db.get_interaction_stats(profile_id)

        # Compute each component
        identity_score, identity_breakdown = self._compute_identity_score(
            profile, linked_profiles
        )

        consistency_score, consistency_breakdown, consistency_warnings = self._compute_consistency_score(
            profile, linked_profiles
        )

        internal_score, internal_breakdown = self._compute_internal_score(
            interaction_stats
        )

        transparency_score, transparency_breakdown = self._compute_transparency_score(
            profile_id
        )

        # Total score
        total_score = identity_score + consistency_score + internal_score + transparency_score
        total_score = min(100, max(0, total_score))

        # Determine trust band
        if total_score >= TRUST_BAND_HIGH:
            trust_band = "High"
        elif total_score >= TRUST_BAND_MEDIUM:
            trust_band = "Medium"
        else:
            trust_band = "Low"

        # Compile breakdown
        breakdown = {
            "identity": identity_breakdown,
            "consistency": consistency_breakdown,
            "internal": internal_breakdown,
            "transparency": transparency_breakdown
        }

        # Compile reasons
        reasons = self._compile_reasons(breakdown)
        warnings = consistency_warnings

        # Create score object
        score = TrustworthinessScore(
            profile_id=profile_id,
            total_score=round(total_score, 1),
            trust_band=trust_band,
            identity_score=round(identity_score, 1),
            consistency_score=round(consistency_score, 1),
            internal_score=round(internal_score, 1),
            transparency_score=round(transparency_score, 1),
            breakdown=breakdown,
            reasons=reasons,
            warnings=warnings,
            last_verified=datetime.now().isoformat()
        )

        # Save to database
        self.db.save_trustworthiness_score(score)

        return score

    def _compute_identity_score(
        self,
        profile: CandidateProfile,
        linked_profiles: List[LinkedProfile]
    ) -> Tuple[float, Dict]:
        """
        Compute Identity & Link Verification score (0-30)
        - LinkedIn reachable: +15
        - GitHub reachable: +8
        - Portfolio reachable: +5
        - Email verified: +2
        """
        score = 0
        breakdown = {
            "linkedin_reachable": False,
            "github_reachable": False,
            "portfolio_reachable": False,
            "email_verified": profile.email_verified
        }

        for linked in linked_profiles:
            if linked.platform == "linkedin" and linked.is_reachable:
                score += 15
                breakdown["linkedin_reachable"] = True
            elif linked.platform == "github" and linked.is_reachable:
                score += 8
                breakdown["github_reachable"] = True
            elif linked.platform == "portfolio" and linked.is_reachable:
                score += 5
                breakdown["portfolio_reachable"] = True

        if profile.email_verified:
            score += 2

        # Cap at max
        score = min(score, PTS_IDENTITY_MAX)
        breakdown["score"] = score
        breakdown["max"] = PTS_IDENTITY_MAX

        return score, breakdown

    def _compute_consistency_score(
        self,
        profile: CandidateProfile,
        linked_profiles: List[LinkedProfile]
    ) -> Tuple[float, Dict, List[str]]:
        """
        Compute Cross-Profile Consistency score (0-30)
        - Name similarity: +10 (strong), +6 (medium), +2 (weak)
        - Employer overlap: +10 (>=60%), +6 (30-59%), +2 (<30%)
        - Skills overlap: +6 (>=50%), +4 (25-49%), +2 (<25%)
        - No timeline conflicts: +4
        """
        score = 0
        breakdown = {
            "name_similarity": 0,
            "employer_overlap": 0,
            "skills_overlap": 0,
            "timeline_conflict": False
        }
        warnings = []

        # Collect external data
        external_names = []
        external_keywords = []

        for linked in linked_profiles:
            if linked.extracted_name:
                external_names.append(linked.extracted_name)
            if linked.extracted_keywords:
                external_keywords.extend(linked.extracted_keywords)

        # Name similarity
        if external_names:
            max_similarity = 0
            for ext_name in external_names:
                sim = TextUtils.name_similarity(profile.name, ext_name)
                max_similarity = max(max_similarity, sim)

            breakdown["name_similarity"] = max_similarity

            if max_similarity >= 0.90:
                score += 10
            elif max_similarity >= 0.75:
                score += 6
            else:
                score += 2
                if max_similarity < 0.5:
                    warnings.append("Low name match across profiles")
        else:
            # No external names to compare
            score += 2

        # Employer overlap
        profile_employers = [exp.company for exp in profile.experience if exp.company]

        if profile_employers and external_keywords:
            employer_overlap = TextUtils.employer_overlap(profile_employers, external_keywords)
            breakdown["employer_overlap"] = employer_overlap

            if employer_overlap >= 0.60:
                score += 10
            elif employer_overlap >= 0.30:
                score += 6
            else:
                score += 2
                if employer_overlap < 0.2:
                    warnings.append("Low employer overlap with public profiles")
        else:
            score += 2

        # Skills overlap
        if profile.skills and external_keywords:
            skills_overlap = TextUtils.skills_overlap(profile.skills, external_keywords)
            breakdown["skills_overlap"] = skills_overlap

            if skills_overlap >= 0.50:
                score += 6
            elif skills_overlap >= 0.25:
                score += 4
            else:
                score += 2
        else:
            score += 2

        # Timeline conflicts
        if profile.experience and external_keywords:
            external_years = TextUtils.extract_years(' '.join(external_keywords))
            has_conflict, conflict_msgs = TextUtils.check_timeline_conflicts(
                [exp.to_dict() for exp in profile.experience],
                external_years
            )

            breakdown["timeline_conflict"] = has_conflict

            if not has_conflict:
                score += 4
            else:
                warnings.extend(conflict_msgs)
        else:
            score += 4

        # Cap at max
        score = min(score, PTS_CONSISTENCY_MAX)
        breakdown["score"] = score
        breakdown["max"] = PTS_CONSISTENCY_MAX

        return score, breakdown, warnings

    def _compute_internal_score(
        self,
        interaction_stats: Dict
    ) -> Tuple[float, Dict]:
        """
        Compute Internal Reliability score (0-25)
        - Avg GCI >= 0.85: +15, 0.70-0.84: +10, 0.50-0.69: +6, <0.50: +2
        - Verifier pass rate >= 0.90: +10, 0.75-0.89: +6, <0.75: +2
        """
        score = 0
        avg_gci = interaction_stats.get("avg_gci", 0)
        verifier_pass_rate = interaction_stats.get("verifier_pass_rate", 1.0)

        breakdown = {
            "avg_gci": avg_gci,
            "verifier_pass_rate": verifier_pass_rate,
            "total_interactions": interaction_stats.get("total_interactions", 0)
        }

        # GCI score
        if avg_gci >= 0.85:
            score += 15
        elif avg_gci >= 0.70:
            score += 10
        elif avg_gci >= 0.50:
            score += 6
        else:
            # If no interactions, give benefit of doubt
            if interaction_stats.get("total_interactions", 0) == 0:
                score += 10
            else:
                score += 2

        # Verifier pass rate
        if verifier_pass_rate >= 0.90:
            score += 10
        elif verifier_pass_rate >= 0.75:
            score += 6
        else:
            score += 2

        # Cap at max
        score = min(score, PTS_INTERNAL_MAX)
        breakdown["score"] = score
        breakdown["max"] = PTS_INTERNAL_MAX

        return score, breakdown

    def _compute_transparency_score(
        self,
        profile_id: int
    ) -> Tuple[float, Dict]:
        """
        Compute Policy & Audit Transparency score (0-15)
        - Sensitive fields protected: +8
        - Policy explanations available: +4
        - Audit logging enabled: +3
        """
        score = 0
        breakdown = {
            "sensitive_protected": False,
            "policy_explanations": False,
            "audit_logging": False
        }

        # Check sensitive field protections
        if self.policy_service.has_sensitive_protections(profile_id):
            score += 8
            breakdown["sensitive_protected"] = True

        # Check policy explanations
        if self.policy_service.has_policy_explanations(profile_id):
            score += 4
            breakdown["policy_explanations"] = True

        # Check audit logging
        if self.policy_service.is_audit_logging_enabled(profile_id):
            score += 3
            breakdown["audit_logging"] = True

        # Cap at max
        score = min(score, PTS_TRANSPARENCY_MAX)
        breakdown["score"] = score
        breakdown["max"] = PTS_TRANSPARENCY_MAX

        return score, breakdown

    def _compile_reasons(self, breakdown: Dict) -> List[str]:
        """Compile human-readable reasons from breakdown"""
        reasons = []

        # Identity reasons
        identity = breakdown.get("identity", {})
        if identity.get("linkedin_reachable"):
            reasons.append("LinkedIn profile verified and reachable")
        if identity.get("github_reachable"):
            reasons.append("GitHub profile verified and reachable")
        if identity.get("email_verified"):
            reasons.append("Email address verified")

        # Consistency reasons
        consistency = breakdown.get("consistency", {})
        name_sim = consistency.get("name_similarity", 0)
        if name_sim >= 0.90:
            reasons.append("Strong name match across profiles")
        elif name_sim >= 0.75:
            reasons.append("Good name consistency across profiles")

        emp_overlap = consistency.get("employer_overlap", 0)
        if emp_overlap >= 0.60:
            reasons.append("High employer overlap with public profiles")

        # Internal reasons
        internal = breakdown.get("internal", {})
        if internal.get("avg_gci", 0) >= 0.85:
            reasons.append("High grounding coverage in responses")
        if internal.get("verifier_pass_rate", 0) >= 0.90:
            reasons.append("Excellent response verification rate")

        # Transparency reasons
        transparency = breakdown.get("transparency", {})
        if transparency.get("sensitive_protected"):
            reasons.append("Sensitive information properly protected")
        if transparency.get("audit_logging"):
            reasons.append("Full audit logging enabled")

        return reasons[:5]  # Return top 5 reasons

    def get_score(self, profile_id: int) -> Optional[TrustworthinessScore]:
        """Get cached trustworthiness score"""
        return self.db.get_trustworthiness_score(profile_id)

    def refresh_score(self, profile_id: int) -> TrustworthinessScore:
        """Refresh and return trustworthiness score"""
        return self.compute_score(profile_id)
