from __future__ import annotations

from typing import Dict, List, Optional

import streamlit as st

from backend.agents.pipeline import AgentPipeline
from backend.services.profile_service import ProfileService
from backend.services.policy_service import PolicyService
from backend.services.trustworthiness_service import TrustworthinessService


@st.cache_resource
def _services():
    return {
        "profiles": ProfileService(),
        "policy": PolicyService(),
        "pipeline": AgentPipeline(),
        "trust": TrustworthinessService(),
    }


def _profile_options(profiles) -> Dict[str, int]:
    return {f"{p.name} · {p.slug}": p.id for p in profiles}


def _mask_email(email: str) -> str:
    if "@" not in email:
        return "Hidden"
    domain = email.split("@")[-1]
    return f"hidden@{domain}"


def _mask_location(location: str) -> str:
    if not location:
        return "Hidden"
    return location.split(",")[0].strip() or "Hidden"


def _apply_policies(profile_dict: Dict, policy_service: PolicyService, profile_id: int) -> Dict:
    filtered = dict(profile_dict)

    for field in ["email", "phone", "location", "address", "summary", "skills", "experience", "education", "projects", "job_preferences"]:
        policy_type, partial_config = policy_service.check_field_allowed(profile_id, field)

        if policy_type == "BLOCK":
            filtered[field] = None
        elif policy_type == "PARTIAL":
            if field == "email":
                filtered[field] = _mask_email(profile_dict.get(field, ""))
            elif field == "location":
                filtered[field] = _mask_location(profile_dict.get(field, ""))

    return filtered


def _trust_badge(trust_band: str) -> str:
    band = trust_band.lower() if trust_band else "low"
    return f"<span class=\"tl-badge {band}\">{trust_band}</span>"


def render() -> None:
    services = _services()
    profile_service = services["profiles"]
    policy_service = services["policy"]
    pipeline = services["pipeline"]
    trust_service = services["trust"]

    st.markdown("## Recruiter Console")
    st.caption("Ask grounded questions and view trust indicators.")

    profiles = profile_service.get_all_profiles()
    if not profiles:
        st.info("No profiles available yet.")
        return

    options = _profile_options(profiles)
    selection = st.selectbox("Select Candidate", list(options.keys()))
    profile_id = options[selection]

    profile = profile_service.get_profile(profile_id)
    profile_data = _apply_policies(profile.to_dict(), policy_service, profile_id)

    trust_score = trust_service.get_score(profile_id) or trust_service.compute_score(profile_id)

    st.markdown("### Profile Snapshot")
    col1, col2, col3 = st.columns([1.2, 1, 1])
    with col1:
        st.markdown("<div class='tl-card'>", unsafe_allow_html=True)
        st.subheader(profile_data.get("name", "Candidate"))
        st.write(profile_data.get("summary") or "Summary not available.")
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.markdown("<div class='tl-card'>", unsafe_allow_html=True)
        st.metric("Trust Score", trust_score.total_score)
        st.markdown(_trust_badge(trust_score.trust_band), unsafe_allow_html=True)
        st.caption(f"Last verified: {trust_score.last_verified}")
        st.markdown("</div>", unsafe_allow_html=True)
    with col3:
        st.markdown("<div class='tl-card'>", unsafe_allow_html=True)
        st.write("**Contact & Location**")
        st.write(f"Email: {profile_data.get('email') or 'Private'}")
        st.write(f"Location: {profile_data.get('location') or 'Private'}")
        st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("View structured profile", expanded=False):
        st.json(profile_data)

    st.markdown("### Ask a Question")
    question = st.text_area("Recruiter question", placeholder="What is the candidate’s experience with AI products?")
    if st.button("Submit Question", width="stretch"):
        if not question.strip():
            st.error("Please enter a question.")
        else:
            with st.spinner("Running multi-agent pipeline..."):
                result = pipeline.process_question(profile_id, question)
                st.markdown("#### Response")
                st.success(result.final_response)

                st.markdown("#### Trust & Verification")
                cols = st.columns(4)
                cols[0].metric("Policy", result.policy_decision)
                cols[1].metric("GCI", round(result.gci_score, 2))
                cols[2].metric("Verifier", result.verification_result)
                cols[3].metric("Trust Band", trust_score.trust_band)

                with st.expander("Details & Audit Trail", expanded=False):
                    st.write(f"Policy Reason: {result.policy_reason}")
                    st.write("Verification Issues:")
                    st.write(result.verification_issues or "None")
                    st.write("Grounding Packet:")
                    st.json(result.grounding_packet)

    st.divider()
    if st.button("Refresh Trust Score", width="stretch"):
        refreshed = trust_service.refresh_score(profile_id)
        st.success("Trust score refreshed.")
        st.metric("Trust Score", refreshed.total_score)
