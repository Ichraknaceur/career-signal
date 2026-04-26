"""
Page 1 — Medium Pipeline
Génération d'articles Medium avec agent IA + QA + validation humaine.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from datetime import datetime

import streamlit as st

from core.client import clear_provider_cache
from core.memory import ContentPipelineState, SourceType

st.set_page_config(
    page_title="Medium Pipeline — CareerSignal",
    page_icon="✍️",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
<style>
    .step-badge {
        background: #EEF2FF; color: #4338CA;
        padding: 2px 10px; border-radius: 20px;
        font-size: 12px; font-weight: 600;
        border: 1px solid #C7D2FE;
    }
    .score-good  { color: #16A34A; font-weight: 700; font-size: 24px; }
    .score-ok    { color: #D97706; font-weight: 700; font-size: 24px; }
    .score-bad   { color: #DC2626; font-weight: 700; font-size: 24px; }
    .pill {
        display: inline-block; background: #EEF2FF;
        color: #4338CA; padding: 2px 10px;
        border-radius: 20px; font-size: 12px; margin: 2px;
        border: 1px solid #C7D2FE;
    }
    .published-box {
        background: #F0FDF4; border: 1px solid #86EFAC;
        border-radius: 8px; padding: 16px; margin-top: 12px;
        color: #166534;
    }
    .published-box a { color: #15803D; font-weight: 600; }
</style>
""",
    unsafe_allow_html=True,
)


# ── Session state ─────────────────────────────────────────────────────────────
def init_state():
    defaults = {
        "med_page": "input",
        "med_pipeline_result": None,
        "med_logs": [],
        "med_publish_mode": "dry_run",
        "med_edited_title": "",
        "med_edited_content": "",
        "med_edited_tags": "",
        "med_url_saved": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


init_state()


# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ✍️ Medium Pipeline")
    st.divider()

    # Provider
    st.subheader("🤖 Provider LLM")
    current_provider = os.getenv("LLM_PROVIDER", "anthropic")
    provider_choice = st.radio(
        "Provider",
        options=["anthropic", "openai"],
        index=0 if current_provider == "anthropic" else 1,
        format_func=lambda x: "🟤 Anthropic" if x == "anthropic" else "🟢 OpenAI",
        horizontal=True,
        label_visibility="collapsed",
    )
    if provider_choice != current_provider:
        os.environ["LLM_PROVIDER"] = provider_choice
        clear_provider_cache()
        st.rerun()

    try:
        from core.config import settings

        st.caption(f"Modèle : `{settings.model.agent(provider_choice)}`")
    except Exception:
        pass

    st.divider()

    # Enregistrer article publié
    st.subheader("📰 Enregistrer un article Medium")
    st.caption("Colle l'URL pour que l'agent LinkedIn puisse le promouvoir.")
    with st.form("medium_url_form", clear_on_submit=True):
        med_title = st.text_input("Titre", placeholder="Mon article sur le RAG hybride")
        med_url = st.text_input("URL Medium", placeholder="https://medium.com/@toi/...")
        med_tags = st.text_input("Tags", placeholder="ai, llm, rag")
        if st.form_submit_button("💾 Enregistrer", use_container_width=True):
            if med_url.strip():
                from tools.scheduler_tools import record_medium_publication

                record_medium_publication(
                    title=med_title.strip() or "Article sans titre",
                    url=med_url.strip(),
                    tags=[t.strip() for t in med_tags.split(",") if t.strip()],
                )
                st.success("✅ Enregistré !")
            else:
                st.warning("L'URL est obligatoire.")

    try:
        from tools.scheduler_tools import get_published_medium_articles

        articles = get_published_medium_articles()
        if articles:
            st.caption(f"📚 {len(articles)} article(s) enregistré(s)")
    except Exception:
        pass

    st.divider()

    # Mode de publication
    st.subheader("⚙️ Publication")
    publish_mode = st.radio(
        "Mode",
        ["dry_run", "live"],
        index=0,
        format_func=lambda x: "🧪 Dry Run" if x == "dry_run" else "🚀 Live (réel)",
    )
    st.session_state.med_publish_mode = publish_mode
    if publish_mode == "live":
        st.warning("⚠️ Mode live — publications réelles !")

    st.divider()
    if st.button("🔄 Recommencer", use_container_width=True):
        for k in list(st.session_state.keys()):
            if k.startswith("med_"):
                del st.session_state[k]
        init_state()
        st.rerun()
    if st.button("🏠 Accueil", use_container_width=True):
        st.switch_page("app.py")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE INPUT
# ══════════════════════════════════════════════════════════════════════════════
if st.session_state.med_page == "input":
    st.title("✍️ Générateur d'articles Medium")
    st.caption("Donne un sujet, l'agent écrit l'article complet. Tu valides avant de publier.")
    st.divider()

    col1, col2 = st.columns([2, 1])

    with col1:
        st.subheader("📝 Sujet de l'article")
        subject = st.text_area(
            "Sujet *",
            placeholder="Ex: Comment j'ai réduit les hallucinations LLM de 40% avec du context engineering",
            height=90,
            help="Sois précis. C'est TON sujet — l'agent le respecte tel quel.",
        )

        st.subheader("📎 Source complémentaire (optionnel)")
        source_type = st.selectbox(
            "Type de source",
            options=[s.value for s in SourceType],
            format_func=lambda x: {
                "raw_idea": "💡 Aucune source (idée brute)",
                "github_repo": "🐙 GitHub Repo",
                "arxiv": "📄 Paper arXiv",
                "pdf": "📑 Fichier PDF",
                "url": "🌐 URL web",
            }.get(x, x),
        )

        source_content = ""
        if source_type != "raw_idea":
            placeholders = {
                "github_repo": "owner/repo ou URL GitHub",
                "arxiv": "2301.07041 ou URL arXiv",
                "pdf": "/chemin/vers/article.pdf",
                "url": "https://example.com/article",
            }
            source_content = st.text_input(
                "Contenu source",
                placeholder=placeholders.get(source_type, ""),
            )

    with col2:
        st.subheader("🎯 Paramètres")
        language = st.selectbox(
            "🌍 Langue de l'article",
            options=["French", "English", "Arabic", "Spanish", "German", "Italian", "Portuguese"],
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
        technical_level = st.select_slider(
            "Niveau technique",
            options=["beginner", "intermediate", "expert"],
            value="intermediate",
        )
        max_revisions = st.slider("Révisions QA max", 0, 3, 1)

        st.divider()
        st.subheader("📊 Ce qui va se passer")
        for num, label in [
            ("1", "Lecture source"),
            ("2", "Définition angle"),
            ("3", "Rédaction article"),
            ("4", "Évaluation QA"),
            ("5", "Ta validation"),
            ("6", "Publication"),
        ]:
            st.markdown(
                f'<span class="step-badge">{num}</span> {label}',
                unsafe_allow_html=True,
            )

    st.divider()
    run_disabled = not subject.strip()
    if st.button(
        "🚀 Générer l'article", type="primary", use_container_width=True, disabled=run_disabled
    ):
        st.session_state["med_run_params"] = {
            "subject": subject.strip(),
            "source_type": source_type,
            "source_content": source_content.strip(),
            "technical_level": technical_level,
            "max_revisions": max_revisions,
            "language": language,
        }
        st.session_state.med_page = "running"
        st.session_state.med_logs = []
        st.rerun()

    if run_disabled:
        st.info("💡 Remplis le sujet pour activer la génération.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE RUNNING
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.med_page == "running":
    params = st.session_state.get("med_run_params", {})
    st.title("⚙️ Pipeline en cours...")
    st.caption(f"Sujet : **{params.get('subject', '')}**")
    st.divider()

    try:
        from pipelines.medium_pipeline import MediumPipeline
    except ImportError as e:
        st.error(f"Erreur d'import : {e}")
        st.stop()

    logs_placeholder = st.empty()
    progress_bar = st.progress(0)
    step_weights = {"ingestion": 20, "strategy": 40, "writing": 65, "qa": 85}
    log_lines = []

    def on_step(step: str, message: str, state: ContentPipelineState):
        ts = datetime.now().strftime("%H:%M:%S")
        icon = {"ingestion": "📥", "strategy": "🧠", "writing": "✍️", "qa": "🔍"}.get(step, "•")
        line = f"`{ts}` {icon} **{step.upper()}** — {message}"
        log_lines.append(line)
        st.session_state.med_logs = log_lines.copy()
        logs_placeholder.markdown("\n\n".join(log_lines))
        progress_bar.progress(step_weights.get(step, 0))

    pipeline = MediumPipeline()
    with st.spinner("Le pipeline tourne..."):
        result = pipeline.generate(
            subject=params["subject"],
            source_type=SourceType(params["source_type"]),
            source_content=params["source_content"],
            technical_level=params["technical_level"],
            max_revisions=params["max_revisions"],
            language=params.get("language", "English"),
            callback=on_step,
        )

    progress_bar.progress(100)

    if result.success:
        st.session_state.med_pipeline_result = result
        st.session_state.med_edited_title = result.article_title
        st.session_state.med_edited_content = result.article_content
        st.session_state.med_edited_tags = ", ".join(result.article_tags)
        st.success("✅ Article généré ! Passe à la validation.")
        st.session_state.med_page = "review"
        st.rerun()
    else:
        st.error(f"❌ Erreur pipeline : {result.error}")
        if st.button("← Retour"):
            st.session_state.med_page = "input"
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE REVIEW
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.med_page == "review":
    result = st.session_state.med_pipeline_result
    if not result:
        st.session_state.med_page = "input"
        st.rerun()

    st.title("📋 Validation de l'article")
    st.caption("Lis, modifie si besoin, puis publie.")
    st.divider()

    col_score, col_verdict, col_revisions = st.columns(3)
    with col_score:
        score = result.qa_score
        css = "score-good" if score >= 7.5 else ("score-ok" if score >= 5 else "score-bad")
        st.markdown(
            f'<div class="{css}">{score:.1f}<span style="font-size:14px">/10</span></div>',
            unsafe_allow_html=True,
        )
        st.caption("Score QA")
    with col_verdict:
        verdict = result.state.qa_verdict.value if result.state.qa_verdict else "N/A"
        emoji = "✅" if verdict == "approved" else ("⚠️" if verdict == "needs_revision" else "❌")
        st.metric("Verdict", f"{emoji} {verdict}")
    with col_revisions:
        st.metric("Révisions effectuées", result.state.revision_count)

    if result.qa_feedback:
        with st.expander("💬 Feedback QA"):
            st.markdown(result.qa_feedback)

    st.divider()
    col_edit, col_preview = st.columns([1, 1], gap="large")

    with col_edit:
        st.subheader("✏️ Éditer")
        st.session_state.med_edited_title = st.text_input(
            "Titre", value=st.session_state.med_edited_title
        )
        st.session_state.med_edited_tags = st.text_input(
            "Tags (virgules)", value=st.session_state.med_edited_tags
        )
        st.session_state.med_edited_content = st.text_area(
            "Contenu Markdown", value=st.session_state.med_edited_content, height=500
        )

    with col_preview:
        st.subheader("👁️ Aperçu")
        st.markdown(f"# {st.session_state.med_edited_title}")
        tags_list = [t.strip() for t in st.session_state.med_edited_tags.split(",") if t.strip()]
        st.markdown(
            "".join(f'<span class="pill">{t}</span>' for t in tags_list), unsafe_allow_html=True
        )
        st.divider()
        st.markdown(st.session_state.med_edited_content)

    st.divider()
    wc = len(st.session_state.med_edited_content.split())
    st.caption(f"📝 {wc} mots · {len(st.session_state.med_edited_content)} caractères")

    col1, col2, col3 = st.columns(3)
    with col1:
        if st.button("← Recommencer", use_container_width=True):
            st.session_state.med_page = "input"
            st.rerun()
    with col2:
        full_article = (
            f"# {st.session_state.med_edited_title}\n\n{st.session_state.med_edited_content}"
        )
        st.code(full_article[:200] + "...", language="markdown")
        st.components.v1.html(
            f"""<button onclick="navigator.clipboard.writeText({repr(full_article)}).then(
                () => this.textContent = '✅ Copié !'
            )" style="width:100%;padding:10px;background:#6366F1;color:white;
            border:none;border-radius:6px;cursor:pointer;font-size:14px;">📋 Copier l'article</button>""",
            height=50,
        )
    with col3:
        st.markdown("**Étapes :**")
        st.markdown(
            "1. Copie ← &nbsp; 2. [Medium](https://medium.com/new-story) &nbsp; 3. Colle & publie &nbsp; 4. Reviens ↓"
        )
        if st.button(
            "✅ J'ai publié — enregistrer l'URL", type="primary", use_container_width=True
        ):
            st.session_state.med_page = "register_url"
            st.rerun()


# ══════════════════════════════════════════════════════════════════════════════
# PAGE REGISTER URL
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.med_page == "register_url":
    from tools.scheduler_tools import get_published_medium_articles, record_medium_publication

    title = st.session_state.med_edited_title
    tags = [t.strip() for t in st.session_state.med_edited_tags.split(",") if t.strip()]

    st.title("🔗 Enregistrer l'article publié")
    st.caption("Colle l'URL Medium pour que l'agent LinkedIn puisse le promouvoir.")
    st.divider()

    col_form, col_info = st.columns(2)
    with col_form:
        st.subheader(f"📰 {title}")
        medium_url = st.text_input("URL Medium *", placeholder="https://medium.com/@ton-pseudo/...")
        if st.session_state.med_url_saved:
            st.success("✅ Enregistré ! L'agent LinkedIn peut maintenant le promouvoir.")
            st.balloons()

        c1, c2 = st.columns(2)
        with c1:
            if st.button(
                "💾 Enregistrer",
                type="primary",
                use_container_width=True,
                disabled=not medium_url.strip(),
            ):
                record_medium_publication(title=title, url=medium_url.strip(), tags=tags)
                st.session_state.med_url_saved = True
                st.rerun()
        with c2:
            if st.button("⏭️ Passer", use_container_width=True):
                st.session_state.med_page = "done"
                st.rerun()

    with col_info:
        st.subheader("Pourquoi ?")
        st.markdown(
            "L'URL sera utilisée par l'agent LinkedIn chaque vendredi "
            "(**pilier Promo Medium**) pour créer un post qui attire lecteurs + followers."
        )
        existing = get_published_medium_articles()
        if existing:
            st.divider()
            st.caption(f"📚 {len(existing)} article(s) déjà enregistré(s) :")
            for art in existing[-3:]:
                st.markdown(f"• [{art['title'][:50]}]({art['url']})")

    if st.session_state.med_url_saved:
        st.divider()
        c1, c2 = st.columns(2)
        with c1:
            if st.button("✍️ Nouvel article", type="primary", use_container_width=True):
                for k in list(st.session_state.keys()):
                    if k.startswith("med_"):
                        del st.session_state[k]
                init_state()
                st.rerun()
        with c2:
            if st.button("📅 LinkedIn Scheduling", use_container_width=True):
                st.switch_page("pages/02_LinkedIn_Scheduling.py")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE DONE
# ══════════════════════════════════════════════════════════════════════════════
elif st.session_state.med_page == "done":
    result = st.session_state.med_pipeline_result
    st.title("✍️ Article prêt !")
    st.divider()
    st.info("Article généré. Publie-le sur Medium manuellement, puis reviens enregistrer l'URL.")
    if result:
        with st.expander("📋 Log complet"):
            for entry in result.state.publish_log:
                st.text(entry)
    st.divider()
    c1, c2 = st.columns(2)
    with c1:
        if st.button("✍️ Nouvel article", type="primary", use_container_width=True):
            for k in list(st.session_state.keys()):
                if k.startswith("med_"):
                    del st.session_state[k]
            init_state()
            st.rerun()
    with c2:
        if st.button("📅 LinkedIn Scheduling", use_container_width=True):
            st.switch_page("pages/02_LinkedIn_Scheduling.py")
