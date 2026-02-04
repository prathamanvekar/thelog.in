from __future__ import annotations

from typing import Dict

import streamlit as st

from backend.services.profile_service import ProfileService
from backend.services.interaction_service import InteractionService
from backend.services.trustworthiness_service import TrustworthinessService


@st.cache_resource
def _services():
    return {
        "profiles": ProfileService(),
        "interactions": InteractionService(),
        "trust": TrustworthinessService(),
    }


def _profile_options(profiles) -> Dict[str, int]:
    return {f"{p.name} · {p.slug}": p.id for p in profiles}


def render() -> None:
    services = _services()
    profile_service = services["profiles"]
    interaction_service = services["interactions"]
    trust_service = services["trust"]

    st.markdown("## Audit Dashboard")
    st.caption("Review interaction logs, audit trails, and system reliability.")

    profiles = profile_service.get_all_profiles()
    if not profiles:
        st.info("No profiles available yet.")
        return

    options = _profile_options(profiles)
    selection = st.selectbox("Select Profile", list(options.keys()))
    profile_id = options[selection]

    summary = interaction_service.get_interaction_summary(profile_id)
    trust_score = trust_service.get_score(profile_id) or trust_service.compute_score(profile_id)

    st.markdown("### Reliability Overview")
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Interactions", summary.get("total_interactions", 0))
    col2.metric("Average GCI", summary.get("avg_gci", 0.0))
    col3.metric("Verifier Pass Rate", summary.get("verifier_pass_rate", 1.0))

    st.markdown("### Trust Score Snapshot")
    st.metric("PTS", trust_score.total_score)
    st.write(f"Band: **{trust_score.trust_band}**")
    st.json(trust_score.breakdown)

    st.markdown("### Recent Interactions")
    interactions = interaction_service.get_interactions(profile_id, limit=50)
    st.dataframe([i.to_dict() for i in interactions], width="stretch", hide_index=True)
