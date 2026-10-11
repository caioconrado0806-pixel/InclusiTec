"""Entrypoint da aplicação Flask para a Vercel."""

from backend import create_app

app = create_app()
