"""
Configuration settings for theLog.in
"""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# Database
DATABASE_PATH = os.getenv("DATABASE_PATH", str(DATA_DIR / "thelog.db"))

# Groq API
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
GROQ_MODEL = "llama-3.1-8b-instant"

# GCI Thresholds
GCI_HIGH_THRESHOLD = 0.7
GCI_LOW_THRESHOLD = 0.3

# Trustworthiness Score Weights
PTS_IDENTITY_MAX = 30
PTS_CONSISTENCY_MAX = 30
PTS_INTERNAL_MAX = 25
PTS_TRANSPARENCY_MAX = 15

# Trust Bands
TRUST_BAND_HIGH = 80
TRUST_BAND_MEDIUM = 60

# Policy Types
POLICY_ALLOW = "ALLOW"
POLICY_BLOCK = "BLOCK"
POLICY_PARTIAL = "PARTIAL"

# Default blocked fields
DEFAULT_BLOCKED_FIELDS = ["salary", "phone", "address", "ssn", "id_number"]
DEFAULT_PARTIAL_FIELDS = ["email", "location"]
