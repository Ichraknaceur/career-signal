# Schema SQLite Minimal

Le schema est defini dans
`storage/migrations/0001_initial_schema.sql`.

## Tables minimales

- `workflow_runs`
- `workflow_events`
- `content_drafts`
- `scheduled_posts`
- `contacts`
- `outreach_messages`
- `job_postings`
- `watch_topics`
- `watch_sources`
- `watch_articles`

## Pourquoi ce schema

- `workflow_runs` et `workflow_events`
  pour la tracabilite et l'audit
- `content_drafts` et `scheduled_posts`
  pour le contenu et le calendrier editorial
- `contacts` et `outreach_messages`
  pour le CRM reseau / recruteurs
- `job_postings`
  pour suivre les offres cibles
- `watch_topics`, `watch_sources`, `watch_articles`
  pour la veille technique et offres

## Exemples de statuts

- `content_drafts.status`
  `draft`, `qa_pending`, `approved`, `rejected`, `published`
- `scheduled_posts.status`
  `draft`, `approved`, `scheduled`, `publishing`, `published`, `failed`
- `outreach_messages.status`
  `pending`, `approved`, `sent`, `replied`, `accepted`, `ignored`
- `job_postings.status`
  `new`, `shortlisted`, `applied`, `interview`, `rejected`, `closed`
- `watch_articles.status`
  `new`, `reviewed`, `used`, `ignored`
