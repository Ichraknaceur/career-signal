"""
LinkedIn Scheduling Pipeline — Phase 2.

Génère un calendrier éditorial LinkedIn pour N semaines :
  - 3 posts/semaine (Lundi / Mercredi / Vendredi)
  - Rotation des pilliers : expertise_ia → projets → promo_medium
  - Sauvegarde dans data/schedule.json (statut : draft)

Usage :
    pipeline = LinkedInSchedulingPipeline()
    result = pipeline.generate(
        niche="IA appliquée, Gen AI, MLOps",
        audience="ingénieurs IA, recruteurs tech, fondateurs startups",
        nb_weeks=2,
        context="Je build des systèmes multi-agents avec Anthropic SDK",
        callback=print,
    )
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import date

from agents.linkedin_content_agent import LinkedInContentAgent
from tools.scheduler_tools import (
    ScheduledPost,
    add_posts,
    build_background_prompt,
    compute_scheduled_dates,
    get_published_medium_articles,
    load_prompt_profile,
)

logger = logging.getLogger(__name__)


# ── Résultat du pipeline ─────────────────────────────────────────────────────
@dataclass
class LinkedInSchedulingResult:
    success: bool
    posts: list[ScheduledPost] = field(default_factory=list)
    nb_weeks: int = 0
    errors: list[str] = field(default_factory=list)
    logs: list[str] = field(default_factory=list)

    @property
    def total_posts(self) -> int:
        return len(self.posts)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


# ── Pipeline principal ───────────────────────────────────────────────────────
class LinkedInSchedulingPipeline:
    """
    Orchestre la génération du calendrier éditorial LinkedIn.

    Pour chaque slot (semaine × jour), appelle LinkedInContentAgent.generate_post()
    et accumule les ScheduledPost générés. Sauvegarde ensuite tout en une fois.
    """

    def __init__(self) -> None:
        self.agent = LinkedInContentAgent()

    def generate(
        self,
        niche: str,
        audience: str,
        nb_weeks: int = 2,
        context: str = "",
        language: str = "English",
        start_date: date | None = None,
        publish_times: dict[str, str] | None = None,
        prompt_profile: dict | None = None,
        callback: Callable[[str], None] | None = None,
    ) -> LinkedInSchedulingResult:
        """
        Génère le calendrier éditorial complet.

        Args:
            niche       : thématique (ex: "IA appliquée, Gen AI, MLOps")
            audience    : cible (ex: "ML engineers, recruteurs tech")
            nb_weeks    : nombre de semaines à planifier (1-4)
            context     : contexte libre (projets récents, idées…)
            callback    : fonction appelée avec des messages de progression

        Returns:
            LinkedInSchedulingResult avec la liste des posts générés.
        """
        result = LinkedInSchedulingResult(success=False, nb_weeks=nb_weeks)

        def log(msg: str) -> None:
            result.logs.append(msg)
            logger.info(msg)
            if callback:
                callback(msg)

        log(f"🚀 LinkedIn Scheduling Pipeline démarré — {nb_weeks} semaine(s)")

        # Calculer les slots de publication
        slots = compute_scheduled_dates(
            nb_weeks=nb_weeks,
            start_date=start_date,
            publish_times=publish_times,
        )
        total_slots = len(slots)
        log(f"📅 {total_slots} posts à générer ({nb_weeks} semaines × 3 jours)")
        active_prompt_profile = prompt_profile or load_prompt_profile()

        # Charger les articles Medium publiés (pour promo_medium)
        medium_articles = get_published_medium_articles()
        medium_index = 0  # Rotation des articles Medium disponibles
        log(f"📰 {len(medium_articles)} article(s) Medium disponible(s) pour promo")

        # Générer chaque post
        generated_posts: list[ScheduledPost] = []

        for i, slot in enumerate(slots, 1):
            pillar = slot["pillar"]
            day = slot["day"]
            week = slot["week"]
            sdate = slot["date"]
            stime = slot["time"]

            log(f"\n[{i}/{total_slots}] Semaine {week} — {day} ({pillar}) — {sdate} {stime}")

            # Sélectionner l'article Medium pour le pillier promo_medium
            medium_article = None
            if pillar == "promo_medium" and medium_articles:
                medium_article = medium_articles[medium_index % len(medium_articles)]
                medium_index += 1

            try:
                post = self.agent.generate_post(
                    pillar=pillar,
                    day_of_week=day,
                    week_number=week,
                    scheduled_date=sdate,
                    scheduled_time=stime,
                    niche=niche,
                    audience=audience,
                    context=context,
                    language=language,
                    medium_article=medium_article,
                    background_prompt=build_background_prompt(pillar, active_prompt_profile),
                )

                if post:
                    generated_posts.append(post)
                    log(
                        f"✅ Post généré — {len(post.content)} chars, {len(post.hashtags)} hashtags"
                    )
                else:
                    msg = f"❌ Échec génération slot {week}/{day}"
                    log(msg)
                    result.errors.append(msg)

            except Exception as e:
                msg = f"❌ Erreur slot {week}/{day}: {e}"
                log(msg)
                result.errors.append(msg)
                logger.exception(msg)

        # Sauvegarde en batch
        if generated_posts:
            try:
                add_posts(generated_posts)
                log(f"\n💾 {len(generated_posts)} posts sauvegardés dans data/schedule.json")
            except Exception as e:
                msg = f"❌ Erreur sauvegarde: {e}"
                log(msg)
                result.errors.append(msg)

        result.posts = generated_posts
        result.success = len(generated_posts) > 0

        log(
            f"\n{'✅' if result.success else '❌'} Pipeline terminé — "
            f"{len(generated_posts)}/{total_slots} posts générés"
        )
        if result.has_errors:
            log(f"⚠️ {len(result.errors)} erreur(s) rencontrée(s)")

        return result
