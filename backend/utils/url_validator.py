"""
URL Validation and Light Extraction Utilities
"""

import requests
import re
from typing import Tuple, List, Optional
from urllib.parse import urlparse
from datetime import datetime


class URLValidator:
    """Validate URLs and perform light extraction"""

    TIMEOUT = 10
    HEADERS = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    @staticmethod
    def validate_url_format(url: str, expected_domain: Optional[str] = None) -> bool:
        """Validate URL format"""
        try:
            result = urlparse(url)
            if not all([result.scheme, result.netloc]):
                return False
            if expected_domain and expected_domain not in result.netloc:
                return False
            return True
        except:
            return False

    @staticmethod
    def check_reachability(url: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Check if URL is reachable
        Returns: (is_reachable, final_url, page_title)
        """
        try:
            response = requests.get(
                url,
                headers=URLValidator.HEADERS,
                timeout=URLValidator.TIMEOUT,
                allow_redirects=True
            )

            if response.status_code == 200:
                # Extract title
                title = None
                title_match = re.search(r'<title[^>]*>([^<]+)</title>', response.text, re.IGNORECASE)
                if title_match:
                    title = title_match.group(1).strip()

                return True, response.url, title
            else:
                return False, None, None
        except Exception as e:
            return False, None, None

    @staticmethod
    def extract_keywords(url: str, max_keywords: int = 30) -> List[str]:
        """Extract visible keywords from a page (light extraction)"""
        try:
            response = requests.get(
                url,
                headers=URLValidator.HEADERS,
                timeout=URLValidator.TIMEOUT
            )

            if response.status_code != 200:
                return []

            # Remove script and style content
            text = response.text
            text = re.sub(r'<script[^>]*>.*?</script>', '', text, flags=re.DOTALL | re.IGNORECASE)
            text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)

            # Remove HTML tags
            text = re.sub(r'<[^>]+>', ' ', text)

            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text)

            # Extract words
            words = re.findall(r'\b[a-zA-Z]{3,}\b', text.lower())

            # Filter common words
            stopwords = {
                'the', 'and', 'for', 'are', 'but', 'not', 'you', 'all', 'can', 'had',
                'her', 'was', 'one', 'our', 'out', 'has', 'have', 'been', 'from', 'this',
                'that', 'with', 'they', 'will', 'what', 'when', 'where', 'which', 'their',
                'about', 'would', 'there', 'could', 'other', 'than', 'then', 'your', 'more',
                'some', 'very', 'just', 'also', 'most', 'into', 'over', 'such', 'only',
                'page', 'view', 'sign', 'login', 'join', 'home', 'menu', 'click', 'here'
            }

            keywords = [w for w in words if w not in stopwords]

            # Count frequency and return top keywords
            from collections import Counter
            word_counts = Counter(keywords)
            return [word for word, count in word_counts.most_common(max_keywords)]

        except Exception as e:
            return []

    @staticmethod
    def extract_name_from_linkedin(url: str) -> Optional[str]:
        """Try to extract name from LinkedIn page title"""
        try:
            response = requests.get(
                url,
                headers=URLValidator.HEADERS,
                timeout=URLValidator.TIMEOUT
            )

            if response.status_code != 200:
                return None

            # LinkedIn title format: "Name - Title | LinkedIn"
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', response.text, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()
                # Extract name before " - " or " | "
                name_part = re.split(r'\s*[-|]\s*', title)[0].strip()
                if name_part and len(name_part) > 2:
                    return name_part

            return None
        except:
            return None

    @staticmethod
    def extract_name_from_github(url: str) -> Optional[str]:
        """Try to extract name from GitHub page"""
        try:
            response = requests.get(
                url,
                headers=URLValidator.HEADERS,
                timeout=URLValidator.TIMEOUT
            )

            if response.status_code != 200:
                return None

            # Look for name in the page
            # GitHub shows name in itemprop="name" or class="p-name"
            name_match = re.search(
                r'itemprop="name"[^>]*>([^<]+)</span>|class="p-name[^"]*"[^>]*>([^<]+)<',
                response.text,
                re.IGNORECASE
            )
            if name_match:
                name = name_match.group(1) or name_match.group(2)
                if name:
                    return name.strip()

            # Fallback to title
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', response.text, re.IGNORECASE)
            if title_match:
                title = title_match.group(1).strip()
                # GitHub title format: "username (Name)"
                name_match = re.search(r'\(([^)]+)\)', title)
                if name_match:
                    return name_match.group(1).strip()

                # Or just username before " · "
                name_part = title.split('·')[0].strip()
                if name_part:
                    return name_part

            return None
        except:
            return None

    @classmethod
    def validate_linkedin(cls, url: str) -> Tuple[bool, Optional[str], List[str]]:
        """Validate LinkedIn URL and extract basic info"""
        if not cls.validate_url_format(url, "linkedin.com"):
            return False, None, []

        is_reachable, final_url, title = cls.check_reachability(url)
        if not is_reachable:
            return False, None, []

        name = cls.extract_name_from_linkedin(url)
        keywords = cls.extract_keywords(url)

        return True, name, keywords

    @classmethod
    def validate_github(cls, url: str) -> Tuple[bool, Optional[str], List[str]]:
        """Validate GitHub URL and extract basic info"""
        if not cls.validate_url_format(url, "github.com"):
            return False, None, []

        is_reachable, final_url, title = cls.check_reachability(url)
        if not is_reachable:
            return False, None, []

        name = cls.extract_name_from_github(url)
        keywords = cls.extract_keywords(url)

        return True, name, keywords

    @classmethod
    def validate_portfolio(cls, url: str) -> Tuple[bool, Optional[str], List[str]]:
        """Validate portfolio URL and extract basic info"""
        if not cls.validate_url_format(url):
            return False, None, []

        is_reachable, final_url, title = cls.check_reachability(url)
        if not is_reachable:
            return False, None, []

        keywords = cls.extract_keywords(url)

        return True, title, keywords
