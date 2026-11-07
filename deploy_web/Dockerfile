# Image de l'application IMMOBILE REELLE en version web.
# Construire depuis la RACINE du projet :
#   docker build -f deploy_web/Dockerfile -t immobile-web .
#   docker run -p 8000:8000 -e SUPABASE_URL=... -e SUPABASE_KEY=... \
#              -e CLOUDINARY_CLOUD_NAME=... -e CLOUDINARY_API_KEY=... -e CLOUDINARY_API_SECRET=... immobile-web
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 PIP_NO_CACHE_DIR=1 PORT=8000
WORKDIR /app

COPY deploy_web/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

# Les secrets (.env, app_env.py) ne sont JAMAIS copies (voir .dockerignore) : on les
# fournit en variables d'environnement.
COPY . /app

RUN useradd -m web && chown -R web /app
USER web

EXPOSE 8000
CMD ["python", "web_server.py"]
