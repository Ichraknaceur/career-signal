"""
Page 2 — LinkedIn Scheduling (Phase 2 + Publication Phase 3)

Flux :
  1. Formulaire : niche + audience + nb_weeks + contexte
  2. Génération du calendrier via LinkedInSchedulingPipeline
  3. Calendrier éditorial : vue semaine × jour (Mon/Wed/Fri)
  4. Par post : éditer le contenu, approuver, rejeter
  5. Publication via Playwright — bouton actif pour les posts approuvés
"""

from __future__ import annotations

import asyncio
import os
import sys
import threading
import time
from datetime import date
from datetime import time as time_value

# ── Ajouter la racine du projet au path (même fix que app.py) ────────────────
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import streamlit as st

# ── Config page ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="LinkedIn Scheduling — CareerSignal",
    page_icon="💼",
    layout="wide",
)

# ── Imports pipeline ─────────────────────────────────────────────────────────
from core.client import clear_provider_cache  # noqa: E402
from pipelines.linkedin_scheduling_pipeline import LinkedInSchedulingPipeline  # noqa: E402
from tools.scheduler_tools import (  # noqa: E402
    DEFAULT_PUBLISH_TIMES,
    PILLAR_LABELS,
    ScheduledPost,
    delete_post,
    get_weeks_summary,
    load_posts,
    load_prompt_profile,
    save_prompt_profile,
    update_post_content,
    update_post_schedule,
    update_post_status,
)

STATUS_BADGE = {
    "draft": "🟡 Draft",
    "approved": "✅ Approuvé",
    "rejected": "❌ Rejeté",
    "published": "🚀 Publié",
}

# CSS palette claire
st.markdown(
    """
<style>
    /* Cards post */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: #FAFAFA;
        border: 1px solid #E5E7EB !important;
        border-radius: 10px;
    }
    /* Compteur caractères */
    .char-ok  { color: #16A34A; font-size: 12px; }
    .char-bad { color: #DC2626; font-size: 12px; }
</style>
""",
    unsafe_allow_html=True,
)


def _badge(status: str) -> str:
    return STATUS_BADGE.get(status, status)


def _init_state() -> None:
    prompt_profile = load_prompt_profile()
    defaults = {
        "li_page": "input",
        "li_logs": [],
        "li_result": None,
        "li_niche": "",
        "li_audience": "",
        "li_nb_weeks": 2,
        "li_context": "",
        "li_language": "English",
        "li_start_date": date.today(),
        "li_publish_time_monday": DEFAULT_PUBLISH_TIMES["monday"],
        "li_publish_time_wednesday": DEFAULT_PUBLISH_TIMES["wednesday"],
        "li_publish_time_friday": DEFAULT_PUBLISH_TIMES["friday"],
        "li_prompt_global": prompt_profile["global_prompt"],
        "li_prompt_voice": prompt_profile["voice_and_tone"],
        "li_prompt_cta": prompt_profile["cta_style"],
        "li_prompt_expertise_ia": prompt_profile["pillar_prompts"]["expertise_ia"],
        "li_prompt_projets": prompt_profile["pillar_prompts"]["projets"],
        "li_prompt_promo_medium": prompt_profile["pillar_prompts"]["promo_medium"],
        # Credentials partagés avec page 03 via session_state
        "li_email": os.getenv("LINKEDIN_EMAIL", ""),
        "li_password": os.getenv("LINKEDIN_PASSWORD", ""),
        # Publication en cours
        "li_pub_running": False,
        "li_pub_logs": [],
        "li_pub_post_id": None,  # ID du post en cours de publication
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _format_day_label(day_name: str) -> str:
    return {
        "monday": "Lundi",
        "tuesday": "Mardi",
        "wednesday": "Mercredi",
        "thursday": "Jeudi",
        "friday": "Vendredi",
        "saturday": "Samedi",
        "sunday": "Dimanche",
    }.get(day_name.lower(), day_name.title())


def _build_prompt_profile_from_state() -> dict:
    return {
        "global_prompt": st.session_state.li_prompt_global,
        "voice_and_tone": st.session_state.li_prompt_voice,
        "cta_style": st.session_state.li_prompt_cta,
        "pillar_prompts": {
            "expertise_ia": st.session_state.li_prompt_expertise_ia,
            "projets": st.session_state.li_prompt_projets,
            "promo_medium": st.session_state.li_prompt_promo_medium,
        },
    }


# ── Publication via Playwright ────────────────────────────────────────────────
def _trigger_publish(post: ScheduledPost) -> None:
    """Lance la publication dans un thread dédié."""
    st.session_state.li_pub_running = True
    st.session_state.li_pub_logs = []
    st.session_state.li_pub_post_id = post.id

    _email = st.session_state.li_email
    _password = st.session_state.li_password
    _content = post.content
    _hashtags = post.hashtags
    _post_id = post.id
    _logs_ref = st.session_state.li_pub_logs

    def _run():
        from tools.linkedin_poster import publish_post_with_session

        _logs_ref.append("🔐 Connexion à LinkedIn…")
        try:
            success = asyncio.run(
                publish_post_with_session(
                    email=_email,
                    password=_password,
                    content=_content,
                    hashtags=_hashtags,
                    headless=False,
                )
            )
            if success:
                update_post_status(_post_id, "published")
                _logs_ref.append("✅ Post publié avec succès !")
            else:
                _logs_ref.append(
                    "❌ Échec de la publication — vérifie les credentials ou réessaie manuellement."
                )
        except Exception as e:
            _logs_ref.append(f"❌ Erreur: {e}")
        finally:
            st.session_state.li_pub_running = False

    threading.Thread(target=_run, daemon=True).start()
    st.rerun()


def _bulk_publish(posts: list[ScheduledPost]) -> None:
    """
    Publie tous les posts approuvés un par un dans un thread unique.
    Utilise une session browser partagée (plus efficace que N sessions).
    """
    if not posts:
        return

    st.session_state.li_pub_running = True
    st.session_state.li_pub_logs = []

    _email = st.session_state.li_email
    _password = st.session_state.li_password
    _post_data = [(p.id, p.content, p.hashtags) for p in posts]
    _logs_ref = st.session_state.li_pub_logs

    def _run():
        import asyncio as _asyncio

        from tools.linkedin_poster import post_to_linkedin
        from tools.linkedin_scraper import (
            create_browser_context,
            login_linkedin,
            restore_session,
        )

        async def _async_bulk():
            pw, browser, context, page = await create_browser_context(headless=False)
            try:
                _logs_ref.append("🔐 Connexion à LinkedIn…")
                session_ok = await restore_session(page)
                if not session_ok:
                    login_ok = await login_linkedin(page, _email, _password)
                    if not login_ok:
                        _logs_ref.append("❌ Authentification échouée")
                        return

                for i, (post_id, content, hashtags) in enumerate(_post_data, 1):
                    _logs_ref.append(f"\n📤 [{i}/{len(_post_data)}] Publication en cours…")
                    try:
                        ok = await post_to_linkedin(page, content, hashtags)
                        if ok:
                            update_post_status(post_id, "published")
                            _logs_ref.append("   ✅ Publié !")
                        else:
                            _logs_ref.append("   ❌ Échec — post skippé")
                    except Exception as e:
                        _logs_ref.append(f"   ❌ Erreur: {e}")

                    # Délai entre chaque post (éviter le spam détecté)
                    if i < len(_post_data):
                        import asyncio as _ac

                        await _ac.sleep(5)

            finally:
                await browser.close()
                await pw.stop()

        _asyncio.run(_async_bulk())
        st.session_state.li_pub_running = False
        _logs_ref.append(f"\n✅ Bulk publish terminé — {len(_post_data)} posts traités")

    threading.Thread(target=_run, daemon=True).start()
    st.rerun()


# ── Composant carte post ──────────────────────────────────────────────────────
def render_post_card(post: ScheduledPost) -> None:
    """Affiche une carte post avec éditeur inline et actions."""
    pillar_label = PILLAR_LABELS.get(post.pillar, post.pillar)
    status_badge = _badge(post.status)

    with st.container(border=True):
        # Header
        header_col, status_col = st.columns([2, 1])
        with header_col:
            st.caption(f"{pillar_label} · 📆 {post.scheduled_date} · 🕒 {post.scheduled_time}")
        with status_col:
            st.caption(status_badge)

        # Lien Medium si promo_medium
        if post.medium_article_url:
            st.caption(
                f"📰 [{post.medium_article_title or 'Article Medium'}]({post.medium_article_url})"
            )

        if post.status != "published":
            # ── Éditeur inline ──────────────────────────────────────────────
            sched_col1, sched_col2 = st.columns(2)
            with sched_col1:
                edited_date = st.date_input(
                    "Date",
                    value=date.fromisoformat(post.scheduled_date),
                    key=f"date_{post.id}",
                )
            with sched_col2:
                edited_time = st.time_input(
                    "Heure",
                    value=time_value.fromisoformat(post.scheduled_time),
                    key=f"time_{post.id}",
                    step=1800,
                )

            edited_content = st.text_area(
                "Contenu",
                value=post.content,
                key=f"content_{post.id}",
                height=200,
                label_visibility="collapsed",
            )
            edited_hashtags_raw = st.text_input(
                "Hashtags",
                value=" ".join(post.hashtags),
                key=f"hashtags_{post.id}",
                placeholder="#ai #genai #mlops",
                label_visibility="collapsed",
            )
            hashtags_parsed = [
                h if h.startswith("#") else f"#{h}"
                for h in edited_hashtags_raw.split()
                if h.strip()
            ]

            # Compteur de caractères
            char_count = len(edited_content)
            char_icon = "🔴" if char_count > 1300 else "🟢"
            st.caption(f"{char_icon} {char_count}/1300 caractères")

            def _save_post_edits() -> None:
                update_post_content(post.id, edited_content, hashtags_parsed)
                update_post_schedule(
                    post.id,
                    edited_date.isoformat(),
                    edited_time.strftime("%H:%M"),
                )

            # Boutons action
            btn_col1, btn_col2, btn_col3, btn_col4 = st.columns(4)
            with btn_col1:
                if st.button("💾 Sauver", key=f"save_{post.id}", use_container_width=True):
                    _save_post_edits()
                    st.success("Sauvegardé !")
                    st.rerun()

            with btn_col2:
                if post.status == "approved":
                    if st.button(
                        "🚀 Publier",
                        key=f"publish_{post.id}",
                        use_container_width=True,
                        type="primary",
                        disabled=(
                            not bool(
                                st.session_state.get("li_email")
                                and st.session_state.get("li_password")
                            )
                            or st.session_state.li_pub_running
                        ),
                    ):
                        _save_post_edits()
                        refreshed_post = next((p for p in load_posts() if p.id == post.id), post)
                        _trigger_publish(refreshed_post)
                else:
                    if st.button(
                        "✅ Approuver",
                        key=f"approve_{post.id}",
                        use_container_width=True,
                        type="primary",
                    ):
                        _save_post_edits()
                        update_post_status(post.id, "approved")
                        st.rerun()

            with btn_col3:
                action_label = "↩️ Brouillon" if post.status == "rejected" else "❌ Rejeter"
                target_status = "draft" if post.status == "rejected" else "rejected"
                if st.button(action_label, key=f"status_{post.id}", use_container_width=True):
                    _save_post_edits()
                    update_post_status(post.id, target_status)
                    st.rerun()

            with btn_col4:
                if st.button("🗑️ Suppr.", key=f"del_{post.id}", use_container_width=True):
                    delete_post(post.id)
                    st.rerun()

        else:
            # ── Vue publiée ────────────────────────────────────────────────
            st.markdown(f"```\n{post.content}\n```")
            if post.hashtags:
                st.caption(" ".join(post.hashtags))
            st.success(f"✅ Publié le {post.published_at or 'N/A'}")


# ── Router principal ──────────────────────────────────────────────────────────
_init_state()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    # ── Provider LLM ─────────────────────────────────────────────────────────
    st.subheader("🤖 Provider LLM")
    current_provider = os.getenv("LLM_PROVIDER", "anthropic")
    provider_choice = st.radio(
        "Provider",
        options=["anthropic", "openai"],
        index=0 if current_provider == "anthropic" else 1,
        format_func=lambda x: "🟤 Anthropic (Claude)" if x == "anthropic" else "🟢 OpenAI (GPT)",
        horizontal=True,
        label_visibility="collapsed",
    )
    if provider_choice != current_provider:
        os.environ["LLM_PROVIDER"] = provider_choice
        clear_provider_cache()
        st.rerun()

    from core.config import settings

    st.caption(f"Modèle agent : `{settings.model.agent(provider_choice)}`")

    st.divider()

    # ── Credentials LinkedIn (pour publication) ───────────────────────────────
    st.subheader("🔐 LinkedIn — Publication")
    st.caption("Requis pour publier les posts approuvés via Playwright.")
    st.caption("Si `LINKEDIN_EMAIL` et `LINKEDIN_PASSWORD` sont présents dans `.env`, ils sont chargés automatiquement.")

    li_email_val = st.text_input(
        "Email LinkedIn",
        value=st.session_state.li_email,
        key="sb_li_email",
        placeholder="toi@example.com",
    )
    li_pwd_val = st.text_input(
        "Mot de passe",
        value=st.session_state.li_password,
        type="password",
        key="sb_li_pwd",
    )
    # Sync dans session_state
    st.session_state.li_email = li_email_val
    st.session_state.li_password = li_pwd_val

    if li_email_val and li_pwd_val:
        st.success("✅ Credentials prêts")
    else:
        st.warning("⚠️ Email / mot de passe requis pour publier")

    # ── Logs de publication en temps réel ─────────────────────────────────────
    if st.session_state.li_pub_running or st.session_state.li_pub_logs:
        st.divider()
        st.subheader("📡 Publication")
        if st.session_state.li_pub_running:
            st.spinner("⏳ Publication en cours…")
        for log_line in st.session_state.li_pub_logs[-10:]:
            if "✅" in log_line:
                st.success(log_line)
            elif "❌" in log_line:
                st.error(log_line)
            else:
                st.caption(log_line)
        if st.session_state.li_pub_running:
            import time as _time

            _time.sleep(1)
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE : INPUT
# ─────────────────────────────────────────────────────────────────────────────
if st.session_state.li_page == "input":
    st.title("💼 LinkedIn Scheduling")
    st.caption("Génère ton calendrier éditorial LinkedIn — 3 posts/semaine, Mon/Mer/Ven")
    st.divider()

    with st.form("li_form"):
        col1, col2 = st.columns(2)

        with col1:
            niche = st.text_area(
                "🎯 Niche / Thématiques",
                placeholder="ex: IA appliquée, Gen AI, MLOps, systèmes multi-agents",
                height=100,
                help="Les sujets principaux que tu traites dans ton contenu.",
            )
            audience = st.text_area(
                "👥 Audience cible",
                placeholder="ex: ingénieurs IA, recruteurs tech, fondateurs de startups, CTOs",
                height=100,
                help="Qui va lire tes posts ? Sois précis.",
            )

        with col2:
            language = st.selectbox(
                "🌍 Langue des posts",
                options=[
                    "French",
                    "English",
                    "Arabic",
                    "Spanish",
                    "German",
                    "Italian",
                    "Portuguese",
                ],
                index=1,
                format_func=lambda x: {
                    "French": "🇫🇷 Français",
                    "English": "🇬🇧 English",
                    "Arabic": "🇸🇦 العربية",
                    "Spanish": "🇪🇸 Español",
                    "German": "🇩🇪 Deutsch",
                    "Italian": "🇮🇹 Italiano",
                    "Portuguese": "🇧🇷 Português",
                }.get(x, x),
            )
            nb_weeks = st.slider(
                "📅 Nombre de semaines",
                min_value=1,
                max_value=4,
                value=st.session_state.li_nb_weeks,
                help="1 semaine = 3 posts (Lun/Mer/Ven). Max 4 semaines = 12 posts.",
            )
            start_date_value = st.date_input(
                "🗓️ Date de départ du calendrier",
                value=st.session_state.li_start_date,
                help="Le calendrier sera généré à partir de cette date de départ.",
            )
            context = st.text_area(
                "💡 Contexte libre (optionnel)",
                placeholder=(
                    "Projets récents, expériences à partager, idées de posts...\n"
                    "ex: Je build un système multi-agents avec Anthropic SDK, "
                    "j'ai réduit les hallucinations de 40% avec du RAG hybride..."
                ),
                height=150,
                help="Donne des éléments concrets pour des posts plus authentiques.",
            )

        with st.expander("🕒 Horaires de publication", expanded=False):
            time_col1, time_col2, time_col3 = st.columns(3)
            with time_col1:
                monday_time = st.time_input(
                    "Lundi",
                    value=time_value.fromisoformat(st.session_state.li_publish_time_monday),
                    step=1800,
                )
            with time_col2:
                wednesday_time = st.time_input(
                    "Mercredi",
                    value=time_value.fromisoformat(st.session_state.li_publish_time_wednesday),
                    step=1800,
                )
            with time_col3:
                friday_time = st.time_input(
                    "Vendredi",
                    value=time_value.fromisoformat(st.session_state.li_publish_time_friday),
                    step=1800,
                )

        with st.expander("🧠 Prompts utilisés en background", expanded=False):
            prompt_global = st.text_area(
                "Global prompt",
                value=st.session_state.li_prompt_global,
                height=90,
                help="Règles globales appliquées à tous les posts générés.",
            )
            voice_prompt = st.text_area(
                "Voice and tone",
                value=st.session_state.li_prompt_voice,
                height=90,
                help="Style rédactionnel de fond utilisé par le générateur.",
            )
            cta_prompt = st.text_area(
                "CTA style",
                value=st.session_state.li_prompt_cta,
                height=70,
                help="Style d'appel à l'action appliqué à la fin des posts.",
            )
            pillar_col1, pillar_col2, pillar_col3 = st.columns(3)
            with pillar_col1:
                prompt_expertise = st.text_area(
                    "Prompt pillar · expertise_ia",
                    value=st.session_state.li_prompt_expertise_ia,
                    height=180,
                )
            with pillar_col2:
                prompt_projets = st.text_area(
                    "Prompt pillar · projets",
                    value=st.session_state.li_prompt_projets,
                    height=180,
                )
            with pillar_col3:
                prompt_promo = st.text_area(
                    "Prompt pillar · promo_medium",
                    value=st.session_state.li_prompt_promo_medium,
                    height=180,
                )

        st.caption(
            f"📊 **Récap** : {nb_weeks} semaine(s) → **{nb_weeks * 3} posts** à générer "
            f"(🧠 Expertise IA × {nb_weeks} · 🛠️ Projets × {nb_weeks} · 📣 Promo Medium × {nb_weeks})"
        )

        submitted = st.form_submit_button(
            f"🚀 Générer {nb_weeks * 3} posts LinkedIn",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        if not niche.strip():
            st.error("❌ La niche est obligatoire.")
        elif not audience.strip():
            st.error("❌ L'audience cible est obligatoire.")
        else:
            st.session_state.li_niche = niche
            st.session_state.li_audience = audience
            st.session_state.li_nb_weeks = nb_weeks
            st.session_state.li_context = context
            st.session_state.li_language = language
            st.session_state.li_start_date = start_date_value
            st.session_state.li_publish_time_monday = monday_time.strftime("%H:%M")
            st.session_state.li_publish_time_wednesday = wednesday_time.strftime("%H:%M")
            st.session_state.li_publish_time_friday = friday_time.strftime("%H:%M")
            st.session_state.li_prompt_global = prompt_global
            st.session_state.li_prompt_voice = voice_prompt
            st.session_state.li_prompt_cta = cta_prompt
            st.session_state.li_prompt_expertise_ia = prompt_expertise
            st.session_state.li_prompt_projets = prompt_projets
            st.session_state.li_prompt_promo_medium = prompt_promo
            save_prompt_profile(_build_prompt_profile_from_state())
            st.session_state.li_logs = []
            st.session_state.li_result = None
            st.session_state.li_page = "running"
            st.rerun()

    # Accès rapide au calendrier existant
    existing = load_posts()
    if existing:
        st.divider()
        st.subheader(f"📅 Calendrier existant ({len(existing)} posts)")
        if st.button("📋 Voir le calendrier", use_container_width=True):
            st.session_state.li_page = "calendar"
            st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE : RUNNING
# ─────────────────────────────────────────────────────────────────────────────
elif st.session_state.li_page == "running":
    st.title("⚙️ Génération en cours...")
    st.caption(
        f"Génération de **{st.session_state.li_nb_weeks * 3} posts** pour ta niche : "
        f"*{st.session_state.li_niche[:80]}*"
    )

    progress_bar = st.progress(0, text="Démarrage du pipeline...")
    log_container = st.empty()

    # ⚠️ Capturer TOUTES les valeurs de session_state ICI, dans le thread principal,
    # avant de lancer le thread — st.session_state n'est pas accessible depuis un thread.
    _niche = st.session_state.li_niche
    _audience = st.session_state.li_audience
    _nb_weeks = st.session_state.li_nb_weeks
    _context = st.session_state.li_context
    _language = st.session_state.get("li_language", "English")
    _start_date = st.session_state.get("li_start_date", date.today())
    _publish_times = {
        "monday": st.session_state.get("li_publish_time_monday", DEFAULT_PUBLISH_TIMES["monday"]),
        "wednesday": st.session_state.get(
            "li_publish_time_wednesday", DEFAULT_PUBLISH_TIMES["wednesday"]
        ),
        "friday": st.session_state.get("li_publish_time_friday", DEFAULT_PUBLISH_TIMES["friday"]),
    }
    _prompt_profile = _build_prompt_profile_from_state()
    _logs_ref = st.session_state.li_logs  # référence mutable partagée

    total_expected = _nb_weeks * 3

    def on_log(msg: str) -> None:
        _logs_ref.append(msg)

    pipeline = LinkedInSchedulingPipeline()
    result_holder: dict = {}
    error_holder: dict = {}

    def run_pipeline() -> None:
        try:
            result_holder["result"] = pipeline.generate(
                niche=_niche,
                audience=_audience,
                nb_weeks=_nb_weeks,
                context=_context,
                language=_language,
                start_date=_start_date,
                publish_times=_publish_times,
                prompt_profile=_prompt_profile,
                callback=on_log,
            )
        except Exception as e:
            error_holder["error"] = str(e)

    thread = threading.Thread(target=run_pipeline, daemon=True)
    thread.start()

    # Polling live logs — utilise _logs_ref (capturé avant le thread)
    while thread.is_alive():
        n_done = sum(1 for ln in _logs_ref if "✅ Post généré" in ln)
        progress = min(n_done / max(total_expected, 1), 0.95)
        progress_bar.progress(progress, text=f"Posts générés : {n_done}/{total_expected}...")
        log_container.code(
            "\n".join(_logs_ref[-25:]) if _logs_ref else "Initialisation...", language=""
        )
        time.sleep(1.5)

    thread.join()

    if "error" in error_holder:
        progress_bar.empty()
        st.error(f"❌ Erreur pipeline : {error_holder['error']}")
        if st.button("← Retour"):
            st.session_state.li_page = "input"
            st.rerun()

    elif "result" in result_holder:
        result = result_holder["result"]
        st.session_state.li_result = result
        progress_bar.progress(1.0, text="✅ Génération terminée !")
        log_container.code("\n".join(_logs_ref[-25:]), language="")

        if result.success:
            st.success(
                f"✅ {result.total_posts} posts générés et sauvegardés dans data/schedule.json !"
            )
            st.balloons()
        else:
            st.warning(f"⚠️ {result.total_posts}/{total_expected} posts générés.")
            for err in result.errors:
                st.error(err)

        time.sleep(1.5)
        st.session_state.li_page = "calendar"
        st.rerun()

# ─────────────────────────────────────────────────────────────────────────────
# PAGE : CALENDAR
# ─────────────────────────────────────────────────────────────────────────────
elif st.session_state.li_page == "calendar":
    st.title("📅 Calendrier éditorial LinkedIn")

    top_col1, top_col2, top_col3, top_col4 = st.columns([1, 1, 1, 3])
    with top_col1:
        if st.button("← Retour"):
            st.session_state.li_page = "input"
            st.rerun()
    with top_col2:
        if st.button("🔄 Générer plus"):
            st.session_state.li_page = "input"
            st.rerun()
    with top_col3:
        # Bouton "Tout publier" — publie tous les posts approuvés un par un
        approved_posts = [p for p in load_posts() if p.status == "approved"]
        has_creds = bool(st.session_state.get("li_email") and st.session_state.get("li_password"))
        if st.button(
            f"🚀 Publier tous ({len(approved_posts)})",
            disabled=not has_creds or st.session_state.li_pub_running or not approved_posts,
            help="Publie tous les posts approuvés un par un via Playwright",
        ):
            _bulk_publish(approved_posts)
    with top_col4:
        all_posts_preview = load_posts()
        draft_n = sum(1 for p in all_posts_preview if p.status == "draft")
        approved_n = sum(1 for p in all_posts_preview if p.status == "approved")
        rejected_n = sum(1 for p in all_posts_preview if p.status == "rejected")
        published_n = sum(1 for p in all_posts_preview if p.status == "published")
        st.caption(
            f"**Total : {len(all_posts_preview)} posts** · "
            f"🟡 {draft_n} draft · ✅ {approved_n} approuvé · "
            f"❌ {rejected_n} rejeté · 🚀 {published_n} publié"
        )

    # Stats globales
    all_posts = load_posts()
    if not all_posts:
        st.info("Aucun post planifié. Lance une génération depuis le formulaire !")
        st.stop()

    st.divider()

    # Organisation par semaine
    weeks_summary = get_weeks_summary()
    sorted_weeks = sorted(weeks_summary.keys())

    if not sorted_weeks:
        st.info("Aucun post trouvé.")
        st.stop()

    week_tabs = st.tabs([f"Semaine {w}" for w in sorted_weeks])

    for tab, week_num in zip(week_tabs, sorted_weeks, strict=False):
        with tab:
            week_posts: list[ScheduledPost] = weeks_summary[week_num]["posts"]
            posts_by_date: dict[str, list[ScheduledPost]] = {}
            for post in sorted(
                week_posts,
                key=lambda item: (item.scheduled_date, item.scheduled_time, item.created_at),
            ):
                posts_by_date.setdefault(post.scheduled_date, []).append(post)

            for scheduled_date, day_posts in posts_by_date.items():
                first_post = day_posts[0]
                st.markdown(
                    f"#### {_format_day_label(first_post.day_of_week)} · {scheduled_date} · "
                    f"{len(day_posts)} post(s)"
                )
                for post in day_posts:
                    render_post_card(post)
