"""
Text processing utilities
"""

import re
from typing import List, Set, Tuple
from fuzzywuzzy import fuzz


class TextUtils:
    """Text processing utilities for profile comparison"""

    @staticmethod
    def normalize_name(name: str) -> str:
        """Normalize a name for comparison"""
        if not name:
            return ""
        # Remove special characters, lowercase
        name = re.sub(r'[^\w\s]', '', name.lower())
        # Remove extra whitespace
        name = ' '.join(name.split())
        return name

    @staticmethod
    def name_similarity(name1: str, name2: str) -> float:
        """
        Calculate similarity between two names
        Returns: similarity score 0.0 to 1.0
        """
        if not name1 or not name2:
            return 0.0

        n1 = TextUtils.normalize_name(name1)
        n2 = TextUtils.normalize_name(name2)

        if not n1 or not n2:
            return 0.0

        # Use fuzzy ratio
        ratio = fuzz.ratio(n1, n2) / 100.0

        # Also check token sort ratio for reordered names
        token_ratio = fuzz.token_sort_ratio(n1, n2) / 100.0

        # Return max of both
        return max(ratio, token_ratio)

    @staticmethod
    def extract_keywords(text: str, min_length: int = 3) -> Set[str]:
        """Extract meaningful keywords from text"""
        if not text:
            return set()

        # Remove special characters
        text = re.sub(r'[^\w\s]', ' ', text.lower())

        # Split into words
        words = text.split()

        # Filter short words and common stopwords
        stopwords = {
            'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had',
            'her', 'was', 'one', 'our', 'out', 'has', 'have', 'been', 'from', 'this',
            'that', 'with', 'they', 'will', 'what', 'when', 'where', 'which', 'their',
            'about', 'would', 'there', 'could', 'other', 'than', 'then', 'your', 'more',
            'some', 'very', 'just', 'also', 'most', 'into', 'over', 'such', 'only'
        }

        keywords = {w for w in words if len(w) >= min_length and w not in stopwords}
        return keywords

    @staticmethod
    def keyword_overlap(keywords1: Set[str], keywords2: Set[str]) -> float:
        """
        Calculate keyword overlap ratio
        Returns: Jaccard similarity 0.0 to 1.0
        """
        if not keywords1 or not keywords2:
            return 0.0

        k1 = {k.lower() for k in keywords1}
        k2 = {k.lower() for k in keywords2}

        intersection = len(k1 & k2)
        union = len(k1 | k2)

        if union == 0:
            return 0.0

        return intersection / union

    @staticmethod
    def employer_overlap(employers1: List[str], employers2: List[str]) -> float:
        """
        Calculate employer overlap
        Uses fuzzy matching for similar company names
        """
        if not employers1 or not employers2:
            return 0.0

        e1 = [e.lower().strip() for e in employers1 if e]
        e2 = [e.lower().strip() for e in employers2 if e]

        if not e1 or not e2:
            return 0.0

        matches = 0
        for emp1 in e1:
            for emp2 in e2:
                # Fuzzy match for similar names
                if fuzz.ratio(emp1, emp2) >= 80 or emp1 in emp2 or emp2 in emp1:
                    matches += 1
                    break

        return matches / len(e1)

    @staticmethod
    def extract_years(text: str) -> List[int]:
        """Extract year numbers from text"""
        years = re.findall(r'\b(19|20)\d{2}\b', text)
        return [int(y) for y in years]

    @staticmethod
    def check_timeline_conflicts(
        experience: List[dict],
        external_years: List[int]
    ) -> Tuple[bool, List[str]]:
        """
        Check for timeline conflicts between profile and external data
        Returns: (has_conflict, list of conflict descriptions)
        """
        conflicts = []

        # Extract years from experience
        profile_years = set()
        for exp in experience:
            start = exp.get("start_date", "")
            end = exp.get("end_date", "")

            start_years = TextUtils.extract_years(start)
            end_years = TextUtils.extract_years(end)

            if start_years:
                profile_years.add(min(start_years))
            if end_years:
                profile_years.add(max(end_years))

        # Check for significant gaps
        if profile_years and external_years:
            profile_min = min(profile_years) if profile_years else 0
            profile_max = max(profile_years) if profile_years else 0
            external_min = min(external_years) if external_years else 0
            external_max = max(external_years) if external_years else 0

            # Check if there's a significant discrepancy
            if abs(profile_min - external_min) > 5:
                conflicts.append(f"Career start year discrepancy: profile shows {profile_min}, external shows {external_min}")

            if abs(profile_max - external_max) > 2:
                conflicts.append(f"Recent activity discrepancy: profile shows {profile_max}, external shows {external_max}")

        return len(conflicts) > 0, conflicts

    @staticmethod
    def skills_overlap(skills1: List[str], skills2: List[str]) -> float:
        """Calculate skills overlap ratio"""
        if not skills1 or not skills2:
            return 0.0

        s1 = {s.lower().strip() for s in skills1 if s}
        s2 = {s.lower().strip() for s in skills2 if s}

        if not s1 or not s2:
            return 0.0

        # Check for fuzzy matches
        matches = 0
        for skill1 in s1:
            for skill2 in s2:
                if fuzz.ratio(skill1, skill2) >= 85 or skill1 in skill2 or skill2 in skill1:
                    matches += 1
                    break

        return matches / len(s1)
