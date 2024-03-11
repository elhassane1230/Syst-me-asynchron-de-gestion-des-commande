# Syst-me-asynchron-de-gestion-des-commande

Dans le cadre des modules "Gestion de processus métiers" et "Gestion de données et services dans le Cloud", nous avons entrepris le développement d'un projet visant à créer un système de traitement de commandes asynchrone en utilisant FastAPI. Ce système se compose de deux composants principaux : un processus client permettant de passer des commandes, de confirmer les devis et de notifier la réception des commandes, et un processus fournisseur chargé de gérer les demandes de commande, de valider les commandes, de générer automatiquement les devis, d'exécuter les commandes et de clôturer les transactions

Installation des dependances : 

   - pip install SQLAlchemy
   - pip install pydantic
   - pip install fastapi
   - pip install typing_extensions
   - pip install plotly
   - pip install uvicorn
   - pip install python-multipart
   - pip install Jinja2

lancer le notebook 'projet.ipynb' pour remplir la base de données et aussi pour lancer notre API  
Apres dans votre navigateur : http://127.0.0.1:8000 ça vous deriger directement vers une page login
connexion tant ue client : username => tal / password => 1230
                           username => asse / password => 0321
connexion tant que fournisseur : username => admin / password => 12345

Deploiement Docker :
  construire un image => docker build -t projet .
  lancer l'image localement => docker run -d -p 8000:8000 projet
  apres il sufit d'ouvrir votre navigateur => http://localhost:8000/


projet réaliser par :
  - Assellaou Mouhcine
  - Bouyahyaoui Soufiane
  - Talha Elhassane
  - Turgut Syabend

