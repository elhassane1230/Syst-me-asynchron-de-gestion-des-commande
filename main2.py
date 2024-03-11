########## Importation des modules nécessaires ##########
import asyncio
from fastapi import FastAPI, HTTPException, BackgroundTasks, Request, Depends, Form, Cookie
from sqlalchemy import create_engine, Column, Integer, String, Float, ForeignKey, Boolean
from sqlalchemy.orm import sessionmaker, relationship, Session
from sqlalchemy.ext.declarative import declarative_base
from pydantic import BaseModel
from fastapi.responses import HTMLResponse
from typing import List
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
import plotly.graph_objects as go


########## Définition du modèle OrderRequest ##########
class OrderRequest(BaseModel):
    item: str
    quantity: int


########## Création de l'application FastAPI ##########
app = FastAPI()

########## Configuration de la base de données ##########
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Définition des modèles de données pour SQLAlchemy
class Client(Base):
    __tablename__ = "clients"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    email = Column(String, unique=True, index=True)
    phone_number = Column(String)
    username = Column(String, unique=True)  
    password = Column(String)  
    orders = relationship("Order", back_populates="client")
    quotes = relationship("Quote", back_populates="client")

class Order(Base):
    __tablename__ = "orders"
    id = Column(Integer, primary_key=True, index=True)
    item = Column(String, index=True)
    quantity = Column(Integer)
    validated = Column(Boolean, default=False) 
    executed =  Column(Boolean, default=False) 
    client_id = Column(Integer, ForeignKey('clients.id'))
    client = relationship("Client", back_populates="orders")
    quote = relationship("Quote", uselist=False, back_populates="order")
    service_completion = relationship("ServiceCompletion", uselist=False, back_populates="order")

class Quote(Base):
    __tablename__ = "quotes"
    id = Column(Integer, primary_key=True, index=True)
    amount = Column(Float)
    confirmed = Column(Boolean, default=False)
    validated = Column(Boolean, default=False)  
    client_id = Column(Integer, ForeignKey('clients.id'))
    order_id = Column(Integer, ForeignKey('orders.id'))
    order = relationship("Order", back_populates="quote")
    client = relationship("Client", back_populates="quotes")

class ServiceCompletion(Base):
    __tablename__ = "service_completions"
    id = Column(Integer, primary_key=True, index=True)
    details = Column(String)
    recived = Column(Boolean, default=False)
    order_id = Column(Integer, ForeignKey('orders.id'))
    order = relationship("Order", back_populates="service_completion")

class Inventory(Base):
    __tablename__ = "inventory"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True)
    quantity = Column(Integer)
    price = Column(Integer)

# Création des tables dans la base de données
Base.metadata.create_all(bind=engine)

########## Fin de la base de données ##########



########## Login ############

from fastapi.responses import HTMLResponse

# Variable globale pour stocker l'ID du client connecté
current_client_id = None

# Endpoint pour la connexion
@app.post("/login/")
async def login(username: str = Form(...), password: str = Form(...)):
    global current_client_id  # Déclarer la variable comme globale
    
    try:
        db = SessionLocal()
        # Recherche du client dans la base de données
        client = db.query(Client).filter(Client.username == username, Client.password == password).first()
        db.close()
        
        if client:
            current_client_id = client.id  # Stocker l'ID du client connecté
            # Redirection vers la page du client
            return RedirectResponse("/client", status_code=302)
        elif username == "admin" and password == "12345":
            # Redirection vers la page de l'administrateur
            return RedirectResponse("/admin", status_code=302)
        else:
            # Affichage du message d'erreur sur la même page
            error_message = "Nom d'utilisateur ou mot de passe incorrect"
            return HTMLResponse(f"""<script>alert("{error_message}"); window.location.href="/";</script>""")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Fonction pour récupérer l'ID du client connecté
def get_current_client():
    global current_client_id
    return current_client_id

############ Fin Login ################



############ Logout ################

# Endpoint pour la déconnexion
@app.get("/logout/")
async def logout():
    current_client_id = None  
    return RedirectResponse("/", status_code=302)

############ Fin Logout ################



########## Process ##########

# Endpoint pour initier une commande par le client
@app.post("/place_order/")
async def place_order(order: OrderRequest, background_tasks: BackgroundTasks):
    background_tasks.add_task(process_order, order)
    return {"message": "Commande reçue, est envoyé pour le traitement"}

# Fonction pour traiter la commande
async def process_order(order: OrderRequest):
    try:
        # Enregistrement de la commande dans la base de données
        db = SessionLocal()
        client = db.query(Client).filter(Client.id == current_client_id).first()
        if client is None:
            raise HTTPException(status_code=404, detail="Client Intouvable")
        
        new_order = Order(item=order.item, quantity=order.quantity, client_id=current_client_id)
        db.add(new_order)
        db.commit()
        db.refresh(new_order)
        db.close()


        # Logique de vérification de commande
        while True:
            db = SessionLocal()
            validated_order = db.query(Order).filter(Order.id == new_order.id, Order.validated == True).first()
            db.close()
            if validated_order:
                break    
            await asyncio.sleep(2)
        
        
        # Génération du devis
        quote = generate_quote(new_order,current_client_id)
        await request_quote_validation(quote)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Fonction pour générer un devis
def generate_quote(order: Order, client_id: int) -> Quote:
    db = SessionLocal()
    inventory_item = db.query(Inventory).filter(Inventory.name == order.item).first()
    if inventory_item is None:
        raise ValueError("L'article spécifié n'existe pas dans l'inventaire.")
    item_price = inventory_item.price
    amount = item_price * order.quantity * 1.05
    new_quote = Quote(amount=amount, order=order, client_id=client_id)
    
    
    # Enregistrement du devis dans la base de données
    db = SessionLocal()
    db.add(new_quote)
    db.commit()
    db.close()
    
    return new_quote

# Fonction pour valider un devis
async def request_quote_validation(quote: Quote):
    try:
        while True:
            async with SessionLocal() as db:
                validated_quote = await db.query(Quote).filter(Quote.order_id == quote.order_id, Quote.validated == True).first()
                if validated_quote:
                    break
            await asyncio.sleep(1)
    except Exception as e:
        print(f"Error in request_quote_validation: {e}")



# Endpoint pour la validation d'une commande par le fournisseur
@app.post("/validate_order")
async def validate_order(order_id: int = Form(...), confirmation: bool = Form(...)):
    try:
        # Récupération de la commande depuis la base de données
        db = SessionLocal()
        order = db.query(Order).filter(Order.id == order_id).first()
        if order is None:
            raise HTTPException(status_code=404, detail="Commande Invtrouvable")
        
        # Mettre à jour le statut de validation du devis en fonction de la confirmation de l'utilisateur
        order.validated = confirmation
        
        # Sauvegarder les modifications dans la base de données
        db.commit()
        db.close()
        message1 = "La commande a été validé avec succès!!"
        message2 = "La commande a été refusé !!"

        # Retourner un message de confirmation à l'utilisateur
        if confirmation:
            return HTMLResponse(f"<script>alert('{message1}'); window.location.href='/admin';</script>")
        else:
            return HTMLResponse(f"<script>alert('{message2}'); window.location.href='/admin';</script>")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# Endpoint pour la validation du devis par le fournisseur 
@app.post("/validate_quote")
async def validate_quote(quote_id: int = Form(...), confirmation: bool = Form(...)):
    try:
        # Vérifier si le devis avec l'ID spécifié existe dans la base de données
        db = SessionLocal()
        quote = db.query(Quote).filter(Quote.id == quote_id).first()
        if quote is None:
            raise HTTPException(status_code=404, detail="Devis Introuvable")
        
        # Mettre à jour le statut de validation du devis en fonction de la confirmation de l'utilisateur
        quote.validated = confirmation
        
        # Sauvegarder les modifications dans la base de données
        db.commit()
        db.close()
        message1 = "Le devis a été validé avec succès!!"
        message2 = "Le devis a été refusé !!"

        # Retourner un message de confirmation à l'utilisateur
        if confirmation:
            return HTMLResponse(f"<script>alert('{message1}'); window.location.href='/admin';</script>")
        else:
            return HTMLResponse(f"<script>alert('{message2}'); window.location.href='/admin';</script>")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# Endpoint pour la confirmation ou le refus du devis par le client
@app.post("/confirm_quote")
async def confirm_quote(quote_id: int = Form(...), confirmation: bool = Form(...)):
    try:
        # Récupération du devis depuis la base de données
        db = SessionLocal()
        quote = db.query(Quote).filter(Quote.id == quote_id).first()
        if quote is None:
            raise HTTPException(status_code=404, detail="Devis Invtrouvable")
        
        # Mettre à jour le statut de validation du devis en fonction de la confirmation de l'utilisateur
        quote.confirmed = confirmation
        
        # Sauvegarder les modifications dans la base de données
        db.commit()
        db.close()
        message1 = "Le devis a été confirmé avec succès!!"
        message2 = "Le devis a été refusé !!"

        # Retourner un message de confirmation à l'utilisateur
        if confirmation:
            return HTMLResponse(f"<script>alert('{message1}'); window.location.href='/client';</script>")
        else:
            return HTMLResponse(f"<script>alert('{message2}'); window.location.href='/client';</script>")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint pour l'exécution du service par le fournissuer
@app.post("/execute_service")
async def execute_service(order_id: int= Form(...)):
    try:
        # Récupération de la commande depuis la base de données
        db = SessionLocal()
        order = db.query(Order).filter(Order.id == order_id).first()
        if order is None:
            raise HTTPException(status_code=404, detail="Commande Invtrouvable")
        
        quote = order.quote
        if quote is None or not (quote.validated and quote.confirmed):
            raise HTTPException(status_code=400, detail="Quote not validated and confirmed")

        order.executed = True
        
        # Après l'exécution du service, générez un événement de réalisation de service
        service_completion = ServiceCompletion(details="Service executed successfully", order_id=order_id)
        db.add(service_completion)
        db.commit()
        db.close()

        message= "Commande executé avec succès"
        return HTMLResponse(f"<script>alert('{message}'); window.location.href='/admin';</script>")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# Endpoint pour la vérification de la réalisation du service par le client
@app.post("/verify_service_completion")
async def verify_service_completion(order_id: int = Form(...), confirmation: bool = Form(...)):
    try:
        # Récupération de la commande depuis la base de données
        db = SessionLocal()
        order = db.query(Order).filter(Order.id == order_id).first()
        if order is None:
            raise HTTPException(status_code=404, detail="Order not found")
        
        # Récupération de l'objet ServiceCompletion lié à cette commande
        completion = db.query(ServiceCompletion).filter(ServiceCompletion.order_id == order_id).first()
        if completion is None:
            raise HTTPException(status_code=404, detail="Service Invtrouvable")

        # Mise à jour du champ recived en fonction de la valeur de confirmation
        completion.recived = confirmation

        # Sauvegarde des modifications dans la base de données
        db.commit()

        message = "Commande reçue avec succès"
        return HTMLResponse(f"<script>alert('{message}'); window.location.href='/client';</script>")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# Endpoint pour la conclusion du processus
@app.post("/conclude_process")
async def conclude_process(order_id: int = Form(...)):
    try:
        # Récupération de la commande depuis la base de données
        db = SessionLocal()
        order = db.query(Order).filter(Order.id == order_id).first()
        if order is None:
            raise HTTPException(status_code=404, detail="Commande Invtrouvable")
        
        # Vérification de la réalisation du service par le client
        completion = db.query(ServiceCompletion).filter(ServiceCompletion.order_id == order_id).first()
        if completion is None or not completion.recived:
            raise HTTPException(status_code=400, detail="Commande non executé ou non reçue")

        # Mise à jour de l'inventaire
        inventory = db.query(Inventory).filter(Inventory.name == order.item).first()
        if inventory is None:
            raise HTTPException(status_code=404, detail="Produit Invtrouvable")
        inventory.quantity -= order.quantity

        db.commit()
        db.close()
        
        message =  "Process finalisé avec succès"
        return HTMLResponse(f"<script>alert('{message}'); window.location.href='/admin';</script>")

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



#consultation etat de stock, les commandes et les devis (pour la validation par intervetion humain)

# Endpoint pour obtenir le stock
@app.get("/inventory")
async def get_inventory():
    try:
        db = SessionLocal()
        inventory = db.query(Inventory).all()
        db.close()
        return [{"name": item.name, "quantity": item.quantity, "price": item.price} for item in inventory]
    except Exception as e:
        return {"error": str(e)}



########## Endpoints pour la redirection et l'affichage #############

templates = Jinja2Templates(directory="templates")

# Endpoint pour afficher la page d'accueil
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})



# Endpoint pour la page client
@app.get("/client", response_class=HTMLResponse)
async def client_page(request: Request):
    try:
        db = SessionLocal()
        current_client_id = get_current_client()  # Récupérer l'ID du client connecté
        if current_client_id:
            # Récupérer les devis du client connecté depuis la base de données
            client_orders = db.query(Order).filter(Order.client_id == current_client_id).all()
            client_quotes = db.query(Quote).filter(Quote.client_id == current_client_id).all()
            db.close()
            return templates.TemplateResponse("client.html", {"request": request, "client_orders": client_orders, "client_quotes": client_quotes})
        else:
            return HTTPException(status_code=401, detail="Veuillez vous connecter en tant que client.")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint pour la page administrateur
@app.get("/admin", response_class=HTMLResponse)
async def admin_page(request: Request):
    try:
        db = SessionLocal()
        all_orders = db.query(Order).all()
        validated_orders = db.query(Order).filter(Order.validated == True).all()
        not_validated_orders = db.query(Order).filter(Order.validated == False).all()

        all_quotes = db.query(Quote).all()
        validated_quotes = db.query(Quote).filter(Quote.validated == True).all()
        not_validated_quotes = db.query(Quote).filter(Quote.validated == False).all()
        db.close()

        # Création des données pour la visualisation
        validated_quote_count = len(validated_quotes)
        not_validated_quote_count = len(not_validated_quotes)

        validated_order_count = len(validated_orders)
        not_validated_order_count = len(not_validated_orders)
        
        # Création du graphique à barres
        fig1 = go.Figure()
        fig1.add_trace(go.Bar(name='Validated', x=['Validated'], y=[validated_quote_count], marker_color='green'))
        fig1.add_trace(go.Bar(name='Not Validated', x=['Not Validated'], y=[not_validated_quote_count], marker_color='red'))
        fig1.update_layout(title_text='Distribution des devis (valider vs Non Valider)', barmode='group')

        fig2 = go.Figure()
        fig2.add_trace(go.Bar(name='Validated', x=['Validated'], y=[validated_order_count], marker_color='green'))
        fig2.add_trace(go.Bar(name='Not Validated', x=['Not Validated'], y=[not_validated_order_count], marker_color='red'))
        fig2.update_layout(title_text='Distribution des commandes(Valider vs Non Valider)', barmode='group')

            
        # Convertir le graphique en HTML
        plot_html1 = fig1.to_html(full_html=False, include_plotlyjs='cdn')
        plot_html2 = fig2.to_html(full_html=False, include_plotlyjs='cdn')

        return templates.TemplateResponse("admin.html", {"request": request, "all_orders": all_orders, "all_quotes": all_quotes, "plot_html1": plot_html1, "plot_html2": plot_html2})
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Endpoint pour la page validate_order
@app.get("/validate_order", response_class=HTMLResponse)
async def validateO_page(request: Request):
    return templates.TemplateResponse("validate_order.html", {"request": request})


# Endpoint pour la page validate_quote
@app.get("/validate_quote", response_class=HTMLResponse)
async def validateQ_page(request: Request):
    return templates.TemplateResponse("validate_quote.html", {"request": request})


# Endpoint pour la page confirm_quote
@app.get("/confirm_quote", response_class=HTMLResponse)
async def confirmQ_page(request: Request):
    return templates.TemplateResponse("confirm_quote.html", {"request": request})


# Endpoint pour la page excute_service
@app.get("/execute_service", response_class=HTMLResponse)
async def execute_service_page(request: Request):
    return templates.TemplateResponse("execute_service.html", {"request": request})

# Endpoint pour la page verify_service_completion
@app.get("/verify_service_completion", response_class=HTMLResponse)
async def verify_service_completion_page(request: Request):
    return templates.TemplateResponse("verify_service_completion.html", {"request": request})


# Endpoint pour la page conclude_process
@app.get("/conclude_process", response_class=HTMLResponse)
async def conclude_process_page(request: Request):
    return templates.TemplateResponse("conclude_process.html", {"request": request})


# Endpoint pour la page place_order
@app.get("/place_order", response_class=HTMLResponse)
async def place_order_page(request: Request):
    return templates.TemplateResponse("place_order.html", {"request": request})









