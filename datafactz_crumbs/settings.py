from datafactz.settings import TEMPLATES

TEMPLATES[0]["OPTIONS"]["context_processors"].append(
    "datafactz_crumbs.context_processors.breadcrumbs",
)
