"""
Page 3 — LinkedIn Outreach.

Workflow :
  1. Configurer la campagne (keyword, location, limite)
  2. Lancer la recherche + enrichissement + génération de notes (Playwright)
  3. Review des profils : approuver / rejeter / modifier la note
  4. Envoyer les connexions approuvées

Phase 3 de CareerSignal.
"""

from __future__ import annotations

import os
import sys
import threading
import time

# ── Path fix ─────────────────────────────────────────────────────────────────
sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)

import streamlit as st

from tools.outreach_store import (
    get_campaign_stats,
    get_records_by_campaign,
    get_records_by_status,
    load_records,
    remaining_today,
    update_record_note,
    update_record_status,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LinkedIn Outreach",
    page_icon="🤝",
    layout="wide",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
  .profile-card {
    background: #ffffff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 14px;
    box-shadow: 0 1px 4px rgba(0,0,0,0.06);
    transition: box-shadow 0.2s;
  }
  .profile-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,0.10); }
  .badge-pending  { background:#fef9c3; color:#854d0e; border-radius:8px; padding:2px 10px; font-size:12px; font-weight:600; }
  .badge-approved { background:#dcfce7; color:#166534; border-radius:8px; padding:2px 10px; font-size:12px; font-weight:600; }
  .badge-rejected { background:#fee2e2; color:#991b1b; border-radius:8px; padding:2px 10px; font-size:12px; font-weight:600; }
  .badge-sent     { background:#dbeafe; color:#1e40af; border-radius:8px; padding:2px 10px; font-size:12px; font-weight:600; }
  .badge-accepted { background:#f0fdf4; color:#15803d; border-radius:8px; padding:2px 10px; font-size:12px; font-weight:600; }
  .badge-skipped  { background:#f1f5f9; color:#475569; border-radius:8px; padding:2px 10px; font-size:12px; font-weight:600; }
  .badge-ignored  { background:#f1f5f9; color:#94a3b8; border-radius:8px; padding:2px 10px; font-size:12px; font-weight:600; }
  .stat-box {
    background: #f8fafc;
    border-radius: 10px;
    padding: 14px 10px;
    text-align: center;
    border: 1px solid #e2e8f0;
  }
  .stat-num  { font-size: 28px; font-weight: 700; color: #4338CA; }
  .stat-lbl  { font-size: 12px; color: #64748b; margin-top: 2px; }
  .log-box   { background: #1e1e2e; color: #a8ff78; border-radius: 8px;
               padding: 14px; font-family: monospace; font-size: 12px;
               max-height: 300px; overflow-y: auto; }
</style>
""",
    unsafe_allow_html=True,
)


# ── Session state init ────────────────────────────────────────────────────────
def _init_session():
    defaults = {
        "out_logs": [],
        "out_running": False,
        "out_campaign_id": None,
        "out_send_running": False,
        "out_send_logs": [],
        "out_regen_running": False,
        "out_regen_logs": [],
        "out_check_running": False,
        "out_check_logs": [],
        # Pré-charger depuis les variables d'environnement si disponibles
        "li_email": os.getenv("LINKEDIN_EMAIL", ""),
        "li_password": os.getenv("LINKEDIN_PASSWORD", ""),
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_session()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Config")

    # ── Provider LLM (pour la génération des notes) ───────────────────────────
    st.markdown("### 🤖 Provider LLM (notes)")
    from core.client import clear_provider_cache
    from core.config import settings as _settings

    current_provider = os.getenv("LLM_PROVIDER", "anthropic")
    provider_choice = st.radio(
        "Provider",
        options=["anthropic", "openai"],
        index=0 if current_provider == "anthropic" else 1,
        format_func=lambda x: "🟤 Anthropic (Claude)" if x == "anthropic" else "🟢 OpenAI (GPT)",
        horizontal=True,
        label_visibility="collapsed",
        key="out_provider",
    )
    if provider_choice != current_provider:
        os.environ["LLM_PROVIDER"] = provider_choice
        clear_provider_cache()
        st.rerun()
    st.caption(f"Modèle: `{_settings.model.agent(provider_choice)}`")

    st.divider()

    # ── Mon profil expéditeur ─────────────────────────────────────────────────
    st.markdown("### 🎓 Mon profil expéditeur")

    _default_context = (
        "Je suis en fin de thèse industrielle en intelligence artificielle, "
        "avec des travaux autour des LLM, du RAG et du développement de "
        "solutions data/IA appliquées. Je cherche à échanger avec des "
        "professionnels pour mieux comprendre les métiers, les compétences "
        "attendues et les retours d'expérience dans le domaine."
    )
    _default_name = "Ichrak Ennaceur"

    sender_name = st.text_input(
        "Ton prénom / nom",
        value=st.session_state.get("sender_name", _default_name),
        key="sidebar_sender_name",
    )
    sender_context = st.text_area(
        "Ton contexte (thèse, spécialité, objectif…)",
        value=st.session_state.get("sender_context", _default_context),
        height=160,
        key="sidebar_sender_context",
        help="Ce texte est injecté dans le prompt LLM pour personnaliser les notes.",
    )
    regen_niche = st.text_input(
        "Domaine / niche",
        value=st.session_state.get("regen_niche", "Applied AI / Gen AI — LLM, RAG"),
        key="sidebar_regen_niche",
    )

    _languages = ["French", "English", "Arabic", "Spanish", "German", "Italian", "Portuguese"]
    regen_language = st.selectbox(
        "🌍 Langue des notes",
        options=_languages,
        index=_languages.index(st.session_state.get("regen_language", "French")),
        key="sidebar_regen_language",
    )

    # Sauvegarder dans session_state pour les threads
    st.session_state["sender_name"] = sender_name
    st.session_state["sender_context"] = sender_context
    st.session_state["regen_niche"] = regen_niche
    st.session_state["regen_language"] = regen_language

    st.divider()

    # LinkedIn credentials
    st.markdown("### 🔐 LinkedIn Auth")
    email_in = st.text_input(
        "Email LinkedIn",
        value=st.session_state.li_email,
        type="default",
        key="sidebar_email",
    )
    pwd_in = st.text_input(
        "Mot de passe",
        value=st.session_state.li_password,
        type="password",
        key="sidebar_pwd",
    )
    st.session_state.li_email = email_in
    st.session_state.li_password = pwd_in

    if email_in and pwd_in:
        st.success("✅ Credentials sauvegardés")
    else:
        st.warning("⚠️ Email / mot de passe requis")

    st.divider()

    # Stats globales
    st.markdown("### 📊 Stats globales")
    stats = get_campaign_stats()
    for label, key in [
        ("Total", "total"),
        ("Pending", "pending"),
        ("Approved", "approved"),
        ("Sent", "sent"),
        ("Accepted", "accepted"),
    ]:
        st.markdown(
            f"<div style='display:flex;justify-content:space-between;'>"
            f"<span>{label}</span><strong>{stats.get(key, 0)}</strong></div>",
            unsafe_allow_html=True,
        )

    st.markdown(
        f"<br>📤 **Restantes aujourd'hui : {remaining_today(15)}**",
        unsafe_allow_html=True,
    )


# ── Titre ─────────────────────────────────────────────────────────────────────
st.title("🤝 LinkedIn Outreach — Phase 3")
st.markdown(
    "Recherche de profils → enrichissement → génération de notes personnalisées → "
    "envoi de connexions avec suivi."
)

tab1, tab2, tab3 = st.tabs(["🔍 Nouvelle Campagne", "📋 Review des Profils", "📤 Envoi"])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Nouvelle campagne
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("🎯 Paramètres de la campagne")

    # ── Type de recherche ─────────────────────────────────────────────────────
    search_type_options = {
        "👤 Profils (People Search)": "people",
        "💼 Offres d'emploi (Jobs → Recruteurs)": "jobs",
    }
    search_type_label = st.radio(
        "🔎 Type de recherche",
        options=list(search_type_options.keys()),
        horizontal=True,
        help=(
            "**Profils** : recherche de personnes par titre/domaine.\n\n"
            "**Offres d'emploi** : scrape les offres LinkedIn → identifie le recruteur "
            "→ génère une note ciblée sur le poste."
        ),
    )
    search_type = search_type_options[search_type_label]
    is_jobs = search_type == "jobs"

    # ── Aide contextuelle ─────────────────────────────────────────────────────
    if is_jobs:
        st.info(
            "💼 **Mode Offres d'emploi** : LinkedIn Jobs sera parcouru, le recruteur de chaque "
            "offre sera identifié, et une note personnalisée mentionnant le poste sera générée.",
            icon="💼",
        )
    else:
        st.info(
            "👤 **Mode Profils** : recherche de personnes par mots-clés dans LinkedIn People Search.",
            icon="👤",
        )

    st.divider()

    col1, col2 = st.columns(2)
    with col1:
        keyword_label = "🔑 Titre du poste" if is_jobs else "🔑 Mots-clés de recherche"
        keyword_placeholder = (
            "ex: Ingénieur IA, Data Scientist, ML Engineer"
            if is_jobs
            else "ex: AI Engineer, MLOps Lead, GenAI Founder"
        )
        keyword = st.text_input(keyword_label, placeholder=keyword_placeholder)

        niche = st.text_input(
            "🎯 Filtre niche / domaine",
            value=st.session_state.get("regen_niche", ""),
            placeholder="ex: GenAI LLM RAG, Computer Vision, MLOps",
            help=(
                "Ajouté aux mots-clés pour affiner la recherche. "
                "Exemple : keyword='Ingénieur IA' + niche='RAG LLM' → cherche 'Ingénieur IA RAG LLM'."
            ),
        )

        location = st.text_input(
            "📍 Localisation",
            placeholder="ex: France, Paris, Remote",
        )
        max_profiles = st.slider(
            "💼 Nombre max d'offres" if is_jobs else "👥 Nombre max de profils",
            5,
            50,
            20,
        )

    with col2:
        sender_niche = st.text_input(
            "🎓 Votre niche / domaine",
            value=st.session_state.get("regen_niche", "Applied AI / Gen AI Engineering"),
            help="Votre domaine d'expertise — utilisé pour personnaliser les notes",
        )
        sender_goal_default = (
            "postuler ou me faire connaître auprès des recruteurs IA"
            if is_jobs
            else "connect with AI builders, researchers and startup founders"
        )
        sender_goal = st.text_area(
            "🎯 Objectif du réseau",
            value=sender_goal_default,
            height=80,
            help="Pourquoi voulez-vous vous connecter à ces profils ?",
        )
        language = st.selectbox(
            "🌍 Langue des notes",
            ["French", "English", "Arabic", "Spanish", "German", "Italian", "Portuguese"],
            index=0,
        )

    headless = st.checkbox(
        "👻 Mode Headless (pas de fenêtre navigateur)",
        value=False,
        help="Recommandé: désactivé pour éviter la détection LinkedIn",
    )

    st.info(
        "ℹ️ Playwright va ouvrir un vrai navigateur Chrome pour interagir avec LinkedIn. "
        "Ne fermez pas la fenêtre pendant le scraping.",
        icon="ℹ️",
    )

    # Bouton lancement
    can_launch = (
        keyword
        and st.session_state.li_email
        and st.session_state.li_password
        and not st.session_state.out_running
    )

    if not st.session_state.li_email or not st.session_state.li_password:
        st.warning("⚠️ Renseigne ton email et mot de passe LinkedIn dans la sidebar.")

    if st.button(
        "🚀 Lancer la campagne",
        disabled=not can_launch,
        type="primary",
        use_container_width=True,
    ):
        st.session_state.out_logs = []
        st.session_state.out_running = True

        # Capturer les valeurs avant le thread (thread-safe : pas d'accès session_state depuis thread)
        _email = st.session_state.li_email
        _password = st.session_state.li_password
        _keyword = keyword
        _niche = niche
        _search_type = search_type
        _location = location
        _max_profiles = max_profiles
        _sender_niche = sender_niche
        _sender_goal = sender_goal
        _sender_context = st.session_state.get("sender_context", "")
        _sender_name = st.session_state.get("sender_name", "")
        _language = language
        _headless = headless
        _logs_ref = st.session_state.out_logs

        def _run_pipeline():
            from pipelines.outreach_pipeline import OutreachPipeline

            def cb(msg: str):
                _logs_ref.append(msg)

            pipeline = OutreachPipeline(daily_limit=15)
            result = pipeline.run(
                email=_email,
                password=_password,
                keyword=_keyword,
                location=_location,
                niche=_niche,
                search_type=_search_type,
                max_profiles=_max_profiles,
                sender_niche=_sender_niche,
                sender_goal=_sender_goal,
                sender_context=_sender_context,
                sender_name=_sender_name,
                language=_language,
                headless=_headless,
                callback=cb,
            )
            st.session_state.out_campaign_id = result.campaign_id
            st.session_state.out_running = False

        t = threading.Thread(target=_run_pipeline, daemon=True)
        t.start()
        st.rerun()

    # Logs
    if st.session_state.out_running or st.session_state.out_logs:
        st.markdown("### 📡 Logs")

        if st.session_state.out_running:
            st.spinner("⏳ Campagne en cours…")

        logs_html = "<br>".join(st.session_state.out_logs[-50:])
        st.markdown(
            f'<div class="log-box">{logs_html or "En attente…"}</div>',
            unsafe_allow_html=True,
        )

        if st.session_state.out_running:
            time.sleep(1)
            st.rerun()
        elif not st.session_state.out_running and st.session_state.out_logs:
            st.success("✅ Campagne terminée ! Passe à l'onglet **Review des Profils**.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Review des profils
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("📋 Review des profils")

    # Filtre
    col_f1, col_f2 = st.columns([2, 2])
    with col_f1:
        status_filter = st.selectbox(
            "Statut",
            ["all", "pending", "approved", "rejected", "sent", "accepted", "skipped"],
            index=0,
        )
    with col_f2:
        # Sélecteur de campagne
        all_records = load_records()
        campaigns = sorted({r.campaign_id for r in all_records}, reverse=True)
        campaign_filter = st.selectbox(
            "Campagne",
            ["all"] + campaigns,
            index=0,
        )

    # Charger les records filtrés
    if campaign_filter != "all":
        records = get_records_by_campaign(campaign_filter)
    else:
        records = all_records

    if status_filter != "all":
        records = [r for r in records if r.status == status_filter]

    st.markdown(f"**{len(records)} profil(s)** trouvé(s)")

    # Bulk actions
    if records:
        col_ba1, col_ba2, col_ba3, col_ba4 = st.columns(4)
        with col_ba1:
            if st.button("✅ Tout approuver", use_container_width=True):
                for r in records:
                    if r.status == "pending":
                        update_record_status(r.id, "approved")
                st.rerun()
        with col_ba2:
            if st.button("❌ Tout rejeter", use_container_width=True):
                for r in records:
                    if r.status == "pending":
                        update_record_status(r.id, "rejected")
                st.rerun()
        with col_ba3:
            empty_notes = [r for r in records if not r.note.strip()]
            regen_label = f"🔄 Régénérer notes ({len(empty_notes)} vides)"
            regen_disabled = len(empty_notes) == 0 or st.session_state.out_regen_running
            if st.button(regen_label, use_container_width=True, disabled=regen_disabled):
                st.session_state.out_regen_running = True
                st.session_state.out_regen_logs = []

                # Capturer les valeurs avant le thread (thread-safe)
                _regen_records = list(empty_notes)
                _regen_niche = st.session_state.get("regen_niche", "Applied AI / Gen AI — LLM, RAG")
                _regen_context = st.session_state.get("sender_context", "")
                _regen_sender_name = st.session_state.get("sender_name", "")
                _regen_language = st.session_state.get("regen_language", "French")
                _regen_logs = st.session_state.out_regen_logs

                def _run_regen():
                    from agents.outreach_agent import OutreachAgent

                    agent = OutreachAgent()

                    for rec in _regen_records:
                        _regen_logs.append(f"✍️ Génération note pour {rec.name}…")
                        try:
                            lang = _regen_language
                            note = agent.generate_note(
                                record=rec,
                                sender_niche=_regen_niche,
                                sender_context=_regen_context,
                                sender_name=_regen_sender_name,
                                language=lang,
                            )
                            update_record_note(rec.id, note)
                            _regen_logs.append(
                                f"   ✅ {rec.name} ({len(note)} chars): {note[:70]}…"
                            )
                        except Exception as e:
                            _regen_logs.append(f"   ❌ {rec.name}: {e}")

                    _regen_logs.append(
                        f"\n✅ Régénération terminée — {len(_regen_records)} notes traitées"
                    )
                    st.session_state.out_regen_running = False

                t = threading.Thread(target=_run_regen, daemon=True)
                t.start()
                st.rerun()

        with col_ba4:
            pending_count = sum(1 for r in records if r.status == "pending")
            st.markdown(
                f"<div style='text-align:center;padding:8px;color:#64748b;'>"
                f"⏳ {pending_count} en attente</div>",
                unsafe_allow_html=True,
            )

    # Logs de régénération
    if st.session_state.out_regen_running or st.session_state.out_regen_logs:
        st.markdown("#### 📡 Logs de régénération")
        regen_html = "<br>".join(st.session_state.out_regen_logs[-30:])
        st.markdown(
            f'<div class="log-box">{regen_html or "En attente…"}</div>',
            unsafe_allow_html=True,
        )
        if st.session_state.out_regen_running:
            time.sleep(1)
            st.rerun()
        else:
            st.success("✅ Notes régénérées ! Rafraîchis la page pour voir les nouvelles notes.")
            if st.button("🔄 Rafraîchir la liste", key="refresh_after_regen"):
                # Reset les note_key du session_state pour forcer le rechargement
                for k in list(st.session_state.keys()):
                    if k.startswith("note_"):
                        del st.session_state[k]
                st.session_state.out_regen_logs = []
                st.rerun()

    st.divider()

    # Cartes de profils
    BADGE = {
        "pending": "badge-pending",
        "approved": "badge-approved",
        "rejected": "badge-rejected",
        "sent": "badge-sent",
        "accepted": "badge-accepted",
        "skipped": "badge-skipped",
        "ignored": "badge-ignored",
    }

    for rec in records:
        badge_cls = BADGE.get(rec.status, "badge-pending")
        about_short = rec.about[:150] + "…" if len(rec.about) > 150 else rec.about

        with st.expander(
            f"**{rec.name}** — {rec.title} @ {rec.company}  [{rec.status.upper()}]",
            expanded=(rec.status == "pending"),
        ):
            col_l, col_r = st.columns([3, 2])

            with col_l:
                st.markdown(
                    f"<span class='{badge_cls}'>{rec.status}</span>",
                    unsafe_allow_html=True,
                )
                st.markdown(f"🔗 [{rec.profile_url}]({rec.profile_url})")
                if rec.location:
                    st.markdown(f"📍 {rec.location}")
                if about_short:
                    st.markdown(f"*{about_short}*")

            with col_r:
                # Éditeur de note
                note_key = f"note_{rec.id}"
                if note_key not in st.session_state:
                    st.session_state[note_key] = rec.note

                new_note = st.text_area(
                    "✍️ Note de connexion",
                    value=st.session_state[note_key],
                    key=f"ta_{rec.id}",
                    height=100,
                    max_chars=300,
                    help="Max 300 caractères (limite LinkedIn)",
                )
                char_count = len(new_note)
                color = "#dc2626" if char_count > 300 else "#16a34a"
                st.markdown(
                    f"<small style='color:{color}'>{char_count}/300 chars</small>",
                    unsafe_allow_html=True,
                )

                # Boutons d'action
                btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
                with btn_col1:
                    if st.button("✅", key=f"approve_{rec.id}", help="Approuver"):
                        if new_note != rec.note:
                            update_record_note(rec.id, new_note)
                        update_record_status(rec.id, "approved")
                        st.rerun()
                with btn_col2:
                    if st.button("❌", key=f"reject_{rec.id}", help="Rejeter"):
                        update_record_status(rec.id, "rejected")
                        st.rerun()
                with btn_col3:
                    if st.button("💾", key=f"save_{rec.id}", help="Sauvegarder note"):
                        update_record_note(rec.id, new_note)
                        st.success("Note sauvegardée !")
                with btn_col4:
                    regen_key = f"regen_{rec.id}"
                    if st.button(
                        "✨ Générer", key=regen_key, help="Générer une note personnalisée via LLM"
                    ):
                        with st.spinner("Génération en cours…"):
                            try:
                                from agents.outreach_agent import OutreachAgent

                                _a = OutreachAgent()
                                _note = _a.generate_note(
                                    record=rec,
                                    sender_niche=st.session_state.get(
                                        "regen_niche", "Applied AI / Gen AI — LLM, RAG"
                                    ),
                                    sender_context=st.session_state.get("sender_context", ""),
                                    sender_name=st.session_state.get("sender_name", ""),
                                    language=st.session_state.get("regen_language", "French"),
                                )
                                update_record_note(rec.id, _note)
                                # Reset le cache session_state pour afficher la nouvelle note
                                st.session_state[note_key] = _note
                                st.success(f"✅ Note générée ({len(_note)} chars)")
                                st.rerun()
                            except Exception as _e:
                                st.error(f"❌ Erreur: {_e}")

                # Infos dates
                if rec.sent_at:
                    st.markdown(
                        f"<small style='color:#64748b'>Envoyé: {rec.sent_at[:10]}</small>",
                        unsafe_allow_html=True,
                    )
                if rec.accepted_at:
                    st.markdown(
                        f"<small style='color:#16a34a'>Accepté: {rec.accepted_at[:10]}</small>",
                        unsafe_allow_html=True,
                    )


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Envoi
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("📤 Envoi des connexions")

    approved_records = get_records_by_status("approved")
    rem = remaining_today(15)

    # KPIs
    col_k1, col_k2, col_k3, col_k4 = st.columns(4)
    kpis = [
        ("✅ Approuvés", len(approved_records), "#dcfce7", "#166534"),
        ("📤 Restants / jour", rem, "#dbeafe", "#1e40af"),
        ("📨 Envoyés total", get_campaign_stats().get("sent", 0), "#f0f9ff", "#0369a1"),
        ("🤝 Acceptés", get_campaign_stats().get("accepted", 0), "#f0fdf4", "#15803d"),
    ]
    for col, (lbl, val, bg, fg) in zip([col_k1, col_k2, col_k3, col_k4], kpis, strict=False):
        with col:
            st.markdown(
                f"<div class='stat-box' style='background:{bg};border-color:{bg};'>"
                f"<div class='stat-num' style='color:{fg};'>{val}</div>"
                f"<div class='stat-lbl'>{lbl}</div></div>",
                unsafe_allow_html=True,
            )

    st.divider()

    if rem == 0:
        st.warning(
            "⛔ Limite journalière atteinte (15/jour). Les envois reprennent demain.",
            icon="⛔",
        )
    elif not approved_records:
        st.info(
            "📭 Aucun profil approuvé. "
            "Approuve des profils dans l'onglet **Review des Profils** d'abord.",
            icon="📭",
        )
    else:
        to_send = approved_records[:rem]
        st.markdown(
            f"**{len(to_send)} connexion(s) seront envoyées** (limite: {rem} restantes aujourd'hui)"
        )

        # Aperçu des profils à envoyer
        with st.expander("👀 Aperçu des profils à envoyer", expanded=True):
            for rec in to_send[:10]:
                st.markdown(f"- **{rec.name}** ({rec.title} @ {rec.company}) — *{rec.note[:80]}…*")

        st.divider()

        headless_send = st.checkbox(
            "👻 Mode Headless pour l'envoi",
            value=False,
            key="headless_send",
        )

        # Vérification des prérequis — feedback explicite
        missing = []
        if not st.session_state.li_email:
            missing.append("**Email LinkedIn** manquant")
        if not st.session_state.li_password:
            missing.append("**Mot de passe LinkedIn** manquant")

        if missing:
            st.warning(
                "⚠️ Pour envoyer les connexions, renseigne dans la **sidebar** (scroll vers le bas) :\n\n"
                + "\n".join(f"- {m}" for m in missing),
                icon="⚠️",
            )

        col_s1, col_s2 = st.columns([2, 1])
        with col_s1:
            can_send = (
                st.session_state.li_email
                and st.session_state.li_password
                and not st.session_state.out_send_running
                and len(to_send) > 0
                and rem > 0
            )

            if st.button(
                f"🚀 Envoyer {len(to_send)} connexion(s)",
                disabled=not can_send,
                type="primary",
                use_container_width=True,
            ):
                st.session_state.out_send_running = True
                st.session_state.out_send_logs = []

                _email_s = st.session_state.li_email
                _password_s = st.session_state.li_password
                _headless_s = headless_send
                _send_logs = st.session_state.out_send_logs

                def _run_send():
                    from pipelines.outreach_pipeline import OutreachPipeline

                    def cb(msg: str):
                        _send_logs.append(msg)

                    pipeline = OutreachPipeline(daily_limit=15)
                    pipeline.send_approved(
                        email=_email_s,
                        password=_password_s,
                        headless=_headless_s,
                        callback=cb,
                    )
                    st.session_state.out_send_running = False

                t = threading.Thread(target=_run_send, daemon=True)
                t.start()
                st.rerun()

        with col_s2:
            if st.button("🔄 Rafraîchir", use_container_width=True):
                st.rerun()

        # Logs d'envoi
        if st.session_state.out_send_running or st.session_state.out_send_logs:
            st.markdown("### 📡 Logs d'envoi")
            send_html = "<br>".join(st.session_state.out_send_logs[-40:])
            st.markdown(
                f'<div class="log-box">{send_html or "En attente…"}</div>',
                unsafe_allow_html=True,
            )
            if st.session_state.out_send_running:
                time.sleep(1)
                st.rerun()
            else:
                st.success("✅ Envoi terminé !")

    st.divider()

    # ── Suivi des acceptations ────────────────────────────────────────────────
    st.markdown("### 🔍 Suivi des acceptations")

    sent_records = get_records_by_status("sent")
    accepted_total = get_campaign_stats().get("accepted", 0)

    col_acc1, col_acc2, col_acc3 = st.columns(3)
    with col_acc1:
        st.markdown(
            f"<div class='stat-box' style='background:#fef9c3;border-color:#fef9c3;'>"
            f"<div class='stat-num' style='color:#854d0e;'>{len(sent_records)}</div>"
            f"<div class='stat-lbl'>📨 En attente de réponse</div></div>",
            unsafe_allow_html=True,
        )
    with col_acc2:
        st.markdown(
            f"<div class='stat-box' style='background:#dcfce7;border-color:#dcfce7;'>"
            f"<div class='stat-num' style='color:#166534;'>{accepted_total}</div>"
            f"<div class='stat-lbl'>🤝 Acceptées</div></div>",
            unsafe_allow_html=True,
        )
    with col_acc3:
        total_sent = len(sent_records) + accepted_total
        rate = f"{int(accepted_total / total_sent * 100)}%" if total_sent > 0 else "—"
        st.markdown(
            f"<div class='stat-box' style='background:#dbeafe;border-color:#dbeafe;'>"
            f"<div class='stat-num' style='color:#1e40af;'>{rate}</div>"
            f"<div class='stat-lbl'>📈 Taux d'acceptation</div></div>",
            unsafe_allow_html=True,
        )

    st.markdown("")

    if not sent_records:
        st.info(
            "📭 Aucune connexion en statut 'sent' à vérifier. "
            "Lance d'abord l'envoi depuis la section ci-dessus.",
            icon="ℹ️",
        )
    else:
        st.markdown(
            f"ℹ️ Le polling visite chaque profil 'sent' ({len(sent_records)}) "
            f"et détecte si la personne est passée en **1er degré**."
        )

        headless_check = st.checkbox(
            "👻 Mode Headless pour la vérification",
            value=True,
            key="headless_check",
            help="Headless recommandé pour la vérification — plus rapide, moins intrusif",
        )

        col_ch1, col_ch2 = st.columns([2, 1])
        with col_ch1:
            can_check = (
                st.session_state.li_email
                and st.session_state.li_password
                and not st.session_state.out_check_running
                and len(sent_records) > 0
            )
            if st.button(
                f"🔍 Vérifier les {len(sent_records)} connexion(s) envoyée(s)",
                disabled=not can_check,
                use_container_width=True,
            ):
                st.session_state.out_check_running = True
                st.session_state.out_check_logs = []

                _email_c = st.session_state.li_email
                _password_c = st.session_state.li_password
                _headless_c = headless_check
                _check_logs = st.session_state.out_check_logs

                def _run_check():
                    from pipelines.outreach_pipeline import OutreachPipeline

                    def cb(msg: str):
                        _check_logs.append(msg)

                    pipeline = OutreachPipeline(daily_limit=15)
                    pipeline.check_acceptances(
                        email=_email_c,
                        password=_password_c,
                        headless=_headless_c,
                        callback=cb,
                    )
                    st.session_state.out_check_running = False

                t = threading.Thread(target=_run_check, daemon=True)
                t.start()
                st.rerun()

        with col_ch2:
            if st.button("🔄 Rafraîchir stats", key="refresh_check", use_container_width=True):
                st.rerun()

        # Logs de vérification
        if st.session_state.out_check_running or st.session_state.out_check_logs:
            st.markdown("#### 📡 Logs de vérification")
            check_html = "<br>".join(st.session_state.out_check_logs[-40:])
            st.markdown(
                f'<div class="log-box">{check_html or "En attente…"}</div>',
                unsafe_allow_html=True,
            )
            if st.session_state.out_check_running:
                time.sleep(1)
                st.rerun()
            else:
                newly = sum(1 for line in st.session_state.out_check_logs if "ACCEPTÉ" in line)
                if newly > 0:
                    st.success(f"🎉 {newly} nouvelle(s) acceptation(s) détectée(s) !")
                else:
                    st.info(
                        "✅ Vérification terminée — aucune nouvelle acceptation pour l'instant."
                    )
                st.session_state.out_check_logs = []

    st.divider()
    st.markdown("### 📊 Rapport de campagne")

    all_recs = load_records()
    if all_recs:
        import pandas as pd

        df = pd.DataFrame(
            [
                {
                    "Nom": r.name,
                    "Poste": r.title,
                    "Entreprise": r.company,
                    "Statut": r.status,
                    "Campagne": r.campaign_id,
                    "Envoyé le": r.sent_at[:10] if r.sent_at else "",
                    "Accepté le": r.accepted_at[:10] if r.accepted_at else "",
                    "Note": r.note[:60] + "…" if len(r.note) > 60 else r.note,
                }
                for r in all_recs
            ]
        )
        st.dataframe(df, use_container_width=True, height=400)

        # Export CSV
        csv_data = df.to_csv(index=False).encode("utf-8")
        st.download_button(
            "⬇️ Exporter CSV",
            data=csv_data,
            file_name="outreach_report.csv",
            mime="text/csv",
        )
    else:
        st.info("Aucune donnée à afficher pour l'instant.")
