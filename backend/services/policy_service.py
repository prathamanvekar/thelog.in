"""
Policy Service - Manages privacy policies (PDL)
"""

from typing import List, Dict, Optional
from ..database.db import Database
from ..database.models import PrivacyPolicy
from ..config import (
    POLICY_ALLOW,
    POLICY_BLOCK,
    POLICY_PARTIAL,
    DEFAULT_BLOCKED_FIELDS,
    DEFAULT_PARTIAL_FIELDS
)


class PolicyService:
    """Service for managing privacy policies"""

    # Field categories and their default policies
    FIELD_CATEGORIES = {
        "personal": ["name", "email", "phone", "location", "address"],
        "financial": ["salary", "expected_salary", "compensation"],
        "professional": ["summary", "skills", "experience", "education", "projects"],
        "preferences": ["job_preferences", "remote_preference", "notice_period", "willing_to_relocate"],
        "sensitive": ["ssn", "id_number", "date_of_birth", "age"]
    }

    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()

    def initialize_default_policies(self, profile_id: int) -> List[PrivacyPolicy]:
        """Initialize default privacy policies for a profile"""
        policies = []

        # Set blocked fields
        for field in DEFAULT_BLOCKED_FIELDS:
            policy = PrivacyPolicy(
                profile_id=profile_id,
                field_name=field,
                policy_type=POLICY_BLOCK
            )
            self.db.set_policy(policy)
            policies.append(policy)

        # Set partial fields
        for field in DEFAULT_PARTIAL_FIELDS:
            policy = PrivacyPolicy(
                profile_id=profile_id,
                field_name=field,
                policy_type=POLICY_PARTIAL,
                partial_config={"show_domain_only": True}  # For email
            )
            self.db.set_policy(policy)
            policies.append(policy)

        return policies

    def set_policy(
        self,
        profile_id: int,
        field_name: str,
        policy_type: str,
        partial_config: Optional[Dict] = None
    ) -> PrivacyPolicy:
        """Set or update a privacy policy"""
        if policy_type not in [POLICY_ALLOW, POLICY_BLOCK, POLICY_PARTIAL]:
            raise ValueError(f"Invalid policy type: {policy_type}")

        policy = PrivacyPolicy(
            profile_id=profile_id,
            field_name=field_name,
            policy_type=policy_type,
            partial_config=partial_config
        )
        self.db.set_policy(policy)
        return policy

    def get_policies(self, profile_id: int) -> List[PrivacyPolicy]:
        """Get all policies for a profile"""
        return self.db.get_policies(profile_id)

    def get_policy_for_field(self, profile_id: int, field_name: str) -> str:
        """Get policy type for a specific field"""
        policy = self.db.get_policy_for_field(profile_id, field_name)
        if policy:
            return policy.policy_type

        # Default policy based on field category
        if field_name in DEFAULT_BLOCKED_FIELDS:
            return POLICY_BLOCK
        elif field_name in DEFAULT_PARTIAL_FIELDS:
            return POLICY_PARTIAL
        else:
            return POLICY_ALLOW

    def get_policies_dict(self, profile_id: int) -> Dict[str, str]:
        """Get all policies as a dictionary"""
        policies = self.get_policies(profile_id)
        return {p.field_name: p.policy_type for p in policies}

    def check_field_allowed(self, profile_id: int, field_name: str) -> tuple:
        """
        Check if a field is allowed to be disclosed
        Returns: (policy_type, partial_config)
        """
        policy = self.db.get_policy_for_field(profile_id, field_name)

        if policy:
            return policy.policy_type, policy.partial_config

        # Check default blocked/partial
        if field_name in DEFAULT_BLOCKED_FIELDS:
            return POLICY_BLOCK, None
        elif field_name in DEFAULT_PARTIAL_FIELDS:
            return POLICY_PARTIAL, {"show_domain_only": True}

        return POLICY_ALLOW, None

    def delete_policy(self, profile_id: int, field_name: str) -> bool:
        """Delete a policy (revert to default)"""
        return self.db.delete_policy(profile_id, field_name)

    def get_all_field_names(self) -> List[str]:
        """Get all possible field names"""
        fields = []
        for category, field_list in self.FIELD_CATEGORIES.items():
            fields.extend(field_list)
        return fields

    def has_sensitive_protections(self, profile_id: int) -> bool:
        """Check if sensitive fields are properly protected"""
        sensitive_fields = ["salary", "expected_salary", "phone", "address", "ssn", "id_number"]

        for field in sensitive_fields:
            policy_type, _ = self.check_field_allowed(profile_id, field)
            if policy_type == POLICY_ALLOW:
                return False

        return True

    def has_policy_explanations(self, profile_id: int) -> bool:
        """Check if policy explanations are available"""
        # In this implementation, we always have explanations
        return True

    def is_audit_logging_enabled(self, profile_id: int) -> bool:
        """Check if audit logging is enabled"""
        # In this implementation, logging is always enabled
        return True
