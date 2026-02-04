from __future__ import annotations

import json
import uuid
from pathlib import Path
from typing import Dict, List, Optional

import streamlit as st

from backend.database.models import (
    CandidateProfile,
    Education,
    Experience,
    Project,
    JobPreferences,
)
from backend.services.profile_service import ProfileService
from backend.services.resume_parser import ResumeParser
from backend.services.policy_service import PolicyService
from backend.services.trustworthiness_service import TrustworthinessService


DATA_DIR = Path(__file__).resolve().parents[2] / "data"
UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


@st.cache_resource
def _services():
    return {
        "profiles": ProfileService(),
        "parser": ResumeParser(),
        "policy": PolicyService(),
        "trust": TrustworthinessService(),
    }


def _profile_options(profiles: List[CandidateProfile]) -> Dict[str, int]:
    return {f"{p.name} · {p.slug}": p.id for p in profiles}


def _skills_from_text(text: str) -> List[str]:
    return [s.strip() for s in text.split(",") if s.strip()]


def _education_inputs(count: int, prefix: str) -> List[Education]:
    educations: List[Education] = []
    for idx in range(count):
        st.markdown(f"**Education {idx + 1}**")
        institution = st.text_input("Institution", key=f"{prefix}_edu_inst_{idx}")
        degree = st.text_input("Degree", key=f"{prefix}_edu_degree_{idx}")
        field = st.text_input("Field of Study", key=f"{prefix}_edu_field_{idx}")
        start_year = st.number_input("Start Year", min_value=1900, max_value=2100, step=1, key=f"{prefix}_edu_start_{idx}")
        end_year = st.number_input("End Year", min_value=1900, max_value=2100, step=1, key=f"{prefix}_edu_end_{idx}")
        description = st.text_area("Description", key=f"{prefix}_edu_desc_{idx}")
        educations.append(
            Education(
                institution=institution,
                degree=degree,
                field_of_study=field,
                start_year=int(start_year) if start_year else None,
                end_year=int(end_year) if end_year else None,
                description=description,
            )
        )
        st.divider()
    return educations


def _experience_inputs(count: int, prefix: str) -> List[Experience]:
    experiences: List[Experience] = []
    for idx in range(count):
        st.markdown(f"**Experience {idx + 1}**")
        company = st.text_input("Company", key=f"{prefix}_exp_company_{idx}")
        title = st.text_input("Title", key=f"{prefix}_exp_title_{idx}")
        location = st.text_input("Location", key=f"{prefix}_exp_location_{idx}")
        start_date = st.text_input("Start Date", key=f"{prefix}_exp_start_{idx}")
        end_date = st.text_input("End Date", key=f"{prefix}_exp_end_{idx}")
        is_current = st.checkbox("Currently Here", key=f"{prefix}_exp_current_{idx}")
        description = st.text_area("Description", key=f"{prefix}_exp_desc_{idx}")
        highlights = st.text_area("Highlights (comma-separated)", key=f"{prefix}_exp_high_{idx}")
        experiences.append(
            Experience(
                company=company,
                title=title,
                location=location,
                start_date=start_date,
                end_date=end_date,
                is_current=is_current,
                description=description,
                highlights=_skills_from_text(highlights),
            )
        )
        st.divider()
    return experiences


def _project_inputs(count: int, prefix: str) -> List[Project]:
    projects: List[Project] = []
    for idx in range(count):
        st.markdown(f"**Project {idx + 1}**")
        name = st.text_input("Project Name", key=f"{prefix}_proj_name_{idx}")
        description = st.text_area("Description", key=f"{prefix}_proj_desc_{idx}")
        technologies = st.text_input("Technologies (comma-separated)", key=f"{prefix}_proj_tech_{idx}")
        url = st.text_input("Project URL", key=f"{prefix}_proj_url_{idx}")
        start_date = st.text_input("Start Date", key=f"{prefix}_proj_start_{idx}")
        end_date = st.text_input("End Date", key=f"{prefix}_proj_end_{idx}")
        projects.append(
            Project(
                name=name,
                description=description,
                technologies=_skills_from_text(technologies),
                url=url,
                start_date=start_date,
                end_date=end_date,
            )
        )
        st.divider()
    return projects


def _job_preferences(prefix: str) -> JobPreferences:
    desired_roles = st.text_input("Desired Roles (comma-separated)", key=f"{prefix}_roles")
    locations = st.text_input("Preferred Locations (comma-separated)", key=f"{prefix}_locations")
    remote_preference = st.selectbox(
        "Remote Preference",
        ["", "remote", "hybrid", "onsite", "flexible"],
        key=f"{prefix}_remote",
    )
    expected_salary = st.text_input("Expected Salary", key=f"{prefix}_salary")
    notice_period = st.text_input("Notice Period", key=f"{prefix}_notice")
    willing_to_relocate = st.checkbox("Willing to Relocate", key=f"{prefix}_relocate")

    return JobPreferences(
        desired_roles=_skills_from_text(desired_roles),
        preferred_locations=_skills_from_text(locations),
        remote_preference=remote_preference,
        expected_salary=expected_salary,
        notice_period=notice_period,
        willing_to_relocate=willing_to_relocate,
    )


def _build_profile_from_inputs(prefix: str) -> CandidateProfile:
    name = st.text_input("Full Name", key=f"{prefix}_name")
    email = st.text_input("Email", key=f"{prefix}_email")
    phone = st.text_input("Phone", key=f"{prefix}_phone")
    location = st.text_input("Location", key=f"{prefix}_location")
    summary = st.text_area("Professional Summary", key=f"{prefix}_summary")
    skills = _skills_from_text(st.text_input("Skills (comma-separated)", key=f"{prefix}_skills"))

    edu_count = st.number_input("Education Entries", min_value=0, max_value=5, step=1, key=f"{prefix}_edu_count")
    education = _education_inputs(int(edu_count), prefix)

    exp_count = st.number_input("Experience Entries", min_value=0, max_value=8, step=1, key=f"{prefix}_exp_count")
    experience = _experience_inputs(int(exp_count), prefix)

    proj_count = st.number_input("Project Entries", min_value=0, max_value=6, step=1, key=f"{prefix}_proj_count")
    projects = _project_inputs(int(proj_count), prefix)

    job_preferences = _job_preferences(prefix)

    return CandidateProfile(
        name=name,
        email=email,
        phone=phone,
        location=location,
        summary=summary,
        skills=skills,
        education=education,
        experience=experience,
        projects=projects,
        job_preferences=job_preferences,
    )


def _create_profile_from_resume(parser: ResumeParser, profile_service: ProfileService, policy_service: PolicyService) -> None:
    st.markdown("### Resume Upload")
    uploaded = st.file_uploader("Upload Resume (PDF/DOCX/TXT)", type=["pdf", "docx", "doc", "txt"])

    if uploaded is None:
        st.info("Upload a resume to begin parsing.")
        return

    temp_path = UPLOAD_DIR / f"{uuid.uuid4().hex}_{uploaded.name}"
    with temp_path.open("wb") as f:
        f.write(uploaded.getbuffer())

    if st.button("Parse Resume", width="stretch"):
        with st.spinner("Parsing resume with Groq LLM..."):
            try:
                profile = parser.parse_resume(str(temp_path))
                st.session_state["resume_profile"] = profile.to_dict()
                st.success("Resume parsed. Review and save the profile below.")
            except Exception as exc:
                st.error(f"Resume parsing failed: {exc}")

    parsed = st.session_state.get("resume_profile")
    if not parsed:
        return

    st.markdown("### Review Parsed Profile")
    st.caption("Edit any field before saving.")

    profile = CandidateProfile.from_dict(parsed)
    with st.form("save_parsed_profile"):
        name = st.text_input("Full Name", value=profile.name)
        email = st.text_input("Email", value=profile.email)
        phone = st.text_input("Phone", value=profile.phone)
        location = st.text_input("Location", value=profile.location)
        summary = st.text_area("Professional Summary", value=profile.summary)
        skills = st.text_input("Skills (comma-separated)", value=", ".join(profile.skills))
        submitted = st.form_submit_button("Save Profile", width="stretch")

    if submitted:
        profile.name = name
        profile.email = email
        profile.phone = phone
        profile.location = location
        profile.summary = summary
        profile.skills = _skills_from_text(skills)

        profile_id = profile_service.create_profile(profile)
        policy_service.initialize_default_policies(profile_id)
        st.success("Profile created with default privacy policies.")
        st.session_state.pop("resume_profile", None)


def _create_profile_manual(profile_service: ProfileService, policy_service: PolicyService) -> None:
    st.markdown("### Manual Profile Entry")
    with st.form("manual_profile_form"):
        profile = _build_profile_from_inputs("manual")
        submitted = st.form_submit_button("Create Profile", width="stretch")

    if submitted:
        if not profile.name.strip():
            st.error("Full name is required.")
            return
        profile_id = profile_service.create_profile(profile)
        policy_service.initialize_default_policies(profile_id)
        st.success("Profile created with default privacy policies.")


def _edit_profile(profile_service: ProfileService) -> None:
    profiles = profile_service.get_all_profiles()
    if not profiles:
        st.info("No profiles available yet.")
        return

    options = _profile_options(profiles)
    selection = st.selectbox("Select Profile", list(options.keys()))
    profile_id = options[selection]
    profile = profile_service.get_profile(profile_id)

    st.markdown("### Edit Profile")
    with st.form("edit_profile_form"):
        name = st.text_input("Full Name", value=profile.name)
        email = st.text_input("Email", value=profile.email)
        phone = st.text_input("Phone", value=profile.phone)
        location = st.text_input("Location", value=profile.location)
        summary = st.text_area("Professional Summary", value=profile.summary)
        skills = st.text_input("Skills (comma-separated)", value=", ".join(profile.skills))
        submitted = st.form_submit_button("Update Profile", width="stretch")

    if submitted:
        profile.name = name
        profile.email = email
        profile.phone = phone
        profile.location = location
        profile.summary = summary
        profile.skills = _skills_from_text(skills)
        profile_service.update_profile(profile)
        st.success("Profile updated.")


def _manage_policies(policy_service: PolicyService, profile_service: ProfileService) -> None:
    profiles = profile_service.get_all_profiles()
    if not profiles:
        st.info("Create a profile first.")
        return

    options = _profile_options(profiles)
    selection = st.selectbox("Profile for Policies", list(options.keys()), key="policy_profile")
    profile_id = options[selection]

    st.markdown("### Current Policies")
    policies = policy_service.get_policies(profile_id)
    policy_rows = [p.to_dict() for p in policies]
    st.dataframe(policy_rows, width="stretch", hide_index=True)

    st.markdown("### Update Policy")
    field_name = st.selectbox("Field", policy_service.get_all_field_names())
    policy_type = st.selectbox("Policy", ["ALLOW", "BLOCK", "PARTIAL"])
    partial_config = None
    if policy_type == "PARTIAL" and field_name == "email":
        partial_config = {"show_domain_only": True}
        st.info("Email will be shown as domain-only.")

    if st.button("Save Policy", width="stretch"):
        policy_service.set_policy(profile_id, field_name, policy_type, partial_config)
        st.success("Policy updated.")


def _manage_linked_profiles(profile_service: ProfileService) -> None:
    profiles = profile_service.get_all_profiles()
    if not profiles:
        st.info("Create a profile first.")
        return

    options = _profile_options(profiles)
    selection = st.selectbox("Profile for Linked Accounts", list(options.keys()), key="linked_profile")
    profile_id = options[selection]

    st.markdown("### Add / Refresh Links")
    col1, col2, col3 = st.columns(3)
    with col1:
        linkedin = st.text_input("LinkedIn URL")
        if st.button("Save LinkedIn", width="stretch"):
            if linkedin:
                profile_service.add_linked_profile(profile_id, "linkedin", linkedin)
                st.success("LinkedIn saved.")
    with col2:
        github = st.text_input("GitHub URL")
        if st.button("Save GitHub", width="stretch"):
            if github:
                profile_service.add_linked_profile(profile_id, "github", github)
                st.success("GitHub saved.")
    with col3:
        portfolio = st.text_input("Portfolio URL")
        if st.button("Save Portfolio", width="stretch"):
            if portfolio:
                profile_service.add_linked_profile(profile_id, "portfolio", portfolio)
                st.success("Portfolio saved.")

    st.divider()
    st.markdown("### Linked Profiles")
    linked_profiles = profile_service.get_linked_profiles(profile_id)
    st.dataframe([lp.to_dict() for lp in linked_profiles], width="stretch", hide_index=True)


def _email_verification(profile_service: ProfileService) -> None:
    profiles = profile_service.get_all_profiles()
    if not profiles:
        st.info("Create a profile first.")
        return

    options = _profile_options(profiles)
    selection = st.selectbox("Profile for Verification", list(options.keys()), key="verify_profile")
    profile_id = options[selection]

    if st.button("Mark Email as Verified (OTP)", width="stretch"):
        profile_service.verify_email(profile_id)
        st.success("Email verification updated.")


def _trustworthiness_panel(trust_service: TrustworthinessService, profile_service: ProfileService) -> None:
    profiles = profile_service.get_all_profiles()
    if not profiles:
        st.info("Create a profile first.")
        return

    options = _profile_options(profiles)
    selection = st.selectbox("Profile for Trust Score", list(options.keys()), key="trust_profile")
    profile_id = options[selection]

    score = trust_service.get_score(profile_id)
    if not score:
        score = trust_service.compute_score(profile_id)

    st.markdown("### Trustworthiness Score")
    st.metric("PTS", score.total_score, help="Profile Trustworthiness Score")
    st.write(f"Band: **{score.trust_band}**")

    st.markdown("#### Breakdown")
    st.json(score.breakdown)

    if st.button("Refresh Score", width="stretch"):
        refreshed = trust_service.refresh_score(profile_id)
        st.success("Trust score refreshed.")
        st.json(refreshed.breakdown)


def render() -> None:
    services = _services()
    profile_service = services["profiles"]
    parser = services["parser"]
    policy_service = services["policy"]
    trust_service = services["trust"]

    st.markdown("## Candidate Console")
    st.caption("Create, review, and govern your professional profile.")

    tab_create, tab_edit, tab_policy, tab_links, tab_trust = st.tabs(
        ["Create Profile", "Edit Profile", "Privacy Policies", "Linked Profiles", "Trust Score"]
    )

    with tab_create:
        st.markdown("### Profile Creation")
        mode = st.radio("Choose input method", ["Resume Upload", "Manual Entry"], horizontal=True)
        if mode == "Resume Upload":
            _create_profile_from_resume(parser, profile_service, policy_service)
        else:
            _create_profile_manual(profile_service, policy_service)

    with tab_edit:
        _edit_profile(profile_service)

    with tab_policy:
        _manage_policies(policy_service, profile_service)

    with tab_links:
        _manage_linked_profiles(profile_service)
        st.divider()
        _email_verification(profile_service)

    with tab_trust:
        _trustworthiness_panel(trust_service, profile_service)
