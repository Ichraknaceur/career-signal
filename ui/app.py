"""
CareerSignal — Home Page & Dashboard Global
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from core.client import clear_provider_cache

st.set_page_config(
    page_title="CareerSignal",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(
    """
<style>
/* Cards fonctionnalité */
.feature-card {
    background: white;
    border: 1.5px solid #E5E7EB;
    border-radius: 14px;
    padding: 24px 20px 20px 20px;
    min-height: 175px;
    cursor: pointer;
    transition: all 0.2s ease;
    position: relative;
    overflow: hidden;
}
.feature-card:hover {
    border-color: #6366F1;
    box-shadow: 0 4px 24px rgba(99,102,241,0.13);
    transform: translateY(-2px);
}
.feature-card .icon {
    font-size: 36px;
    margin-bottom: 10px;
    display: block;
}
.feature-card .title {
    font-size: 17px;
    font-weight: 700;
    color: #111827;
    margin-bottom: 6px;
}
.feature-card .desc {
    font-size: 13px;
    color: #6B7280;
    line-height: 1.5;
}
.feature-card .badge {
    position: absolute;
    top: 14px; right: 14px;
    background: #EEF2FF;
    color: #6366F1;
    font-size: 11px;
    font-weight: 600;
    padding: 2px 9px;
    border-radius: 20px;
    border: 1px solid #C7D2FE;
}
/* KPI metric cards */
.kpi-card {
    background: white;
    border: 1.5px solid #E5E7EB;
    border-radius: 12px;
    padding: 18px 16px;
    text-align: center;
}
.kpi-value {
    font-size: 32px;
    font-weight: 800;
    color: #6366F1;
    line-height: 1.1;
}
.kpi-label {
    font-size: 12px;
    color: #6B7280;
    margin-top: 4px;
    font-weight: 500;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
.kpi-delta {
    font-size: 12px;
    color: #10B981;
    margin-top: 2px;
}
/* Section header */
.section-header {
    font-size: 18px;
    font-weight: 700;
    color: #111827;
    margin: 28px 0 14px 0;
    display: flex;
    align-items: center;
    gap: 8px;
}
/* Status dot */
.dot-green { display:inline-block; width:8px; height:8px;
    background:#10B981; border-radius:50%; margin-right:5px; }
.dot-yellow { display:inline-block; width:8px; height:8px;
    background:#F59E0B; border-radius:50%; margin-right:5px; }
.dot-red { display:inline-block; width:8px; height:8px;
    background:#EF4444; border-radius:50%; margin-right:5px; }
/* Hero banner */
.hero {
    background: linear-gradient(135deg, #6366F1 0%, #8B5CF6 100%);
    border-radius: 16px;
    padding: 32px 36px;
    color: white;
    margin-bottom: 24px;
}
.hero h1 { color: white; font-size: 28px; font-weight: 800; margin: 0 0 8px 0; }
.hero p  { color: rgba(255,255,255,0.85); font-size: 15px; margin: 0; }
</style>
""",
    unsafe_allow_html=True,
)


# ── Sidebar : provider LLM + config globale ───────────────────────────────────
with st.sidebar:
    st.markdown("## 🤖 CareerSignal")
    st.caption("Système IA de contenu bout-en-bout")
    st.divider()

    st.markdown("### Provider LLM")
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

    try:
        from core.config import settings

        model_label = settings.model.agent(provider_choice)
        st.caption(f"Modèle : `{model_label}`")
    except Exception:
        pass

    st.divider()

    # Statut des clés API
    st.markdown("### 🔑 Statut API")
    anthropic_ok = bool(os.getenv("ANTHROPIC_API_KEY"))
    openai_ok = bool(os.getenv("OPENAI_API_KEY"))
    linkedin_ok = bool(os.getenv("LINKEDIN_EMAIL"))

    def _dot(ok):
        return "🟢" if ok else "🔴"

    st.markdown(f"{_dot(anthropic_ok)} Anthropic")
    st.markdown(f"{_dot(openai_ok)}    OpenAI")
    st.markdown(f"{_dot(linkedin_ok)}  LinkedIn (email)")

    st.divider()
    st.caption("💡 Configure les clés dans `.env`")


# ── Charger les stats globales ────────────────────────────────────────────────
def _load_stats() -> dict:
    stats = {
        "medium_articles": 0,
        "posts_scheduled": 0,
        "posts_published": 0,
        "connections_sent": 0,
        "connections_accepted": 0,
        "veille_articles": 0,
        "veille_new": 0,
        "veille_sources": 0,
    }
    try:
        from tools.scheduler_tools import get_published_medium_articles, get_scheduled_posts

        stats["medium_articles"] = len(get_published_medium_articles())
        posts = get_scheduled_posts()
        stats["posts_scheduled"] = len([p for p in posts if p.status in ("draft", "approved")])
        stats["posts_published"] = len([p for p in posts if p.status == "published"])
    except Exception:
        pass
    try:
        from tools.outreach_store import get_campaign_stats

        cs = get_campaign_stats()
        stats["connections_sent"] = cs.get("sent", 0) + cs.get("accepted", 0)
        stats["connections_accepted"] = cs.get("accepted", 0)
    except Exception:
        pass
    try:
        from tools.veille_store import get_veille_stats

        vs = get_veille_stats()
        stats["veille_articles"] = vs.get("total", 0)
        stats["veille_new"] = vs.get("new", 0)
        stats["veille_sources"] = vs.get("sources", 0)
    except Exception:
        pass
    return stats


stats = _load_stats()


# ── Hero ──────────────────────────────────────────────────────────────────────
st.markdown(
    """
<div class="hero">
  <h1>🤖 CareerSignal</h1>
  <p>Pipeline IA complet : génération d'articles · scheduling LinkedIn · outreach recruteurs · veille technologique</p>
</div>
""",
    unsafe_allow_html=True,
)


# ── KPIs globaux ──────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">📊 Dashboard Global</div>', unsafe_allow_html=True)

k1, k2, k3, k4, k5 = st.columns(5)

with k1:
    st.markdown(
        f"""
    <div class="kpi-card">
        <div class="kpi-value">{stats["medium_articles"]}</div>
        <div class="kpi-label">Articles Medium</div>
    </div>""",
        unsafe_allow_html=True,
    )

with k2:
    st.markdown(
        f"""
    <div class="kpi-card">
        <div class="kpi-value">{stats["posts_scheduled"]}</div>
        <div class="kpi-label">Posts en attente</div>
        <div class="kpi-delta">+{stats["posts_published"]} publiés</div>
    </div>""",
        unsafe_allow_html=True,
    )

with k3:
    st.markdown(
        f"""
    <div class="kpi-card">
        <div class="kpi-value">{stats["connections_sent"]}</div>
        <div class="kpi-label">Connexions envoyées</div>
        <div class="kpi-delta">{stats["connections_accepted"]} acceptées</div>
    </div>""",
        unsafe_allow_html=True,
    )

with k4:
    st.markdown(
        f"""
    <div class="kpi-card">
        <div class="kpi-value">{stats["veille_articles"]}</div>
        <div class="kpi-label">Articles veille</div>
        <div class="kpi-delta">{stats["veille_new"]} nouveaux</div>
    </div>""",
        unsafe_allow_html=True,
    )

with k5:
    st.markdown(
        f"""
    <div class="kpi-card">
        <div class="kpi-value">{stats["veille_sources"]}</div>
        <div class="kpi-label">Sources actives</div>
    </div>""",
        unsafe_allow_html=True,
    )


# ── Feature cards ─────────────────────────────────────────────────────────────
st.markdown('<div class="section-header">🚀 Fonctionnalités</div>', unsafe_allow_html=True)

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(
        """
    <div class="feature-card">
        <span class="badge">Phase 1</span>
        <span class="icon">✍️</span>
        <div class="title">Medium Pipeline</div>
        <div class="desc">Génère des articles complets depuis un sujet ou une source. QA automatique + édition avant publication.</div>
    </div>
    """,
        unsafe_allow_html=True,
    )
    if st.button("Ouvrir →", key="btn_medium", use_container_width=True):
        st.switch_page("pages/01_Medium_Pipeline.py")

with col2:
    st.markdown(
        """
    <div class="feature-card">
        <span class="badge">Phase 2</span>
        <span class="icon">📅</span>
        <div class="title">LinkedIn Scheduling</div>
        <div class="desc">Planifie et génère tes posts LinkedIn sur 4 piliers de contenu. Calendrier éditorial sur 4 semaines.</div>
    </div>
    """,
        unsafe_allow_html=True,
    )
    if st.button("Ouvrir →", key="btn_sched", use_container_width=True):
        st.switch_page("pages/02_LinkedIn_Scheduling.py")

with col3:
    st.markdown(
        """
    <div class="feature-card">
        <span class="badge">Phase 3</span>
        <span class="icon">🤝</span>
        <div class="title">LinkedIn Outreach</div>
        <div class="desc">Scrape des profils ou des offres d'emploi IA, génère des notes personnalisées et envoie des demandes de connexion.</div>
    </div>
    """,
        unsafe_allow_html=True,
    )
    if st.button("Ouvrir →", key="btn_out", use_container_width=True):
        st.switch_page("pages/03_LinkedIn_Outreach.py")


col4, col5, col6 = st.columns(3)

with col4:
    st.markdown(
        """
    <div class="feature-card">
        <span class="badge">Phase 4</span>
        <span class="icon">🔍</span>
        <div class="title">Veille IA</div>
        <div class="desc">Agrège les derniers articles IA depuis 7 sources RSS. Résumés automatiques + suggestions de posts LinkedIn.</div>
    </div>
    """,
        unsafe_allow_html=True,
    )
    if st.button("Ouvrir →", key="btn_veille", use_container_width=True):
        st.switch_page("pages/04_Veille_IA.py")

with col5:
    st.markdown(
        """
    <div class="feature-card">
        <span class="badge">Docs</span>
        <span class="icon">📚</span>
        <div class="title">Documentation</div>
        <div class="desc">Architecture du projet, guide de configuration, best practices LinkedIn et workflow hebdomadaire recommandé.</div>
    </div>
    """,
        unsafe_allow_html=True,
    )
    if st.button("Ouvrir →", key="btn_doc", use_container_width=True):
        st.switch_page("pages/05_Documentation.py")

with col6:
    # Placeholder pour une future feature
    st.markdown(
        """
    <div class="feature-card" style="background:#F9FAFB; border-style: dashed;">
        <span class="icon" style="opacity:0.3">⚡</span>
        <div class="title" style="color:#9CA3AF">Bientôt</div>
        <div class="desc" style="color:#D1D5DB">Publication automatique Medium · Messages de suivi · Déploiement cloud</div>
    </div>
    """,
        unsafe_allow_html=True,
    )


# ── Activité récente ──────────────────────────────────────────────────────────
st.divider()
st.markdown('<div class="section-header">⚡ Activité récente</div>', unsafe_allow_html=True)

col_a, col_b = st.columns(2)

with col_a:
    st.markdown("**📰 Derniers articles Medium**")
    try:
        from tools.scheduler_tools import get_published_medium_articles

        articles = get_published_medium_articles()
        if articles:
            for art in articles[-4:][::-1]:
                st.markdown(
                    f"• [{art['title'][:55]}{'…' if len(art['title']) > 55 else ''}]({art['url']})"
                    f"  <span style='color:#9CA3AF;font-size:11px'>{art.get('published_at', '')[:10]}</span>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("_Aucun article publié — lance le Medium Pipeline_")
    except Exception as e:
        st.caption(f"_Erreur chargement: {e}_")

with col_b:
    st.markdown("**🔍 Derniers articles de veille**")
    try:
        from tools.veille_store import get_articles

        arts = get_articles(status_filter="new", limit=4)
        if arts:
            for a in arts:
                st.markdown(
                    f"• **{a.source_name}** — {a.title[:52]}{'…' if len(a.title) > 52 else ''}  "
                    f"<span style='color:#9CA3AF;font-size:11px'>{a.published_at[:10] if a.published_at else ''}</span>",
                    unsafe_allow_html=True,
                )
        else:
            st.caption("_Aucun nouvel article — lance la Veille IA_")
    except Exception as e:
        st.caption(f"_Erreur chargement: {e}_")


# ── Footer ────────────────────────────────────────────────────────────────────
st.divider()
st.markdown(
    "<div style='text-align:center; color:#9CA3AF; font-size:12px; padding:8px 0'>"
    "Built with ❤️ by <strong>Ichrak Ennaceur</strong> · Applied AI / Gen AI Engineer"
    "</div>",
    unsafe_allow_html=True,
)
