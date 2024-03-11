# Utiliser l'image de base python
FROM python:3.9

# Définir le répertoire de travail dans le conteneur
WORKDIR /app

# Copier le contenu actuel du répertoire vers le répertoire de travail dans le conteneur
COPY . /app

# Installer les dépendances
RUN pip install --no-cache-dir -r requirements.txt

# Exposer le port 8000 pour que FastAPI puisse être accessible depuis l'extérieur du conteneur
EXPOSE 8000

# Commande pour démarrer l'application FastAPI lorsque le conteneur démarre
CMD ["uvicorn", "main2:app", "--host", "0.0.0.0", "--port", "8000"]
