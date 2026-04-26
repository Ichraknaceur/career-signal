#!/bin/bash
# ─────────────────────────────────────────────────────────────────
# Entrypoint Docker — vérifie la config avant de démarrer
# ─────────────────────────────────────────────────────────────────
set -e

echo "🚀 CareerSignal starting..."

# Vérification des clés API — au moins une doit être définie
# Le système supporte Anthropic ET OpenAI (sélectionnable dans l'UI)
if [ -z "$ANTHROPIC_API_KEY" ] && [ -z "$OPENAI_API_KEY" ]; then
    echo "⚠️  ATTENTION : Ni ANTHROPIC_API_KEY ni OPENAI_API_KEY ne sont définies."
    echo "   Le système démarrera mais les fonctions LLM seront indisponibles."
    echo "   Ajoute au moins une clé dans ton fichier .env."
else
    [ -n "$ANTHROPIC_API_KEY" ] && echo "✅ ANTHROPIC_API_KEY détectée"
    [ -n "$OPENAI_API_KEY" ]    && echo "✅ OPENAI_API_KEY détectée"
fi

echo "📋 Mode : ${ENVIRONMENT:-development}"
echo "🖥️  UI disponible sur : http://localhost:8501"
echo ""

# Créer les dossiers de données si absents
mkdir -p /app/data /app/logs

if [ "${LINKEDIN_AUTOPUBLISH_ENABLED:-false}" = "true" ]; then
    echo "🤖 Autopublication LinkedIn activée"
    uv run python autopublish.py &
fi

# Lancer Streamlit
# --server.runOnSave=true : recharge automatiquement les modules Python modifiés
#   → évite de devoir redémarrer le container après chaque changement de code
exec uv run streamlit run ui/app.py \
    --server.port=8501 \
    --server.address=0.0.0.0 \
    --server.headless=true \
    --server.runOnSave=true \
    --browser.gatherUsageStats=false
