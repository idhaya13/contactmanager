from fastapi import FastAPI, Request, Form, Depends 
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from database import SessionLocal
from models import Contact
from collections import defaultdict
from google import genai  # Gemini client

app = FastAPI(title="Business AI Contact Manager")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# -------------------------------
# Gemini API key (freemium)
# -------------------------------
GEMINI_API_KEY = "AIzaSyDQFcv0TujBSyEm8LFzuGvOeX4FpyDFTsM"  # replace with your freemium key
client = genai.Client(api_key=GEMINI_API_KEY)

# -------------------------------
# Dependency: DB session
# -------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------------------
# Helper: Relationship score calculator
# -------------------------------
def relationship_score(contact: Contact) -> float:
    days_since_contact = (datetime.now() - contact.last_contact).days
    recency_score = max(0, 1 - days_since_contact / 180)
    freq_score = min(contact.frequency / 12, 1)
    return round((0.6 * recency_score + 0.4 * freq_score), 2)

# -------------------------------
# Helper: Filter contacts by months
# -------------------------------
def filter_contacts(db: Session, months=None):
    query = db.query(Contact)
    if months and months != "all":
        cutoff = datetime.now() - timedelta(days=30 * int(months))
        query = query.filter(Contact.last_contact >= cutoff)
    return query.all()

# -------------------------------
# Helper: Group contacts by company
# -------------------------------
def group_by_company(contact_list):
    groups = defaultdict(list)
    for c in contact_list:
        company = c.company or "Independent / Unknown"
        groups[company].append(c)
    return groups

# -------------------------------
# Helper: Generate AI draft email via Gemini
# -------------------------------
def generate_email_ai(contact: Contact) -> str:
    prompt_text = f"""
Write a concise, professional, friendly follow-up email to {contact.name}.
Company: {contact.company}
Notes: {contact.notes if contact.notes else "No specific notes available."}
Last contact: {contact.last_contact.strftime('%Y-%m-%d')}
Relationship score: {relationship_score(contact)}
"""
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt_text,
            generation_config={
                "temperature": 0.7,
                "max_output_tokens": 200
            }
        )
        return response.text.strip()
    except Exception as e:
        return f"⚠️ AI generation failed: {str(e)}\n\nFallback message:\nHi {contact.name}, just checking in!"

# -------------------------------
# Routes
# -------------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/contacts", response_class=HTMLResponse)
async def contact_list(
    request: Request,
    months: str = "all",
    search: str = "",
    db: Session = Depends(get_db),
):
    contacts = filter_contacts(db, months)
    if search:
        search_lower = search.lower()
        contacts = [
            c for c in contacts
            if search_lower in c.name.lower() or (c.company and search_lower in c.company.lower())
        ]
    for c in contacts:
        c.relationship = relationship_score(c)
    contacts.sort(key=lambda c: (c.relationship, c.frequency), reverse=True)
    grouped = group_by_company(contacts)
    return templates.TemplateResponse(
        "contact_list.html",
        {"request": request, "contacts_by_company": grouped, "months": months, "search": search},
    )

@app.get("/contacts/add", response_class=HTMLResponse)
async def add_contact_form(request: Request):
    return templates.TemplateResponse(
        "add_contact.html",
        {"request": request, "today": datetime.now().strftime("%Y-%m-%d")},
    )

@app.post("/contacts/add", response_class=HTMLResponse)
async def add_contact(
    request: Request,
    name: str = Form(...),
    company: str = Form("Independent / Unknown"),
    email: str = Form(""),
    phone: str = Form(""),
    notes: str = Form(""),
    frequency: int = Form(0),
    last_contact: str = Form(datetime.now().strftime("%Y-%m-%d")),
    db: Session = Depends(get_db),
):
    last_contact_dt = datetime.strptime(last_contact, "%Y-%m-%d")
    new_contact = Contact(
        name=name,
        company=company,
        email=email,
        phone=phone,
        notes=notes,
        frequency=frequency,
        last_contact=last_contact_dt,
    )
    db.add(new_contact)
    db.commit()
    db.refresh(new_contact)
    return RedirectResponse("/contacts", status_code=303)

@app.get("/contacts/{contact_id}", response_class=HTMLResponse)
async def contact_detail(
    request: Request, contact_id: int, db: Session = Depends(get_db)
):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        return HTMLResponse("Contact not found", status_code=404)
    contact.relationship = relationship_score(contact)
    suggestion = (
        "💡 Maintain contact regularly — relationship fading."
        if contact.relationship < 0.5
        else "✅ Strong relationship — keep up the engagement!"
    )
    return templates.TemplateResponse(
        "contact_detail.html",
        {"request": request, "contact": contact, "suggestion": suggestion},
    )

# -------------------------------
# AI Email Draft Route
# -------------------------------
@app.post("/contacts/{contact_id}/draft_email", response_class=JSONResponse)
async def draft_email(contact_id: int, email: str = Form(None), db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        return JSONResponse({"error": "Contact not found"}, status_code=404)

    # Ensure email exists
    if not email and not contact.email:
        return JSONResponse({"error": "No email provided. Please enter an email first."}, status_code=400)

    draft_email_text = generate_email_ai(contact)
    return {"draft_email": draft_email_text}
