"""
Database operations for theLog.in using SQLite
"""

import sqlite3
import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from contextlib import contextmanager
from pathlib import Path

from ..config import DATABASE_PATH
from .models import (
    CandidateProfile,
    Education,
    Experience,
    Project,
    JobPreferences,
    PrivacyPolicy,
    LinkedProfile,
    Interaction,
    TrustworthinessScore
)


class Database:
    def __init__(self, db_path: str = DATABASE_PATH):
        self.db_path = db_path
        Path(db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def get_connection(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

    def _init_db(self):
        """Initialize database schema"""
        schema = """
        CREATE TABLE IF NOT EXISTS candidate_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            slug TEXT UNIQUE NOT NULL,
            name TEXT NOT NULL,
            email TEXT,
            phone TEXT,
            location TEXT,
            summary TEXT,
            skills TEXT,
            education TEXT,
            experience TEXT,
            projects TEXT,
            job_preferences TEXT,
            email_verified INTEGER DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS privacy_policies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            field_name TEXT NOT NULL,
            policy_type TEXT NOT NULL DEFAULT 'ALLOW',
            partial_config TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES candidate_profiles(id) ON DELETE CASCADE,
            UNIQUE(profile_id, field_name)
        );

        CREATE TABLE IF NOT EXISTS linked_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            platform TEXT NOT NULL,
            url TEXT NOT NULL,
            is_reachable INTEGER,
            last_checked TEXT,
            extracted_name TEXT,
            extracted_keywords TEXT,
            FOREIGN KEY (profile_id) REFERENCES candidate_profiles(id) ON DELETE CASCADE,
            UNIQUE(profile_id, platform)
        );

        CREATE TABLE IF NOT EXISTS interactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL,
            recruiter_question TEXT NOT NULL,
            policy_decision TEXT,
            grounding_packet TEXT,
            gci_score REAL,
            generated_answer TEXT,
            verification_result TEXT,
            final_response TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (profile_id) REFERENCES candidate_profiles(id) ON DELETE CASCADE
        );

        CREATE TABLE IF NOT EXISTS trustworthiness_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            profile_id INTEGER NOT NULL UNIQUE,
            total_score REAL,
            trust_band TEXT,
            identity_score REAL,
            consistency_score REAL,
            internal_score REAL,
            transparency_score REAL,
            breakdown TEXT,
            reasons TEXT,
            warnings TEXT,
            last_verified TEXT,
            FOREIGN KEY (profile_id) REFERENCES candidate_profiles(id) ON DELETE CASCADE
        );

        CREATE INDEX IF NOT EXISTS idx_profiles_slug ON candidate_profiles(slug);
        CREATE INDEX IF NOT EXISTS idx_policies_profile ON privacy_policies(profile_id);
        CREATE INDEX IF NOT EXISTS idx_interactions_profile ON interactions(profile_id);
        """

        with self.get_connection() as conn:
            conn.executescript(schema)

    # ============ Candidate Profile Operations ============

    def create_profile(self, profile: CandidateProfile) -> int:
        """Create a new candidate profile"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO candidate_profiles
                (slug, name, email, phone, location, summary, skills,
                 education, experience, projects, job_preferences, email_verified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                profile.slug,
                profile.name,
                profile.email,
                profile.phone,
                profile.location,
                profile.summary,
                json.dumps(profile.skills),
                json.dumps([e.to_dict() for e in profile.education]),
                json.dumps([e.to_dict() for e in profile.experience]),
                json.dumps([p.to_dict() for p in profile.projects]),
                json.dumps(profile.job_preferences.to_dict()) if profile.job_preferences else None,
                1 if profile.email_verified else 0
            ))
            return cursor.lastrowid

    def get_profile_by_id(self, profile_id: int) -> Optional[CandidateProfile]:
        """Get profile by ID"""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM candidate_profiles WHERE id = ?",
                (profile_id,)
            ).fetchone()

            if row:
                return self._row_to_profile(row)
            return None

    def get_profile_by_slug(self, slug: str) -> Optional[CandidateProfile]:
        """Get profile by slug"""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM candidate_profiles WHERE slug = ?",
                (slug,)
            ).fetchone()

            if row:
                return self._row_to_profile(row)
            return None

    def get_all_profiles(self) -> List[CandidateProfile]:
        """Get all profiles"""
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM candidate_profiles ORDER BY created_at DESC").fetchall()
            return [self._row_to_profile(row) for row in rows]

    def update_profile(self, profile: CandidateProfile) -> bool:
        """Update an existing profile"""
        with self.get_connection() as conn:
            conn.execute("""
                UPDATE candidate_profiles SET
                    name = ?, email = ?, phone = ?, location = ?, summary = ?,
                    skills = ?, education = ?, experience = ?, projects = ?,
                    job_preferences = ?, email_verified = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (
                profile.name,
                profile.email,
                profile.phone,
                profile.location,
                profile.summary,
                json.dumps(profile.skills),
                json.dumps([e.to_dict() for e in profile.education]),
                json.dumps([e.to_dict() for e in profile.experience]),
                json.dumps([p.to_dict() for p in profile.projects]),
                json.dumps(profile.job_preferences.to_dict()) if profile.job_preferences else None,
                1 if profile.email_verified else 0,
                profile.id
            ))
            return True

    def delete_profile(self, profile_id: int) -> bool:
        """Delete a profile"""
        with self.get_connection() as conn:
            conn.execute("DELETE FROM candidate_profiles WHERE id = ?", (profile_id,))
            return True

    def _row_to_profile(self, row: sqlite3.Row) -> CandidateProfile:
        """Convert database row to CandidateProfile"""
        data = dict(row)
        data["skills"] = json.loads(data["skills"]) if data["skills"] else []
        data["education"] = json.loads(data["education"]) if data["education"] else []
        data["experience"] = json.loads(data["experience"]) if data["experience"] else []
        data["projects"] = json.loads(data["projects"]) if data["projects"] else []
        data["job_preferences"] = json.loads(data["job_preferences"]) if data["job_preferences"] else None
        data["email_verified"] = bool(data["email_verified"])
        return CandidateProfile.from_dict(data)

    # ============ Privacy Policy Operations ============

    def set_policy(self, policy: PrivacyPolicy) -> int:
        """Set or update a privacy policy"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT OR REPLACE INTO privacy_policies
                (profile_id, field_name, policy_type, partial_config)
                VALUES (?, ?, ?, ?)
            """, (
                policy.profile_id,
                policy.field_name,
                policy.policy_type,
                json.dumps(policy.partial_config) if policy.partial_config else None
            ))
            return cursor.lastrowid

    def get_policies(self, profile_id: int) -> List[PrivacyPolicy]:
        """Get all policies for a profile"""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM privacy_policies WHERE profile_id = ?",
                (profile_id,)
            ).fetchall()

            policies = []
            for row in rows:
                policy = PrivacyPolicy(
                    id=row["id"],
                    profile_id=row["profile_id"],
                    field_name=row["field_name"],
                    policy_type=row["policy_type"],
                    partial_config=json.loads(row["partial_config"]) if row["partial_config"] else None,
                    created_at=row["created_at"]
                )
                policies.append(policy)
            return policies

    def get_policy_for_field(self, profile_id: int, field_name: str) -> Optional[PrivacyPolicy]:
        """Get policy for a specific field"""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM privacy_policies WHERE profile_id = ? AND field_name = ?",
                (profile_id, field_name)
            ).fetchone()

            if row:
                return PrivacyPolicy(
                    id=row["id"],
                    profile_id=row["profile_id"],
                    field_name=row["field_name"],
                    policy_type=row["policy_type"],
                    partial_config=json.loads(row["partial_config"]) if row["partial_config"] else None,
                    created_at=row["created_at"]
                )
            return None

    def delete_policy(self, profile_id: int, field_name: str) -> bool:
        """Delete a policy"""
        with self.get_connection() as conn:
            conn.execute(
                "DELETE FROM privacy_policies WHERE profile_id = ? AND field_name = ?",
                (profile_id, field_name)
            )
            return True

    # ============ Linked Profile Operations ============

    def add_linked_profile(self, linked: LinkedProfile) -> int:
        """Add or update a linked profile"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT OR REPLACE INTO linked_profiles
                (profile_id, platform, url, is_reachable, last_checked,
                 extracted_name, extracted_keywords)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                linked.profile_id,
                linked.platform,
                linked.url,
                1 if linked.is_reachable else 0 if linked.is_reachable is not None else None,
                linked.last_checked,
                linked.extracted_name,
                json.dumps(linked.extracted_keywords)
            ))
            return cursor.lastrowid

    def get_linked_profiles(self, profile_id: int) -> List[LinkedProfile]:
        """Get all linked profiles"""
        with self.get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM linked_profiles WHERE profile_id = ?",
                (profile_id,)
            ).fetchall()

            linked_profiles = []
            for row in rows:
                lp = LinkedProfile(
                    id=row["id"],
                    profile_id=row["profile_id"],
                    platform=row["platform"],
                    url=row["url"],
                    is_reachable=bool(row["is_reachable"]) if row["is_reachable"] is not None else None,
                    last_checked=row["last_checked"],
                    extracted_name=row["extracted_name"] or "",
                    extracted_keywords=json.loads(row["extracted_keywords"]) if row["extracted_keywords"] else []
                )
                linked_profiles.append(lp)
            return linked_profiles

    # ============ Interaction Operations ============

    def log_interaction(self, interaction: Interaction) -> int:
        """Log an interaction"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO interactions
                (profile_id, recruiter_question, policy_decision, grounding_packet,
                 gci_score, generated_answer, verification_result, final_response)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                interaction.profile_id,
                interaction.recruiter_question,
                interaction.policy_decision,
                json.dumps(interaction.grounding_packet),
                interaction.gci_score,
                interaction.generated_answer,
                interaction.verification_result,
                interaction.final_response
            ))
            return cursor.lastrowid

    def get_interactions(self, profile_id: int, limit: int = 50) -> List[Interaction]:
        """Get interactions for a profile"""
        with self.get_connection() as conn:
            rows = conn.execute(
                """SELECT * FROM interactions WHERE profile_id = ?
                   ORDER BY created_at DESC LIMIT ?""",
                (profile_id, limit)
            ).fetchall()

            interactions = []
            for row in rows:
                interaction = Interaction(
                    id=row["id"],
                    profile_id=row["profile_id"],
                    recruiter_question=row["recruiter_question"],
                    policy_decision=row["policy_decision"],
                    grounding_packet=json.loads(row["grounding_packet"]) if row["grounding_packet"] else {},
                    gci_score=row["gci_score"] or 0.0,
                    generated_answer=row["generated_answer"] or "",
                    verification_result=row["verification_result"] or "",
                    final_response=row["final_response"] or "",
                    created_at=row["created_at"]
                )
                interactions.append(interaction)
            return interactions

    def get_interaction_stats(self, profile_id: int) -> Dict[str, Any]:
        """Get interaction statistics for a profile"""
        with self.get_connection() as conn:
            stats = conn.execute("""
                SELECT
                    COUNT(*) as total_interactions,
                    AVG(gci_score) as avg_gci,
                    SUM(CASE WHEN verification_result = 'PASS' THEN 1 ELSE 0 END) as pass_count,
                    SUM(CASE WHEN verification_result = 'FAIL' THEN 1 ELSE 0 END) as fail_count
                FROM interactions WHERE profile_id = ?
            """, (profile_id,)).fetchone()

            total = stats["total_interactions"] or 0
            pass_count = stats["pass_count"] or 0

            return {
                "total_interactions": total,
                "avg_gci": stats["avg_gci"] or 0.0,
                "pass_count": pass_count,
                "fail_count": stats["fail_count"] or 0,
                "verifier_pass_rate": pass_count / total if total > 0 else 1.0
            }

    # ============ Trustworthiness Score Operations ============

    def save_trustworthiness_score(self, score: TrustworthinessScore) -> int:
        """Save or update trustworthiness score"""
        with self.get_connection() as conn:
            cursor = conn.execute("""
                INSERT OR REPLACE INTO trustworthiness_scores
                (profile_id, total_score, trust_band, identity_score, consistency_score,
                 internal_score, transparency_score, breakdown, reasons, warnings, last_verified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                score.profile_id,
                score.total_score,
                score.trust_band,
                score.identity_score,
                score.consistency_score,
                score.internal_score,
                score.transparency_score,
                json.dumps(score.breakdown),
                json.dumps(score.reasons),
                json.dumps(score.warnings),
                score.last_verified
            ))
            return cursor.lastrowid

    def get_trustworthiness_score(self, profile_id: int) -> Optional[TrustworthinessScore]:
        """Get trustworthiness score for a profile"""
        with self.get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM trustworthiness_scores WHERE profile_id = ?",
                (profile_id,)
            ).fetchone()

            if row:
                return TrustworthinessScore(
                    id=row["id"],
                    profile_id=row["profile_id"],
                    total_score=row["total_score"],
                    trust_band=row["trust_band"],
                    identity_score=row["identity_score"],
                    consistency_score=row["consistency_score"],
                    internal_score=row["internal_score"],
                    transparency_score=row["transparency_score"],
                    breakdown=json.loads(row["breakdown"]) if row["breakdown"] else {},
                    reasons=json.loads(row["reasons"]) if row["reasons"] else [],
                    warnings=json.loads(row["warnings"]) if row["warnings"] else [],
                    last_verified=row["last_verified"]
                )
            return None
