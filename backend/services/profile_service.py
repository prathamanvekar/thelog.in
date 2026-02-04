"""
Profile Service - Manages candidate profiles
"""

import uuid
import re
from typing import List, Optional
from datetime import datetime

from ..database.db import Database
from ..database.models import CandidateProfile, LinkedProfile
from ..utils.url_validator import URLValidator


class ProfileService:
    """Service for managing candidate profiles"""

    def __init__(self, db: Optional[Database] = None):
        self.db = db or Database()

    def generate_slug(self, name: str) -> str:
        """Generate a unique slug from name"""
        # Create base slug from name
        base_slug = re.sub(r'[^\w\s-]', '', name.lower())
        base_slug = re.sub(r'[-\s]+', '-', base_slug).strip('-')

        if not base_slug:
            base_slug = "profile"

        # Add random suffix for uniqueness
        suffix = uuid.uuid4().hex[:8]
        slug = f"{base_slug}-{suffix}"

        return slug

    def create_profile(self, profile: CandidateProfile) -> int:
        """Create a new candidate profile"""
        if not profile.slug:
            profile.slug = self.generate_slug(profile.name)

        return self.db.create_profile(profile)

    def get_profile(self, profile_id: int) -> Optional[CandidateProfile]:
        """Get profile by ID"""
        return self.db.get_profile_by_id(profile_id)

    def get_profile_by_slug(self, slug: str) -> Optional[CandidateProfile]:
        """Get profile by slug"""
        return self.db.get_profile_by_slug(slug)

    def get_all_profiles(self) -> List[CandidateProfile]:
        """Get all profiles"""
        return self.db.get_all_profiles()

    def update_profile(self, profile: CandidateProfile) -> bool:
        """Update a profile"""
        return self.db.update_profile(profile)

    def delete_profile(self, profile_id: int) -> bool:
        """Delete a profile"""
        return self.db.delete_profile(profile_id)

    def add_linked_profile(
        self,
        profile_id: int,
        platform: str,
        url: str,
        validate: bool = True
    ) -> Optional[LinkedProfile]:
        """Add a linked profile (LinkedIn, GitHub, Portfolio)"""
        linked = LinkedProfile(
            profile_id=profile_id,
            platform=platform.lower(),
            url=url
        )

        if validate:
            # Validate and extract info based on platform
            if platform.lower() == "linkedin":
                is_valid, name, keywords = URLValidator.validate_linkedin(url)
            elif platform.lower() == "github":
                is_valid, name, keywords = URLValidator.validate_github(url)
            else:
                is_valid, name, keywords = URLValidator.validate_portfolio(url)

            linked.is_reachable = is_valid
            linked.last_checked = datetime.now().isoformat()
            linked.extracted_name = name or ""
            linked.extracted_keywords = keywords

        self.db.add_linked_profile(linked)
        return linked

    def get_linked_profiles(self, profile_id: int) -> List[LinkedProfile]:
        """Get all linked profiles"""
        return self.db.get_linked_profiles(profile_id)

    def refresh_linked_profile(self, profile_id: int, platform: str) -> Optional[LinkedProfile]:
        """Refresh a linked profile's validation"""
        linked_profiles = self.db.get_linked_profiles(profile_id)

        for linked in linked_profiles:
            if linked.platform == platform.lower():
                return self.add_linked_profile(
                    profile_id,
                    platform,
                    linked.url,
                    validate=True
                )

        return None

    def verify_email(self, profile_id: int) -> bool:
        """Mark email as verified (OTP simulation)"""
        profile = self.get_profile(profile_id)
        if profile:
            profile.email_verified = True
            return self.update_profile(profile)
        return False

    def get_profile_json(self, profile_id: int) -> dict:
        """Get profile as structured JSON for agents"""
        profile = self.get_profile(profile_id)
        if not profile:
            return {}
        return profile.to_dict()
