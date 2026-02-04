import sys
from pathlib import Path

import streamlit as st

# Ensure project root is on path
ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from tabs import candidate, recruiter, admin


st.set_page_config(
    page_title="theLog.in — Interactive Professional Profile",
    page_icon="🧭",
    layout="wide",
)


def _inject_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --tl-primary: #1f3a8a;
            --tl-secondary: #0f172a;
            --tl-accent: #06b6d4;
            --tl-muted: #64748b;
            --tl-surface: #ffffff;
        }
        .block-container { padding-top: 2.2rem; }
        .tl-hero {
            background: linear-gradient(120deg, #0f172a 0%, #1e3a8a 55%, #0ea5e9 100%);
            color: #ffffff;
            border-radius: 18px;
            padding: 24px 28px;
            margin-bottom: 18px;
            box-shadow: 0 12px 28px rgba(15, 23, 42, 0.25);
        }
        .tl-hero h1 { font-size: 2.1rem; margin: 0 0 4px 0; }
        .tl-hero p { margin: 0; color: #e2e8f0; }
        .tl-card {
            background: var(--tl-surface);
            border-radius: 16px;
            padding: 16px 18px;
            box-shadow: 0 10px 20px rgba(15, 23, 42, 0.08);
            border: 1px solid #e2e8f0;
            margin-bottom: 12px;
        }
        .tl-badge {
            display: inline-block;
            padding: 4px 10px;
            border-radius: 999px;
            font-size: 0.75rem;
            font-weight: 600;
            color: white;
        }
        .tl-badge.high { background: #16a34a; }
        .tl-badge.medium { background: #f59e0b; }
        .tl-badge.low { background: #ef4444; }
        .tl-muted { color: var(--tl-muted); }
        .stTabs [data-baseweb="tab"] { font-weight: 600; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    _inject_styles()

    st.markdown(
        """
        <div class="tl-hero">
            <h1>theLog.in — Interactive Professional Profile</h1>
            <p>Policy-driven grounded responses, audit trails, and trustworthiness scoring.</p>
        </div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.markdown("### Navigation")
        page = st.radio(
            "Select page",
            ["Candidate Console", "Recruiter Console", "Audit Dashboard"],
            index=0,
            label_visibility="collapsed",
        )
        st.divider()
        st.markdown("**Prototype Notes**")
        st.caption("Local-only research prototype. No production authentication or scaling.")

    if page == "Candidate Console":
        candidate.render()
    elif page == "Recruiter Console":
        recruiter.render()
    else:
        admin.render()


if __name__ == "__main__":
    main()
