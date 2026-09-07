FROM python:3.11-slim
WORKDIR /app
ENV PYTHONUNBUFFERED=1
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
# Copie explicite : le .env (secrets) n'entre jamais dans l'image
COPY app.py calendrier.py db.py index.html indexnew.html ajout.html login.html tennis.png ./
EXPOSE 3020
CMD ["python", "app.py"]
