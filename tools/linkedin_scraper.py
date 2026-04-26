"""
LinkedIn Scraper — Phase 3.

Utilise Playwright pour :
  1. Se connecter à LinkedIn (avec session persistante via cookies)
  2. Scraper les résultats de recherche (People Search)
  3. Extraire les infos d'un profil (nom, titre, entreprise, about)

Stealth mode :
  - User-agent réaliste
  - Délais aléatoires entre les actions
  - Session persistante via cookies (évite le re-login)
  - Headless=False recommandé pour éviter la détection
"""

from __future__ import annotations

import asyncio
import logging
import random

from tools.outreach_store import load_cookies, save_cookies

logger = logging.getLogger(__name__)

# ── Config ────────────────────────────────────────────────────────────────────
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/120.0.0.0 Safari/537.36"
)
LINKEDIN_BASE = "https://www.linkedin.com"


# ── Helpers ───────────────────────────────────────────────────────────────────
async def _human_delay(min_s: float = 1.5, max_s: float = 4.0) -> None:
    """Délai aléatoire pour simuler un comportement humain."""
    await asyncio.sleep(random.uniform(min_s, max_s))


async def _slow_type(page, selector: str, text: str) -> None:
    """Frappe caractère par caractère avec délai aléatoire."""
    await page.click(selector)
    for char in text:
        await page.keyboard.type(char, delay=random.randint(50, 150))


# ── Login ─────────────────────────────────────────────────────────────────────
async def login_linkedin(
    page,
    email: str,
    password: str,
    callback=None,
) -> bool:
    """
    Se connecte a LinkedIn.
    Gere les deux pages de login LinkedIn :
      - /login          → selectors #username / #password
      - /uas/login      → selectors input[name=session_key] / input[name=session_password]

    Retourne True si la connexion a reussi.
    Sauvegarde les cookies pour les sessions futures.
    """

    def _log(msg: str) -> None:
        logger.info(msg)
        if callback:
            callback(msg)

    # Selecteurs compatibles /login ET /uas/login
    EMAIL_SELECTORS = [
        "#username",  # /login standard
        "input[name='session_key']",  # /uas/login
        "input[type='email']",  # fallback generique
        "input[autocomplete='username']",
    ]
    PASSWORD_SELECTORS = [
        "#password",  # /login standard
        "input[name='session_password']",  # /uas/login
        "input[type='password']",  # fallback generique
    ]
    SUBMIT_SELECTORS = [
        "button[type='submit']",
        "input[type='submit']",
        ".sign-in-form__submit-btn--full-width",
        "[data-litms-control-urn*='login'] button",
        "form button",
    ]

    async def _fill_field(
        selectors: list[str], value: str, label: str, timeout: int = 5000
    ) -> bool:
        """Essaie chaque selecteur, remplit le premier trouve."""
        for sel in selectors:
            try:
                el = await page.wait_for_selector(sel, timeout=timeout)
                if el:
                    await el.click()
                    await asyncio.sleep(0.3)
                    await el.fill("")
                    for char in value:
                        await page.keyboard.type(char, delay=random.randint(40, 120))
                    _log(f"   ✓ {label} saisi")
                    return True
            except Exception:
                continue
        return False

    async def _click_submit() -> bool:
        """Clique sur le bouton de soumission."""
        for sel in SUBMIT_SELECTORS:
            try:
                btn = await page.query_selector(sel)
                if btn:
                    await btn.click()
                    return True
            except Exception:
                continue
        await page.keyboard.press("Enter")
        return True

    async def _wait_for_navigation_result() -> str:
        """Attend la navigation et retourne l'URL finale."""
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=20000)
        except Exception:
            pass
        await _human_delay(3, 5)
        return page.url

    async def _save_and_return_success() -> bool:
        cookies = await page.context.cookies()
        save_cookies(cookies)
        _log("✅ Connexion LinkedIn réussie — cookies sauvegardés")
        return True

    async def _handle_post_login_url(url: str) -> bool:
        """
        Analyse l'URL apres soumission.
        Retourne True/False si on peut conclure, None si checkpoint en cours.
        """
        if "checkpoint" in url or "challenge" in url:
            _log("⚠️  LinkedIn demande une vérification (2FA / code email / CAPTCHA)")
            _log("👉 Complète la vérification dans la fenêtre Chrome ouverte.")
            _log("⏳ Attente jusqu'à 90 secondes…")
            for attempt in range(18):
                await asyncio.sleep(5)
                url_now = page.url
                if "checkpoint" not in url_now and "challenge" not in url_now:
                    _log("✅ Vérification passée !")
                    return await _save_and_return_success()
                _log(f"   … {90 - (attempt + 1) * 5}s restantes")
            _log("❌ Délai expiré — relance et complète la vérification plus vite")
            return False

        login_signals = ("/login", "/uas/login", "authwall", "uas/authenticate", "signup")
        if any(s in url for s in login_signals):
            _log("❌ Connexion échouée — email ou mot de passe incorrect")
            return False

        return await _save_and_return_success()

    try:
        _log("🌐 Ouverture de la page de connexion LinkedIn…")
        await page.goto(f"{LINKEDIN_BASE}/login", wait_until="domcontentloaded", timeout=25000)
        await _human_delay(2, 3)

        current_url = page.url
        _log(f"📍 Page de login: {current_url}")

        # ── Détecter le type de page ──────────────────────────────────────────
        # LinkedIn affiche parfois une page "Bon retour" avec SEULEMENT le mdp
        # (compte déjà reconnu depuis le navigateur — pas de champ email)
        has_email_field = False
        for sel in EMAIL_SELECTORS:
            try:
                el = await page.wait_for_selector(sel, timeout=2000)
                if el:
                    has_email_field = True
                    break
            except Exception:
                continue

        has_password_field = False
        for sel in PASSWORD_SELECTORS:
            try:
                el = await page.wait_for_selector(sel, timeout=2000)
                if el:
                    has_password_field = True
                    break
            except Exception:
                continue

        # ── Cas A : Page "Bon retour" — compte reconnu, seulement mdp ────────
        if not has_email_field and has_password_field:
            _log("🔁 Page 'Bon retour parmi nous' détectée (compte pré-sélectionné)")
            _log("🔒 Saisie du mot de passe…")
            pwd_ok = await _fill_field(PASSWORD_SELECTORS, password, "mot de passe")
            if not pwd_ok:
                _log("❌ Champ mot de passe introuvable")
                return False
            await _human_delay(0.5, 1)
            _log("🖱️  Clic sur S'identifier…")
            await _click_submit()
            url = await _wait_for_navigation_result()
            _log(f"📍 URL après connexion: {url}")
            return await _handle_post_login_url(url)

        # ── Cas B : Page standard — email + mot de passe ─────────────────────
        if has_email_field:
            _log("✏️  Saisie de l'email…")
            await _fill_field(EMAIL_SELECTORS, email, "email")
            await _human_delay(0.5, 1)
            _log("🔒 Saisie du mot de passe…")
            pwd_ok = await _fill_field(PASSWORD_SELECTORS, password, "mot de passe")
            if not pwd_ok:
                _log("❌ Champ mot de passe introuvable")
                return False
            await _human_delay(0.5, 1)
            _log("🖱️  Envoi du formulaire…")
            await _click_submit()
            url = await _wait_for_navigation_result()
            _log(f"📍 URL après connexion: {url}")
            return await _handle_post_login_url(url)

        # ── Cas C : Page inconnue — screenshot debug ──────────────────────────
        _log("❌ Page de login non reconnue — screenshot sauvegardé dans data/debug_login.png")
        import pathlib

        pathlib.Path("data").mkdir(exist_ok=True)
        await page.screenshot(path="data/debug_login.png")

        # ── Attendre la réponse de LinkedIn ───────────────────────────────────
        try:
            await page.wait_for_load_state("domcontentloaded", timeout=20000)
        except Exception:
            pass
        await _human_delay(3, 5)

        current_url = page.url
        _log(f"📍 URL après connexion: {current_url}")

        # ── Cas 1 : Checkpoint (2FA / CAPTCHA / vérification email) ───────────
        if "checkpoint" in current_url or "challenge" in current_url:
            _log("⚠️  LinkedIn demande une vérification !")
            _log("👉 Regarde la fenêtre Chrome et complète la vérification.")
            _log("⏳ Attente jusqu'à 90 secondes…")

            for attempt in range(18):  # 18 x 5s = 90s
                await asyncio.sleep(5)
                url_now = page.url
                if "checkpoint" not in url_now and "challenge" not in url_now:
                    _log(f"✅ Vérification passée ! URL: {url_now}")
                    cookies = await page.context.cookies()
                    save_cookies(cookies)
                    _log("💾 Cookies sauvegardés")
                    return True
                remaining = 90 - (attempt + 1) * 5
                _log(f"   … en attente ({remaining}s restantes)")

            _log("❌ Délai expiré — relance et complète la vérification plus rapidement")
            return False

        # ── Cas 2 : Encore sur une page de login → mauvais credentials ───────
        login_signals = ("/login", "/uas/login", "authwall", "uas/authenticate", "signup")
        if any(s in current_url for s in login_signals):
            _log("❌ Connexion échouée — vérifie ton email et mot de passe LinkedIn")
            _log(f"   URL actuelle: {current_url}")
            return False

        # ── Cas 3 : Succès ────────────────────────────────────────────────────
        cookies = await page.context.cookies()
        save_cookies(cookies)
        _log("✅ Connexion LinkedIn réussie — cookies sauvegardés")
        return True

    except Exception as e:
        _log(f"❌ Erreur lors de la connexion: {e}")
        logger.error(f"[Scraper] Erreur login: {e}", exc_info=True)
        return False


async def restore_session(page, callback=None) -> bool:
    """
    Restaure la session LinkedIn depuis les cookies sauvegardés.
    Retourne True si la session est valide (pas redirige vers login).
    """

    def _log(msg):
        logger.info(msg)
        if callback:
            callback(msg)

    cookies = load_cookies()
    if not cookies:
        _log("ℹ️  Aucun cookie sauvegardé — première connexion requise")
        return False

    try:
        await page.context.add_cookies(cookies)
        await page.goto(f"{LINKEDIN_BASE}/feed", wait_until="domcontentloaded", timeout=20000)
        await _human_delay(2, 3)

        current_url = page.url
        _log(f"📍 URL après restauration: {current_url}")

        # Si on n'est PAS redirigé vers une page de login → session valide
        bad_signals = ("login", "authwall", "checkpoint", "signup", "uas/authenticate")
        if any(s in current_url for s in bad_signals):
            _log("ℹ️  Cookies expirés — re-login nécessaire")
            return False

        # L'URL est /feed/ ou similaire → session valide, pas besoin de vérifier la navbar
        good_signals = ("/feed", "/mynetwork", "/messaging", "/notifications", "/jobs", "/in/")
        if any(s in current_url for s in good_signals):
            _log("✅ Session LinkedIn restaurée depuis cookies")
            return True

        # URL ambiguë → vérifier la navbar avec un timeout généreux
        try:
            await page.wait_for_selector(
                "header.global-nav, nav.global-nav, "
                "[data-control-name='nav.homepage'], "
                ".global-nav__content, "
                ".feed-identity-module",
                timeout=8000,
            )
            _log("✅ Session LinkedIn restaurée (navbar détectée)")
            return True
        except Exception:
            _log(f"ℹ️  URL ambiguë ({current_url}) — re-login par précaution")
            return False

    except Exception as e:
        _log(f"❌ Erreur restauration session: {e}")
        logger.error(f"[Scraper] Erreur restauration session: {e}")
        return False


# ── Recherche de profils ──────────────────────────────────────────────────────
async def search_people(
    page,
    keyword: str,
    location: str = "",
    max_results: int = 20,
) -> list[dict]:
    """
    Cherche des profils LinkedIn par mots-clés.
    Retourne une liste de dicts {url, name, title, company, location}.

    Stratégie robuste :
      1. URL de recherche avec geoUrn si location fourni
      2. Attente scroll pour charger le contenu lazy
      3. Sélecteurs multiples en fallback (LinkedIn change souvent son HTML)
      4. Debug log du HTML si 0 résultats
    """
    import urllib.parse

    results: list[dict[str, str]] = []

    # ── Construire l'URL de recherche ─────────────────────────────────────────
    # IMPORTANT : geoUrn requiert un ID numérique LinkedIn (ex: 105015875 pour France).
    # Pour éviter ce problème, on combine keyword + location dans le champ keywords.
    # C'est exactement ce que fait un utilisateur humain en cherchant "Data scientist France".
    full_keyword = f"{keyword} {location}".strip() if location else keyword
    search_url = f"{LINKEDIN_BASE}/search/results/people/?" + urllib.parse.urlencode(
        {
            "keywords": full_keyword,
            "origin": "GLOBAL_SEARCH_HEADER",
        }
    )

    import pathlib

    # Répertoire data en chemin absolu pour éviter les problèmes de CWD
    DATA_DIR_ABS = pathlib.Path(__file__).parent.parent / "data"
    DATA_DIR_ABS.mkdir(exist_ok=True)

    async def _screenshot(name: str) -> None:
        try:
            p = str(DATA_DIR_ABS / name)
            await page.screenshot(path=p, full_page=False)
            logger.info(f"[Scraper] Screenshot → {p}")
        except Exception as e:
            logger.warning(f"[Scraper] Screenshot échoué: {e}")

    try:
        logger.info(f"[Scraper] URL recherche: {search_url}")

        # domcontentloaded d'abord (rapide), puis on attend manuellement
        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        except Exception:
            await page.goto(search_url, wait_until="commit", timeout=30000)

        # Attente fixe + scroll pour déclencher les XHR de résultats
        await asyncio.sleep(4)
        await page.evaluate("window.scrollTo(0, 600)")
        await asyncio.sleep(2)
        await page.evaluate("window.scrollTo(0, 0)")
        await asyncio.sleep(1)

        final_url = page.url
        logger.info(f"[Scraper] URL après navigation: {final_url}")

        # Screenshot immédiat — TOUJOURS, avant toute extraction
        await _screenshot("debug_search_loaded.png")

        if any(s in final_url for s in ("authwall", "checkpoint", "signup")):
            logger.error("[Scraper] Redirigé — session invalide")
            return []

        page_num = 1

        while len(results) < max_results:
            logger.info(f"[Scraper] Page {page_num}…")

            # ── Scroll progressif pour déclencher le lazy-loading ─────────────
            for pos in [400, 800, 1200, 1600]:
                await page.evaluate(f"window.scrollTo(0, {pos})")
                await asyncio.sleep(0.7)
            await page.evaluate("window.scrollTo(0, 0)")
            await _human_delay(1.5, 2.5)

            # ── Attendre qu'au moins un lien /in/ soit présent ────────────────
            # On ne dépend PAS des class names LinkedIn (trop instables)
            # Re-scroll pour s'assurer que le contenu est chargé
            await page.evaluate("window.scrollTo(0, 800)")
            await asyncio.sleep(1.5)
            await page.evaluate("window.scrollTo(0, 0)")
            await asyncio.sleep(1)

            # Vérifier si des liens profil sont présents (sans timeout bloquant)
            n_links = await page.evaluate(
                "() => document.querySelectorAll(\"a[href*='/in/']\").length"
            )
            logger.info(f"[Scraper] Liens /in/ dans le DOM: {n_links}")

            if n_links == 0:
                await _screenshot(f"debug_search_page{page_num}_no_links.png")
                txt = await page.evaluate("() => document.body.innerText.substring(0, 2000)")
                (DATA_DIR_ABS / "debug_search_text.txt").write_text(txt, encoding="utf-8")
                logger.warning(
                    f"[Scraper] 0 liens /in/ sur la page — URL: {page.url}\n"
                    f"Texte de la page → {DATA_DIR_ABS}/debug_search_text.txt"
                )
                break

            # ── Extraction JS : approche universelle par liens /in/ ───────────
            # On ne se fie à AUCUN class name spécifique de LinkedIn.
            # On remonte depuis chaque lien vers son conteneur li/article.
            profiles = await page.evaluate("""() => {
var seen = new Set();
var out = [];
var links = Array.from(document.querySelectorAll("a[href*='/in/']"));
for (var i = 0; i < links.length; i++) {
  var link = links[i];
  var href = link.href || "";
  var url = href.split("?")[0];
  if (!url || seen.has(url)) continue;
  if (url.indexOf("/in/") === -1) continue;

  var name = "";
  var spans = link.querySelectorAll("span[aria-hidden='true']");
  for (var s = 0; s < spans.length; s++) {
    var t = spans[s].innerText.trim();
    if (t && t !== "LinkedIn Member" && t.length > 1) { name = t; break; }
  }
  if (!name) name = link.innerText.trim().split("\\n")[0].trim();
  if (!name || name === "LinkedIn Member" || name.length < 2) continue;

  seen.add(url);

  var card = link.closest("li") || link.closest("article") || link.closest("[class*='result']");
  var title = "", company = "", location = "";
  if (card) {
    var allText = card.innerText.split("\\n").map(function(s){return s.trim();}).filter(Boolean);
    var nameIdx = -1;
    for (var j = 0; j < allText.length; j++) {
      if (allText[j] === name) { nameIdx = j; break; }
    }
    title    = nameIdx >= 0 && allText[nameIdx+1] ? allText[nameIdx+1] : (allText[1] || "");
    company  = nameIdx >= 0 && allText[nameIdx+2] ? allText[nameIdx+2] : (allText[2] || "");
    location = nameIdx >= 0 && allText[nameIdx+3] ? allText[nameIdx+3] : (allText[3] || "");
  }

  out.push({ url: url, name: name, title: title, company: company, location: location });
}
return out;
}""")

            logger.info(f"[Scraper] {len(profiles)} profils extraits (page {page_num})")

            if not profiles:
                await _screenshot(f"debug_search_page{page_num}_0profiles.png")
                logger.warning(
                    f"[Scraper] 0 profils extraits malgré {n_links} liens /in/ dans le DOM — "
                    f"screenshot sauvegardé"
                )
                break

            results.extend(profiles)
            if len(results) >= max_results:
                break

            # ── Pagination ────────────────────────────────────────────────────
            next_btn = None
            for sel in [
                "button[aria-label='Next']",
                "button[aria-label='Suivant']",
                ".artdeco-pagination__button--next",
            ]:
                try:
                    btn = await page.query_selector(sel)
                    if btn:
                        disabled = await btn.get_attribute("disabled")
                        if disabled is None:
                            next_btn = btn
                            break
                except Exception:
                    continue

            if not next_btn:
                logger.info("[Scraper] Dernière page atteinte")
                break

            await next_btn.click()
            await page.wait_for_load_state("networkidle", timeout=20000)
            await _human_delay(2, 3)
            page_num += 1

    except Exception as e:
        logger.error(f"[Scraper] Erreur search_people: {e}", exc_info=True)

    logger.info(f"[Scraper] {len(results[:max_results])} profils retournés au total")
    return results[:max_results]


# ── Recherche d'offres d'emploi ───────────────────────────────────────────────
async def search_jobs(
    page,
    keyword: str,
    location: str = "",
    niche: str = "",
    filters: dict | None = None,
    max_results: int = 20,
) -> list[dict]:
    """
    Scrape les offres d'emploi LinkedIn Jobs.

    Retourne une liste de dicts :
        {url, title, company, location, posted, job_id}

    Args:
        keyword   : Titre du poste / mots-clés (ex: "Ingénieur IA", "ML Engineer")
        location  : Ville ou pays (ex: "France", "Paris")
        niche     : Filtre niche ajouté aux mots-clés (ex: "GenAI LLM RAG")
        filters   : Filtres additionnels LinkedIn (ex: {"f_TPR": "r2592000"} = 30 derniers jours)
        max_results : Nombre max d'offres à retourner
    """
    import pathlib
    import urllib.parse

    DATA_DIR_ABS = pathlib.Path(__file__).parent.parent / "data"
    DATA_DIR_ABS.mkdir(exist_ok=True)

    async def _screenshot(name: str) -> None:
        try:
            await page.screenshot(path=str(DATA_DIR_ABS / name), full_page=False)
        except Exception:
            pass

    # Construire les mots-clés : keyword + niche
    full_keyword = " ".join(filter(None, [keyword, niche])).strip()

    params = {
        "keywords": full_keyword,
        "origin": "JOB_SEARCH_PAGE_KEYWORD_AUTOCOMPLETE",
    }
    if location:
        params["location"] = location
    if filters:
        params.update(filters)

    search_url = f"{LINKEDIN_BASE}/jobs/search/?" + urllib.parse.urlencode(params)
    logger.info(f"[Scraper] Jobs URL: {search_url}")

    results: list[dict] = []

    try:
        try:
            await page.goto(search_url, wait_until="domcontentloaded", timeout=30000)
        except Exception:
            await page.goto(search_url, wait_until="commit", timeout=30000)

        await asyncio.sleep(4)
        await page.evaluate("window.scrollTo(0, 600)")
        await asyncio.sleep(2)

        await _screenshot("debug_jobs_loaded.png")

        page_num = 1
        while len(results) < max_results:
            logger.info(f"[Scraper] Jobs — page {page_num}")

            # Scroll progressif pour déclencher le lazy-load des cartes
            for pos in [400, 800, 1200, 1600]:
                await page.evaluate(f"window.scrollTo(0, {pos})")
                await asyncio.sleep(0.6)
            await page.evaluate("window.scrollTo(0, 0)")
            await _human_delay(1.5, 2.5)

            # Extraire les cartes d'offres via JS
            # LinkedIn Jobs : chaque offre est dans un <li> avec un lien /jobs/view/<id>/
            jobs = await page.evaluate("""() => {
var seen = new Set();
var out = [];
// Liens vers les offres : /jobs/view/ ou /jobs/collections/
var links = Array.from(document.querySelectorAll(
    "a[href*='/jobs/view/'], a[href*='/jobs/collections/']"
));
for (var i = 0; i < links.length; i++) {
    var link = links[i];
    var href = (link.href || "").split("?")[0].split("&")[0];
    if (!href || seen.has(href)) continue;
    // Ne garder que les liens /jobs/view/
    if (href.indexOf("/jobs/view/") === -1) continue;
    seen.add(href);

    // Extraire l'ID du job depuis l'URL
    var jobIdMatch = href.match(/\\/jobs\\/view\\/(\\d+)/);
    var jobId = jobIdMatch ? jobIdMatch[1] : "";

    // Remonter vers la carte parente (li ou article)
    var card = link.closest("li") || link.closest("article") || link.closest("[class*='job-card']");
    var title = "", company = "", loc = "", posted = "";

    if (card) {
        // Titre du poste
        var titleEl = card.querySelector(
            "[class*='job-card-list__title'], [class*='job-card__title'], " +
            "h3, h4, [aria-label]"
        );
        title = titleEl ? titleEl.innerText.trim() : link.innerText.trim().split("\\n")[0];

        // Entreprise
        var companyEl = card.querySelector(
            "[class*='job-card-container__company'], [class*='subtitle'], " +
            "[class*='company-name'], [class*='job-card__company']"
        );
        company = companyEl ? companyEl.innerText.trim().split("\\n")[0] : "";

        // Localisation
        var locEl = card.querySelector(
            "[class*='job-card__location'], [class*='location'], " +
            "[class*='job-card-container__metadata']"
        );
        loc = locEl ? locEl.innerText.trim().split("\\n")[0] : "";

        // Date de publication
        var dateEl = card.querySelector("time, [class*='date'], [class*='listed']");
        posted = dateEl ? (dateEl.getAttribute("datetime") || dateEl.innerText.trim()) : "";
    } else {
        title = link.innerText.trim().split("\\n")[0];
    }

    if (!title || title.length < 3) continue;
    out.push({ url: href, title: title, company: company, location: loc, posted: posted, job_id: jobId });
}
return out;
}""")

            logger.info(f"[Scraper] {len(jobs)} offres extraites (page {page_num})")

            if not jobs:
                await _screenshot(f"debug_jobs_page{page_num}_0results.png")
                txt = await page.evaluate("() => document.body.innerText.substring(0, 2000)")
                (DATA_DIR_ABS / "debug_jobs_text.txt").write_text(txt, encoding="utf-8")
                logger.warning("[Scraper] 0 offres extraites — voir debug_jobs_text.txt")
                break

            results.extend(jobs)
            if len(results) >= max_results:
                break

            # Pagination
            import re as _re

            next_loc = page.get_by_role("button", name=_re.compile(r"^(Next|Suivant)$", _re.I))
            try:
                nc = await next_loc.count()
                found_next = False
                for i in range(nc):
                    btn = next_loc.nth(i)
                    if await btn.is_visible() and await btn.is_enabled():
                        await btn.click()
                        await page.wait_for_load_state("domcontentloaded", timeout=20000)
                        await _human_delay(2, 3)
                        page_num += 1
                        found_next = True
                        break
                if not found_next:
                    logger.info("[Scraper] Jobs — dernière page atteinte")
                    break
            except Exception:
                logger.info("[Scraper] Jobs — pagination introuvable")
                break

    except Exception as e:
        logger.error(f"[Scraper] Erreur search_jobs: {e}", exc_info=True)

    logger.info(f"[Scraper] {len(results[:max_results])} offres retournées")
    return results[:max_results]


# ── Extraction du recruteur depuis une offre d'emploi ────────────────────────
async def get_job_recruiter(page, job_url: str) -> dict:
    """
    Visite une page d'offre LinkedIn et extrait le recruteur ("Meet the hiring team").

    Retourne un dict :
        {recruiter_url, recruiter_name, recruiter_title, job_title, company, description}
    Retourne un dict vide si aucun recruteur n'est trouvé.
    """
    result: dict = {}
    try:
        await page.goto(job_url, wait_until="domcontentloaded", timeout=30000)
        await _human_delay(2, 3)
        await page.evaluate("window.scrollTo(0, 600)")
        await _human_delay(1, 2)

        data = await page.evaluate("""() => {
var out = {
    recruiter_url: "", recruiter_name: "", recruiter_title: "",
    job_title: "", company: "", description: ""
};

// Titre du poste
var titleEl = document.querySelector(
    "h1.t-24, h1[class*='job-title'], .job-details-jobs-unified-top-card__job-title h1, h1"
);
out.job_title = titleEl ? titleEl.innerText.trim() : "";

// Entreprise
var companyEl = document.querySelector(
    "[class*='company-name'] a, [class*='topcard__org-name'] a, " +
    ".job-details-jobs-unified-top-card__company-name a"
);
out.company = companyEl ? companyEl.innerText.trim() : "";

// Section "Meet the hiring team" (section recruteur)
// LinkedIn affiche cette section sous le nom "Rencontrez l'équipe de recrutement" (FR)
// ou "Meet the hiring team" (EN)
var sections = Array.from(document.querySelectorAll("section, div[class*='hiring-team']"));
for (var i = 0; i < sections.length; i++) {
    var sec = sections[i];
    var txt = sec.innerText || "";
    if (txt.indexOf("hiring team") !== -1 || txt.indexOf("recrutement") !== -1 ||
        txt.indexOf("Recruiter") !== -1 || txt.indexOf("Recruteur") !== -1) {
        // Chercher le lien profil dans cette section
        var profileLink = sec.querySelector("a[href*='/in/']");
        if (profileLink) {
            out.recruiter_url = profileLink.href.split("?")[0];
            // Nom du recruteur
            var nameSpan = profileLink.querySelector("span[aria-hidden='true'], span, strong");
            out.recruiter_name = nameSpan ? nameSpan.innerText.trim() : profileLink.innerText.trim().split("\\n")[0];
            // Titre du recruteur
            var allText = sec.innerText.split("\\n").map(function(s){return s.trim();}).filter(Boolean);
            var nameIdx = allText.indexOf(out.recruiter_name);
            out.recruiter_title = (nameIdx >= 0 && allText[nameIdx+1]) ? allText[nameIdx+1] : "";
            break;
        }
    }
}

// Description du poste (premiers 1000 chars)
var descEl = document.querySelector(
    "[class*='job-description'] .jobs-description-content__text, " +
    "[class*='description__text'], .jobs-box__html-content"
);
out.description = descEl ? descEl.innerText.trim().substring(0, 1000) : "";

return out;
}""")

        result = data
        if result.get("recruiter_url"):
            logger.info(
                f"[Scraper] Recruteur trouvé: {result['recruiter_name']} "
                f"({result['recruiter_url']}) pour {job_url}"
            )
        else:
            logger.info(f"[Scraper] Pas de recruteur trouvé pour {job_url}")

    except Exception as e:
        logger.error(f"[Scraper] Erreur get_job_recruiter({job_url}): {e}")

    return result


# ── Extraction d'un profil ────────────────────────────────────────────────────
async def get_profile_info(page, profile_url: str) -> dict:
    """
    Visite un profil LinkedIn et extrait les informations clés.
    Retourne un dict enrichi pour l'agent de note.
    """
    try:
        await page.goto(profile_url, wait_until="networkidle")
        await _human_delay(2, 4)

        # Scroll pour charger le contenu lazy
        await page.evaluate("window.scrollTo(0, 500)")
        await _human_delay(1, 2)

        info = await page.evaluate("""
            () => {
                const getText = (sel) => {
                    const el = document.querySelector(sel);
                    return el ? el.innerText.trim() : '';
                };

                // About section
                const aboutBtn = document.querySelector(
                    '#about ~ .pvs-list__outer-container .inline-show-more-text__button, '
                    '.pv-shared-text-with-see-more button'
                );
                if (aboutBtn) aboutBtn.click();

                return {
                    name: getText('h1'),
                    title: getText('.text-body-medium.break-words'),
                    company: getText(
                        '.pv-text-details__right-panel .hoverable-link-text span[aria-hidden]'
                    ),
                    location: getText('.text-body-small.inline.t-black--light.break-words'),
                    about: getText('#about ~ .pvs-list__outer-container .full-width, '
                                  '.pv-shared-text-with-see-more span[aria-hidden]'),
                    followers: getText('.pvs-header__subtitle .t-bold'),
                };
            }
        """)

        info["about"] = info.get("about", "")[:600]
        info["url"] = profile_url
        return info

    except Exception as e:
        logger.error(f"[Scraper] Erreur get_profile_info({profile_url}): {e}")
        return {"url": profile_url, "name": "", "title": "", "company": "", "about": ""}


# ── Check acceptance status ──────────────────────────────────────────────────
async def check_acceptance_status(page, profile_url: str) -> str:
    """
    Visite un profil LinkedIn et retourne le statut de la connexion :

      "accepted"  → la personne a accepté (badge "1er" / "1st")
      "pending"   → invitation toujours en attente (bouton Retirer/Withdraw présent)
      "unknown"   → impossible de déterminer (page inaccessible, profil supprimé…)

    Aucune action n'est effectuée — lecture seule.
    """
    try:
        await page.goto(profile_url, wait_until="domcontentloaded")
        await _human_delay(1.5, 2.5)

        status = await page.evaluate("""() => {
            // ── 1. Badge de degré "1er" ou "1st" → accepté ──────────────────
            var degreeSelectors = [
                ".dist-value",
                "[class*='distance']",
                "[class*='degree']",
            ];
            for (var sel of degreeSelectors) {
                var el = document.querySelector(sel);
                if (el) {
                    var t = el.innerText.trim();
                    if (t.indexOf("1er") !== -1 || t.indexOf("1st") !== -1) {
                        return "accepted";
                    }
                }
            }
            // Cherche dans tous les spans courts (le badge degré est souvent un span isolé)
            var spans = Array.from(document.querySelectorAll("span"));
            for (var s of spans) {
                var t = s.innerText.trim();
                if (t === "1er" || t === "1st" || t === "1er degré" || t === "1st degree") {
                    return "accepted";
                }
            }

            // ── 2. Bouton Retirer / Withdraw → toujours en attente ───────────
            var buttons = Array.from(document.querySelectorAll("button"));
            for (var b of buttons) {
                var label = (b.getAttribute("aria-label") || b.innerText || "").trim();
                if (label.indexOf("Retirer") !== -1 || label.indexOf("Withdraw") !== -1 ||
                    label.indexOf("En attente") !== -1 || label.indexOf("Pending") !== -1) {
                    return "pending";
                }
            }

            // ── 3. Bouton "Se connecter" visible → invitation non envoyée / refusée
            for (var b of buttons) {
                var label = (b.getAttribute("aria-label") || b.innerText || "").trim();
                if (label === "Se connecter" || label === "Connect") {
                    return "unknown";
                }
            }

            return "unknown";
        }""")

        logger.info(f"[Scraper] check_acceptance({profile_url}) → {status}")
        return status

    except Exception as e:
        logger.error(f"[Scraper] check_acceptance error ({profile_url}): {e}")
        return "unknown"


# ── Send connection request ───────────────────────────────────────────────────
async def send_connection_request(
    page,
    profile_url: str,
    note: str,
) -> bool:
    """
    Envoie une demande de connexion LinkedIn avec note personnalisée.
    Gère FR + EN. Détecte connexions existantes via le badge de degré.

    Retourne True  → invitation envoyée avec succès
    Retourne False → déjà connecté / invitation en attente / bouton introuvable

    Implémenté avec le Playwright locator API (get_by_role) — plus fiable que
    evaluate_handle+JS car Playwright gère l'attente et la visibilité nativement.
    """
    import pathlib
    import re as _re

    note = note[:300]
    DATA_DIR = pathlib.Path(__file__).parent.parent / "data"
    DATA_DIR.mkdir(exist_ok=True)

    try:
        await page.goto(profile_url, wait_until="domcontentloaded")
        await _human_delay(2, 3)
        await page.evaluate("window.scrollTo(0, 300)")
        await _human_delay(1, 2)

        # ── 0. Détecter si déjà connecté via le badge de DEGRÉ ───────────────
        # LinkedIn affiche "• 1er" ou "• 1st" directement sur la page profil.
        # On utilise page.evaluate (lecture pure, pas de click) — fiable.
        degree_info = await page.evaluate("""() => {
            var degreeEl = document.querySelector(".dist-value, [class*='distance']");
            if (degreeEl) return degreeEl.innerText.trim();
            var spans = Array.from(document.querySelectorAll("span"));
            for (var s of spans) {
                var t = s.innerText.trim();
                if (t === "1er" || t === "1st" || t === "1st degree connection") return t;
            }
            return "";
        }""")
        if degree_info and ("1er" in degree_info or "1st" in degree_info):
            logger.info(f"[Scraper] Déjà connecté (degré={degree_info}): {profile_url}")
            return False

        # ── 1. Invitation déjà envoyée (bouton Retirer / Withdraw / En attente) ──
        pending_info = await page.evaluate("""() => {
            var buttons = Array.from(document.querySelectorAll("button"));
            for (var b of buttons) {
                var label = (b.getAttribute("aria-label") || b.innerText || "").trim();
                if (label.indexOf("Retirer") !== -1 || label.indexOf("Withdraw") !== -1 ||
                    label.indexOf("En attente") !== -1 || label.indexOf("Pending") !== -1) {
                    return label.slice(0, 60);
                }
            }
            return "";
        }""")
        if pending_info:
            logger.info(f"[Scraper] Invitation en attente ({pending_info}): {profile_url}")
            return False

        # ── 2. Chercher bouton Connect via locator API (FR + EN) ──────────────
        # get_by_role est robuste : Playwright cherche par accessible name,
        # gère les éléments chargés en async et la visibilité nativement.
        _CONNECT_RE = _re.compile(r"^(Se connecter|Connect|Inviter|Invite)(\s|$)", _re.IGNORECASE)
        connect_btn = None

        connect_loc = page.get_by_role("button", name=_CONNECT_RE)
        try:
            count = await connect_loc.count()
            for i in range(count):
                btn = connect_loc.nth(i)
                if await btn.is_visible():
                    connect_btn = btn
                    logger.info(f"[Scraper] Bouton Connect trouvé via locator (#{i})")
                    break
        except Exception as e:
            logger.debug(f"[Scraper] locator Connect: {e}")

        # ── 3. Si pas trouvé → ouvrir menu "Plus" / "More actions" ───────────
        if not connect_btn:
            _MORE_RE = _re.compile(
                r"Plus d.options|Plus|More actions|More|Actions supplémentaires", _re.IGNORECASE
            )
            more_loc = page.get_by_role("button", name=_MORE_RE)
            try:
                mc = await more_loc.count()
                for i in range(mc):
                    m = more_loc.nth(i)
                    if await m.is_visible():
                        await m.click()
                        await _human_delay(0.8, 1.5)
                        logger.info("[Scraper] Menu Plus ouvert — recherche Connect dedans")
                        break
            except Exception as e:
                logger.debug(f"[Scraper] Menu Plus: {e}")

            # Chercher Connect dans le menu déroulant (role=menuitem ou button)
            for role in ("menuitem", "button", "option"):
                try:
                    loc2 = page.get_by_role(role, name=_CONNECT_RE)
                    c2 = await loc2.count()
                    for i in range(c2):
                        btn = loc2.nth(i)
                        if await btn.is_visible():
                            connect_btn = btn
                            logger.info(f"[Scraper] Connect trouvé dans menu (role={role}, #{i})")
                            break
                    if connect_btn:
                        break
                except Exception:
                    continue

        # ── 4. Toujours pas trouvé → screenshot debug + skip ─────────────────
        if not connect_btn:
            slug = profile_url.rstrip("/").split("/")[-1]
            debug_path = str(DATA_DIR / f"debug_connect_{slug}.png")
            try:
                await page.screenshot(path=debug_path, full_page=False)
                logger.warning(
                    f"[Scraper] Bouton Connect introuvable — screenshot: {debug_path} | {profile_url}"
                )
            except Exception:
                logger.warning(f"[Scraper] Bouton Connect introuvable: {profile_url}")
            return False

        # ── 5. Cliquer Connect ────────────────────────────────────────────────
        await connect_btn.click()
        await _human_delay(1, 2)

        # ── 6. "Ajouter une note" / "Add a note" ─────────────────────────────
        _ADD_NOTE_RE = _re.compile(r"Ajouter une note|Add a note", _re.IGNORECASE)
        add_note_loc = page.get_by_role("button", name=_ADD_NOTE_RE)
        try:
            if await add_note_loc.count() > 0 and await add_note_loc.first.is_visible():
                await add_note_loc.first.click()
                await _human_delay(0.8, 1.5)
                logger.info("[Scraper] Bouton 'Ajouter une note' cliqué")

                # ── 7. Remplir le champ note ──────────────────────────────────
                note_field = None
                for sel in [
                    "#custom-message",
                    'textarea[name="message"]',
                    'textarea[id*="custom"]',
                    'div[role="textbox"]',
                ]:
                    try:
                        f = await page.query_selector(sel)
                        if f and await f.is_visible():
                            note_field = f
                            break
                    except Exception:
                        continue

                if note_field:
                    await note_field.click()
                    await _human_delay(0.2, 0.5)
                    await page.keyboard.type(note, delay=random.randint(25, 65))
                    await _human_delay(0.5, 1)
                    logger.info(f"[Scraper] Note saisie ({len(note)} chars)")
                else:
                    logger.warning("[Scraper] Champ note introuvable — envoi sans note")
            else:
                logger.info("[Scraper] Bouton 'Ajouter une note' absent — envoi sans note")
        except Exception as e:
            logger.debug(f"[Scraper] 'Ajouter une note': {e}")

        # ── 8. Cliquer Envoyer / Send ─────────────────────────────────────────
        _SEND_RE = _re.compile(
            r"Envoyer l.invitation|Envoyer maintenant|Envoyer|Send invitation|Send now|Send",
            _re.IGNORECASE,
        )
        send_loc = page.get_by_role("button", name=_SEND_RE)
        try:
            sc = await send_loc.count()
            for i in range(sc):
                s = send_loc.nth(i)
                if await s.is_visible() and await s.is_enabled():
                    await s.click()
                    await _human_delay(1.5, 3)
                    logger.info(f"[Scraper] ✅ Connexion envoyée → {profile_url}")
                    return True
        except Exception as e:
            logger.warning(f"[Scraper] Bouton Envoyer locator: {e}")

        logger.warning(f"[Scraper] Bouton Envoyer introuvable: {profile_url}")
        return False

    except Exception as e:
        logger.error(f"[Scraper] Erreur send_connection({profile_url}): {e}")
        return False


# ── Context manager Playwright ────────────────────────────────────────────────
async def create_browser_context(headless: bool = False):
    """
    Cree et retourne (playwright, browser, context, page).
    Utilise headless=False par defaut pour eviter la detection LinkedIn.

    Nettoyage : await browser.close() puis await pw.stop()
    (PAS pw.__aexit__ — utiliser .start()/.stop())
    """
    from playwright.async_api import async_playwright

    # Utiliser .start() au lieu de __aenter__() pour pouvoir appeler .stop() proprement
    pw = await async_playwright().start()
    browser = await pw.chromium.launch(
        headless=headless,
        args=[
            "--disable-blink-features=AutomationControlled",
            "--no-sandbox",
        ],
    )
    context = await browser.new_context(
        user_agent=USER_AGENT,
        viewport={"width": 1280, "height": 800},
        locale="fr-FR",
    )
    # Masquer la signature automation
    await context.add_init_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )
    page = await context.new_page()
    return pw, browser, context, page
