"""WSGI entrypoint para o Azure App Service (gunicorn).

Uso (Azure): gunicorn --bind=0.0.0.0:8000 wsgi:app
"""

from backend import create_app

app = create_app()
