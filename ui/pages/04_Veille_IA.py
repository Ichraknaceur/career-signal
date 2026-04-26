"""
Page 4 — Veille IA.

Workflow :
  1. Gérer les sources RSS (ajouter, activer/désactiver, supprimer)
  2. Lancer le scraping + résumés LLM
  3. Review des articles : lire, ignorer, envoyer au scheduler LinkedIn

Phase 4 de CareerSignal.
"""

from __future__ import annotations

import os
import sys
import threading
import time
import uuid

sys.path.insert(
    0,
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
)

import streamlit as st

from tools.veille_store import (
    VeilleSource,
    add_source,
    delete_source,
    get_articles,
    get_sources,
    get_veille_stats,
    seed_default_sources,
    toggle_source,
    update_article,
    update_article_status,
)

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Veille IA",
    page_icon="📡",
    layout="wide",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
  .article-card {
    background:#fff;border:1px solid #e2e8f0;border-radius:12px;
    padding:18px 20px;margin-bottom:14px;
    box-shadow:0 1px 4px rgba(0,0,0,0.06);
  }
  .badge-new      { background:#dbeafe;color:#1e40af;border-radius:8px;padding:2px 10px;font-size:12px;font-weight:600; }
  .badge-read     { background:#f0fdf4;color:#15803d;border-radius:8px;padding:2px 10px;font-size:12px;font-weight:600; }
  .badge-used     { background:#f0f9ff;color:#0369a1;border-radius:8px;padding:2px 10px;font-size:12px;font-weight:600; }
  .badge-ignored  { background:#f1f5f9;color:#94a3b8;border-radius:8px;padding:2px 10px;font-size:12px;font-weight:600; }
  .stat-box { background:#f8fafc;border-radius:10px;padding:14px 10px;text-align:center;border:1px solid #e2e8f0; }
  .stat-num { font-size:28px;font-weight:700;color:#4338CA; }
  .stat-lbl { font-size:12px;color:#64748b;margin-top:2px; }
  .log-box  { background:#1e1e2e;color:#a8ff78;border-radius:8px;
               padding:14px;font-family:monospace;font-size:12px;
               max-height:300px;overflow-y:auto; }
  .source-row { display:flex;align-items:center;gap:10px;
                padding:10px 14px;border:1px solid #e2e8f0;
                border-radius:10px;margin-bottom:8px;background:#fafafa; }
</style>
""",
    unsafe_allow_html=True,
)


# ── Session state ─────────────────────────────────────────────────────────────
def _init():
    defaults = {
        "veille_running": False,
        "veille_logs": [],
        "veille_enrich_running": False,
        "veille_enrich_logs": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init()

# Seed des sources par défaut au premier lancement
_seeded = seed_default_sources()
if _seeded:
    st.toast(f"✅ {_seeded} sources par défaut ajoutées !", icon="📡")

# ── Sidebar — Stats globales ──────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 📊 Stats")
    stats = get_veille_stats()
    for label, key, color in [
        ("📄 Total articles", "total", "#4338CA"),
        ("🆕 Nouveaux", "new", "#1e40af"),
        ("✅ Résumés", "with_summary", "#15803d"),
        ("📣 Posts générés", "with_post", "#0369a1"),
        ("♻️ Utilisés", "used", "#854d0e"),
    ]:
        st.markdown(
            f"<div style='display:flex;justify-content:space-between;padding:4px 0;'>"
            f"<span style='color:#64748b'>{label}</span>"
            f"<strong style='color:{color}'>{stats.get(key, 0)}</strong></div>",
            unsafe_allow_html=True,
        )

    st.divider()
    st.markdown("### ⚙️ Provider LLM")
    from core.client import clear_provider_cache
    from core.config import settings as _settings

    current_provider = os.getenv("LLM_PROVIDER", "anthropic")
    provider_choice = st.radio(
        "Provider",
        options=["anthropic", "openai"],
        index=0 if current_provider == "anthropic" else 1,
        format_func=lambda x: "🟤 Anthropic" if x == "anthropic" else "🟢 OpenAI",
        horizontal=True,
        key="veille_provider",
    )
    if provider_choice != current_provider:
        os.environ["LLM_PROVIDER"] = provider_choice
        clear_provider_cache()
        st.rerun()
    st.caption(f"`{_settings.model.agent(provider_choice)}`")


# ── Titre ─────────────────────────────────────────────────────────────────────
st.title("📡 Veille IA — Phase 4")
st.markdown(
    "Surveille des flux RSS IA/LLM/RAG, génère des résumés automatiques "
    "et propose des posts LinkedIn prêts à publier."
)

tab1, tab2, tab3 = st.tabs(["🔧 Sources", "📄 Articles", "📣 Posts suggérés"])


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 1 — Gestion des sources
# ═══════════════════════════════════════════════════════════════════════════════
with tab1:
    st.subheader("🔧 Sources RSS / Web")

    # ── Lancement du scraping ─────────────────────────────────────────────────
    col_run1, col_run2, col_run3 = st.columns([2, 1, 1])

    with col_run1:
        max_per_source = st.slider(
            "Articles max par source", min_value=3, max_value=20, value=8, step=1
        )
    with col_run2:
        gen_summaries = st.checkbox("Résumés LLM", value=True)
    with col_run3:
        gen_posts = st.checkbox("Posts LinkedIn", value=True)

    col_btn1, col_btn2 = st.columns([3, 1])
    with col_btn1:
        if st.button(
            "🚀 Lancer la veille (toutes les sources)",
            type="primary",
            disabled=st.session_state.veille_running,
            use_container_width=True,
        ):
            st.session_state.veille_running = True
            st.session_state.veille_logs = []
            _logs = st.session_state.veille_logs
            _max = max_per_source
            _gen_s = gen_summaries
            _gen_p = gen_posts

            def _run_veille():
                from pipelines.veille_pipeline import VeillePipeline

                pipeline = VeillePipeline(
                    generate_summaries=_gen_s,
                    generate_posts=_gen_p,
                )
                pipeline.run(max_per_source=_max, callback=lambda m: _logs.append(m))
                st.session_state.veille_running = False

            threading.Thread(target=_run_veille, daemon=True).start()
            st.rerun()

    with col_btn2:
        if st.button("🔄 Rafraîchir", use_container_width=True):
            st.rerun()

    # Logs
    if st.session_state.veille_running or st.session_state.veille_logs:
        logs_html = "<br>".join(st.session_state.veille_logs[-60:])
        st.markdown(
            f'<div class="log-box">{logs_html or "En attente…"}</div>',
            unsafe_allow_html=True,
        )
        if st.session_state.veille_running:
            time.sleep(1)
            st.rerun()
        else:
            new_count = sum(
                1 for log_line in st.session_state.veille_logs if "sauvegardé" in log_line
            )
            st.success("✅ Veille terminée — passe à l'onglet **Articles** !")

    st.divider()

    # ── Liste des sources ─────────────────────────────────────────────────────
    st.subheader("📋 Sources configurées")
    sources = get_sources()

    if not sources:
        st.info("Aucune source configurée. Les sources par défaut sont chargées au démarrage.")
    else:
        for src in sources:
            col_a, col_b, col_c, col_d, col_e = st.columns([3, 1, 1, 1, 1])
            with col_a:
                status_icon = "🟢" if src.active else "⚫"
                st.markdown(
                    f"{status_icon} **{src.name}**  \n"
                    f"<small style='color:#64748b'>{src.url[:55]}…</small>",
                    unsafe_allow_html=True,
                )
            with col_b:
                st.markdown(
                    f"<span style='background:#e0e7ff;color:#3730a3;"
                    f"border-radius:6px;padding:2px 8px;font-size:11px'>"
                    f"{src.category}</span>",
                    unsafe_allow_html=True,
                )
            with col_c:
                st.markdown(
                    f"<small style='color:#64748b'>{'📡 RSS' if src.rss else '🌐 Web'}</small>",
                    unsafe_allow_html=True,
                )
            with col_d:
                btn_label = "⏸ Pause" if src.active else "▶ Activer"
                if st.button(btn_label, key=f"toggle_{src.id}", use_container_width=True):
                    toggle_source(src.id)
                    st.rerun()
            with col_e:
                if st.button("🗑", key=f"del_{src.id}", help="Supprimer cette source"):
                    delete_source(src.id)
                    st.rerun()

    st.divider()

    # ── Ajouter une source ────────────────────────────────────────────────────
    st.subheader("➕ Ajouter une source")
    with st.form("add_source_form", clear_on_submit=True):
        col_f1, col_f2 = st.columns(2)
        with col_f1:
            new_name = st.text_input("Nom de la source", placeholder="ex: MIT AI Blog")
            new_url = st.text_input(
                "URL du flux RSS",
                placeholder="https://example.com/feed.xml",
            )
        with col_f2:
            new_category = st.selectbox(
                "Catégorie",
                ["IA", "LLM", "RAG", "Data/IA", "MLOps", "Général"],
            )
            new_rss = st.radio(
                "Type",
                ["RSS / Atom", "Scraping direct"],
                horizontal=True,
            )

        submitted = st.form_submit_button("➕ Ajouter", use_container_width=True)
        if submitted:
            if not new_name or not new_url:
                st.error("Nom et URL requis.")
            else:
                source = VeilleSource(
                    id=str(uuid.uuid4()),
                    name=new_name,
                    url=new_url,
                    category=new_category,
                    rss=(new_rss == "RSS / Atom"),
                )
                if add_source(source):
                    st.success(f"✅ Source '{new_name}' ajoutée !")
                    st.rerun()
                else:
                    st.warning("⚠️ Cette URL existe déjà.")


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 2 — Articles
# ═══════════════════════════════════════════════════════════════════════════════
with tab2:
    st.subheader("📄 Articles récupérés")

    # Filtres
    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        status_filter = st.selectbox(
            "Statut", ["all", "new", "read", "used", "ignored"], index=0, key="art_status"
        )
    with col_f2:
        sources_list = get_sources()
        source_names = ["all"] + [s.name for s in sources_list]
        source_filter = st.selectbox("Source", source_names, index=0, key="art_source")
    with col_f3:
        limit = st.slider("Nb articles", 10, 100, 30, key="art_limit")

    # Charger
    source_id_filter = None
    if source_filter != "all":
        matching = [s for s in sources_list if s.name == source_filter]
        if matching:
            source_id_filter = matching[0].id

    articles = get_articles(
        status=None if status_filter == "all" else status_filter,
        source_id=source_id_filter,
        limit=limit,
    )

    st.markdown(f"**{len(articles)} article(s)** trouvé(s)")

    BADGE = {
        "new": "badge-new",
        "read": "badge-read",
        "used": "badge-used",
        "ignored": "badge-ignored",
    }

    if not articles:
        st.info("Aucun article. Lance la veille dans l'onglet **Sources** d'abord.")
    else:
        for art in articles:
            badge_cls = BADGE.get(art.status, "badge-new")
            with st.expander(
                f"**{art.title[:80]}** — {art.source_name}  [{art.status.upper()}]",
                expanded=(art.status == "new" and not art.summary),
            ):
                col_l, col_r = st.columns([3, 2])

                with col_l:
                    st.markdown(
                        f"<span class='{badge_cls}'>{art.status}</span> "
                        f"<small style='color:#64748b'>• {art.source_name} • "
                        f"{art.published_at[:10] if art.published_at else ''}</small>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(f"🔗 [{art.url[:70]}]({art.url})")

                    if art.summary:
                        st.markdown("**📝 Résumé :**")
                        st.markdown(art.summary)
                    else:
                        st.caption("*Pas encore de résumé — clique ✨ Enrichir*")

                with col_r:
                    btn_c1, btn_c2, btn_c3, btn_c4 = st.columns(4)
                    with btn_c1:
                        if st.button("👁 Lu", key=f"read_{art.id}", help="Marquer comme lu"):
                            update_article_status(art.id, "read")
                            st.rerun()
                    with btn_c2:
                        if st.button("🚫", key=f"ign_{art.id}", help="Ignorer"):
                            update_article_status(art.id, "ignored")
                            st.rerun()
                    with btn_c3:
                        if st.button(
                            "✨ Enrichir",
                            key=f"enrich_{art.id}",
                            help="Générer résumé + post LLM",
                            disabled=st.session_state.veille_enrich_running,
                        ):
                            st.session_state.veille_enrich_running = True
                            st.session_state.veille_enrich_logs = []
                            _art_id = art.id
                            _art_copy = art
                            _enrich_logs = st.session_state.veille_enrich_logs

                            def _append_enrich_log(message: str, logs=_enrich_logs) -> None:
                                logs.append(message)

                            def _run_enrich(a=_art_copy):
                                from pipelines.veille_pipeline import VeillePipeline

                                VeillePipeline().enrich_article(
                                    a,
                                    callback=_append_enrich_log,
                                )
                                st.session_state.veille_enrich_running = False

                            threading.Thread(target=_run_enrich, daemon=True).start()
                            st.rerun()

                    with btn_c4:
                        if art.suggested_post:
                            if st.button(
                                "📣 → Sched.",
                                key=f"sched_{art.id}",
                                help="Envoyer le post au scheduler LinkedIn",
                            ):
                                # Ajouter au scheduler LinkedIn (Phase 2)
                                try:
                                    import uuid as _uuid
                                    from datetime import datetime as _dt
                                    from datetime import timedelta

                                    from tools.scheduler_tools import ScheduledPost, add_posts

                                    _now = _dt.utcnow()
                                    sp = ScheduledPost(
                                        id=str(_uuid.uuid4()),
                                        pillar="expertise_ia",
                                        day_of_week=_now.strftime("%A").lower(),
                                        week_number=int(_now.strftime("%W")) + 1,
                                        scheduled_date=(_now + timedelta(days=1)).strftime(
                                            "%Y-%m-%d"
                                        ),
                                        content=art.suggested_post,
                                        hashtags=[],
                                        status="approved",
                                    )
                                    add_posts([sp])
                                    update_article_status(art.id, "used")
                                    st.success("✅ Post ajouté au scheduler LinkedIn !")
                                    st.rerun()
                                except Exception as e:
                                    st.error(f"❌ Erreur scheduler: {e}")

        # Logs d'enrichissement
        if st.session_state.veille_enrich_running or st.session_state.veille_enrich_logs:
            st.divider()
            st.markdown("#### 📡 Logs d'enrichissement")
            enrich_html = "<br>".join(st.session_state.veille_enrich_logs[-20:])
            st.markdown(
                f'<div class="log-box">{enrich_html or "En attente…"}</div>',
                unsafe_allow_html=True,
            )
            if st.session_state.veille_enrich_running:
                time.sleep(1)
                st.rerun()
            else:
                st.success("✅ Enrichissement terminé ! Rafraîchis pour voir le résumé.")
                if st.button("🔄 Rafraîchir", key="refresh_enrich"):
                    st.session_state.veille_enrich_logs = []
                    st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# TAB 3 — Posts suggérés
# ═══════════════════════════════════════════════════════════════════════════════
with tab3:
    st.subheader("📣 Posts LinkedIn suggérés")
    st.markdown(
        "Posts générés par le LLM à partir des articles scrappés. "
        "Modifie, approuve et envoie directement au **Scheduler LinkedIn**."
    )

    # Articles avec post généré
    articles_with_post = [
        a for a in get_articles(limit=200) if a.suggested_post and a.status != "ignored"
    ]

    if not articles_with_post:
        st.info(
            "📭 Aucun post suggéré pour l'instant. Lance la veille avec **Posts LinkedIn** activé.",
            icon="📭",
        )
    else:
        st.markdown(f"**{len(articles_with_post)} post(s)** disponible(s)")
        st.divider()

        for art in articles_with_post:
            badge_cls = BADGE.get(art.status, "badge-new")
            with st.expander(
                f"📣 **{art.title[:70]}** — {art.source_name}  [{art.status.upper()}]",
                expanded=(art.status == "new"),
            ):
                col_l, col_r = st.columns([2, 3])

                with col_l:
                    st.markdown(
                        f"<span class='{badge_cls}'>{art.status}</span> "
                        f"<small>• {art.source_name}</small>",
                        unsafe_allow_html=True,
                    )
                    if art.summary:
                        with st.expander("📝 Résumé source"):
                            st.markdown(art.summary)
                    st.markdown(f"🔗 [Article original]({art.url})")

                with col_r:
                    post_key = f"post_edit_{art.id}"
                    if post_key not in st.session_state:
                        st.session_state[post_key] = art.suggested_post

                    edited_post = st.text_area(
                        "✏️ Post LinkedIn (modifiable)",
                        value=st.session_state[post_key],
                        key=f"ta_post_{art.id}",
                        height=200,
                        help="Modifie le post avant de l'envoyer au scheduler",
                    )
                    char_count = len(edited_post)
                    color = "#dc2626" if char_count > 3000 else "#16a34a"
                    st.markdown(
                        f"<small style='color:{color}'>{char_count} chars</small>",
                        unsafe_allow_html=True,
                    )

                    btn_p1, btn_p2, btn_p3 = st.columns(3)
                    with btn_p1:
                        if st.button("💾 Sauver", key=f"save_post_{art.id}"):
                            update_article(art.id, suggested_post=edited_post)
                            st.session_state[post_key] = edited_post
                            st.success("Sauvegardé !")

                    with btn_p2:
                        if st.button(
                            "📅 → Scheduler",
                            key=f"to_sched_{art.id}",
                            type="primary",
                            help="Ajouter au scheduler LinkedIn (Page 2)",
                        ):
                            try:
                                import uuid as _uuid
                                from datetime import datetime as _dt
                                from datetime import timedelta

                                from tools.scheduler_tools import ScheduledPost, add_posts

                                _now = _dt.utcnow()
                                sp = ScheduledPost(
                                    id=str(_uuid.uuid4()),
                                    pillar="expertise_ia",
                                    day_of_week=_now.strftime("%A").lower(),
                                    week_number=int(_now.strftime("%W")) + 1,
                                    scheduled_date=(_now + timedelta(days=1)).strftime("%Y-%m-%d"),
                                    content=edited_post,
                                    hashtags=[],
                                    status="approved",
                                )
                                add_posts([sp])
                                update_article(art.id, suggested_post=edited_post, status="used")
                                st.session_state[post_key] = edited_post
                                st.success("✅ Post ajouté au scheduler !")
                                st.rerun()
                            except Exception as e:
                                st.error(f"❌ {e}")

                    with btn_p3:
                        if st.button("🚫 Ignorer", key=f"ign_post_{art.id}"):
                            update_article_status(art.id, "ignored")
                            st.rerun()
