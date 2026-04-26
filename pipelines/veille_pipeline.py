"""
VeillePipeline — Phase 4.

Orchestration complète du workflow de veille IA :

  1. Fetch   : Récupère les nouveaux articles depuis les sources actives (RSS / scraping)
  2. Filter  : Ignore les articles déjà vus (déduplication par URL)
  3. Summarize : VeilleAgent génère un résumé pour chaque nouvel article
  4. Suggest : VeilleAgent génère un post LinkedIn suggéré
  5. Store   : Sauvegarde tout en base JSON (statut: 'new')

Le pipeline est entièrement synchrone (pas de Playwright).
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime

from agents.veille_agent import VeilleAgent
from tools.rss_fetcher import fetch_source
from tools.veille_store import (
    VeilleArticle,
    VeilleSource,
    add_articles,
    get_sources,
    update_article,
    update_source,
    url_already_fetched,
)

logger = logging.getLogger(__name__)


# ── Résultat du pipeline ──────────────────────────────────────────────────────
@dataclass
class VeilleResult:
    sources_checked: int = 0
    articles_fetched: int = 0
    articles_new: int = 0
    summaries_generated: int = 0
    posts_generated: int = 0
    errors: list[str] = field(default_factory=list)
    duration_seconds: float = 0.0

    def summary(self) -> str:
        lines = [
            f"Sources vérifiées  : {self.sources_checked}",
            f"Articles récupérés : {self.articles_fetched}",
            f"Nouveaux articles  : {self.articles_new}",
            f"Résumés générés    : {self.summaries_generated}",
            f"Posts suggérés     : {self.posts_generated}",
            f"Durée              : {self.duration_seconds:.1f}s",
        ]
        if self.errors:
            lines.append(f"Erreurs ({len(self.errors)}): {self.errors[:3]}")
        return "\n".join(lines)


# ── Pipeline ──────────────────────────────────────────────────────────────────
class VeillePipeline:
    """
    Pipeline de veille IA.

    Usage simple :
        pipeline = VeillePipeline()
        result = pipeline.run(max_per_source=10, callback=print)

    Usage ciblé (une seule source) :
        result = pipeline.run_source(source, max_per_source=5, callback=print)
    """

    def __init__(
        self,
        generate_summaries: bool = True,
        generate_posts: bool = True,
    ) -> None:
        self.generate_summaries = generate_summaries
        self.generate_posts = generate_posts
        self._agent = VeilleAgent()

    # ── Run complet (toutes les sources actives) ──────────────────────────────
    def run(
        self,
        max_per_source: int = 10,
        source_ids: list[str] | None = None,
        callback: Callable[[str], None] | None = None,
    ) -> VeilleResult:
        """
        Récupère les articles de toutes les sources actives (ou celles spécifiées).

        Args:
            max_per_source : Nombre max d'articles par source
            source_ids     : Si fourni, ne traite que ces sources
            callback       : Fonction de log appelée à chaque étape
        """
        cb = callback or (lambda _: None)
        result = VeilleResult()
        start = datetime.utcnow()

        sources = get_sources(active_only=True)
        if source_ids:
            sources = [s for s in sources if s.id in source_ids]

        if not sources:
            cb("⚠️ Aucune source active trouvée.")
            return result

        cb(f"🔍 {len(sources)} source(s) à vérifier…")

        for source in sources:
            try:
                self._process_source(source, max_per_source, result, cb)
            except Exception as e:
                logger.error(f"[VeillePipeline] Erreur source {source.name}: {e}")
                result.errors.append(f"{source.name}: {e}")

        result.duration_seconds = (datetime.utcnow() - start).total_seconds()
        cb(f"\n📊 Résumé:\n{result.summary()}")
        return result

    # ── Run sur une seule source ──────────────────────────────────────────────
    def run_source(
        self,
        source: VeilleSource,
        max_per_source: int = 10,
        callback: Callable[[str], None] | None = None,
    ) -> VeilleResult:
        cb = callback or (lambda _: None)
        result = VeilleResult()
        start = datetime.utcnow()
        try:
            self._process_source(source, max_per_source, result, cb)
        except Exception as e:
            result.errors.append(str(e))
        result.duration_seconds = (datetime.utcnow() - start).total_seconds()
        return result

    # ── Traitement d'une source ───────────────────────────────────────────────
    def _process_source(
        self,
        source: VeilleSource,
        max_per_source: int,
        result: VeilleResult,
        cb: Callable[[str], None],
    ) -> None:
        cb(f"\n📡 [{source.name}] Récupération RSS…")
        result.sources_checked += 1

        # ── 1. Fetch ──────────────────────────────────────────────────────────
        raw_articles = fetch_source(source, max_items=max_per_source)
        result.articles_fetched += len(raw_articles)
        cb(f"   📄 {len(raw_articles)} article(s) récupéré(s)")

        if not raw_articles:
            return

        # ── 2. Filtre déduplication ───────────────────────────────────────────
        new_articles = [a for a in raw_articles if not url_already_fetched(a.url)]
        cb(f"   🆕 {len(new_articles)} nouveau(x) article(s) (non déjà vus)")

        if not new_articles:
            update_source(source.id, last_fetched=datetime.utcnow().isoformat() + "Z")
            return

        # ── 3. Summarize + Suggest ────────────────────────────────────────────
        enriched: list[VeilleArticle] = []

        for i, article in enumerate(new_articles, 1):
            cb(f"   ✍️  [{i}/{len(new_articles)}] {article.title[:60]}…")

            # Résumé
            if self.generate_summaries:
                try:
                    summary = self._agent.summarize(article)
                    article.summary = summary
                    result.summaries_generated += 1
                    cb(f"      📝 Résumé: {summary[:80]}…")
                except Exception as e:
                    logger.error(f"[VeillePipeline] Résumé échoué: {e}")
                    result.errors.append(f"Résumé {article.title[:30]}: {e}")

            # Post LinkedIn
            if self.generate_posts and article.summary:
                try:
                    post = self._agent.suggest_post(article, article.summary)
                    article.suggested_post = post
                    result.posts_generated += 1
                    cb(f"      📣 Post: {post[:80]}…")
                except Exception as e:
                    logger.error(f"[VeillePipeline] Post échoué: {e}")
                    result.errors.append(f"Post {article.title[:30]}: {e}")

            enriched.append(article)

        # ── 4. Store ──────────────────────────────────────────────────────────
        added = add_articles(enriched)
        result.articles_new += added
        cb(f"   💾 {added} article(s) sauvegardé(s)")

        # Mettre à jour la source
        update_source(
            source.id,
            last_fetched=datetime.utcnow().isoformat() + "Z",
            article_count=source.article_count + added,
        )

    # ── Générer résumé + post pour un article existant ────────────────────────
    def enrich_article(
        self,
        article: VeilleArticle,
        callback: Callable[[str], None] | None = None,
    ) -> VeilleArticle:
        """
        (Ré)génère résumé et post pour un article déjà en base.
        Met à jour directement le store.
        """
        cb = callback or (lambda _: None)

        cb(f"✍️ Résumé en cours pour : {article.title[:60]}…")
        try:
            summary = self._agent.summarize(article)
            article.summary = summary
            update_article(article.id, summary=summary)
            cb(f"   📝 Résumé ({len(summary)} chars) ✓")
        except Exception as e:
            cb(f"   ❌ Résumé échoué: {e}")

        if article.summary:
            cb("📣 Post LinkedIn en cours…")
            try:
                post = self._agent.suggest_post(article, article.summary)
                article.suggested_post = post
                update_article(article.id, suggested_post=post)
                cb(f"   📣 Post ({len(post)} chars) ✓")
            except Exception as e:
                cb(f"   ❌ Post échoué: {e}")

        return article
