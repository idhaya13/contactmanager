from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
from database import SessionLocal
from models import Contact
from collections import defaultdict
from google import genai
from google.genai import types
import os
from dotenv import load_dotenv

app = FastAPI(title="Business AI Contact Manager")
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# -------------------------------
# Gemini API setup
# -------------------------------
load_dotenv()
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
if not GOOGLE_API_KEY:
    raise ValueError("❌ GOOGLE_API_KEY environment variable not set.")

client = genai.Client(api_key=GOOGLE_API_KEY)

# -------------------------------
# DB session dependency
# -------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# -------------------------------
# Helpers
# -------------------------------
def relationship_score(contact: Contact) -> float:
    days_since_contact = (datetime.now() - contact.last_contact).days
    recency_score = max(0, 1 - days_since_contact / 180)
    freq_score = min(contact.frequency / 12, 1)
    return round((0.6 * recency_score + 0.4 * freq_score), 2)

def filter_contacts(db: Session, months=None):
    query = db.query(Contact)
    if months and months != "all":
        cutoff = datetime.now() - timedelta(days=30 * int(months))
        query = query.filter(Contact.last_contact >= cutoff)
    return query.all()

def group_by_company(contact_list):
    from collections import defaultdict
    groups = defaultdict(list)
    for c in contact_list:
        company = c.company or "Independent / Unknown"
        groups[company].append(c)
    return groups

def generate_email_ai(contact: Contact) -> str:
    prompt_text = f"""
Write a concise, professional, friendly follow-up email to {contact.name}.
Company: {contact.company}
Notes: {contact.notes if contact.notes else "No specific notes available."}
Last contact: {contact.last_contact.strftime('%Y-%m-%d')}
Relationship score: {relationship_score(contact)}
"""

    try:
        gen_config = types.GenerateContentConfig(
            temperature=0.7,
            top_p=0.95,
            top_k=40,
            candidate_count=1,
            max_output_tokens=200,
        )
        response = client.models.generate_content(
            model="gemini-2.0-flash-001",
            contents=prompt_text,
            config=gen_config,
        )
        if getattr(response, "text", None):
            return response.text.strip()
        candidates = getattr(response, "candidates", None)
        if candidates:
            cand = candidates[0]
            text = cand.content.parts[0].text
            return text.strip()
        return "⚠️ AI returned no text output."
    except Exception as e:
        return f"⚠️ AI generation failed: {str(e)}"

# -------------------------------
# Routes
# -------------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/contacts", response_class=HTMLResponse)
async def contact_list(request: Request, months: str = "all", search: str = "", db: Session = Depends(get_db)):
    contacts = filter_contacts(db, months)
    if search:
        search_lower = search.lower()
        contacts = [c for c in contacts if search_lower in c.name.lower() or (c.company and search_lower in c.company.lower())]
    for c in contacts:
        c.relationship = relationship_score(c)
    contacts.sort(key=lambda c: (c.relationship, c.frequency), reverse=True)
    grouped = group_by_company(contacts)
    return templates.TemplateResponse("contact_list.html", {"request": request, "contacts_by_company": grouped, "months": months, "search": search})

@app.get("/contacts/{contact_id}", response_class=HTMLResponse)
async def contact_detail(request: Request, contact_id: int, db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        return HTMLResponse("Contact not found", status_code=404)
    contact.relationship = relationship_score(contact)
    suggestion = "💡 Maintain contact regularly — relationship fading." if contact.relationship < 0.5 else "✅ Strong relationship — keep up the engagement!"
    return templates.TemplateResponse("contact_detail.html", {"request": request, "contact": contact, "suggestion": suggestion})

@app.post("/contacts/{contact_id}/draft_email", response_class=JSONResponse)
async def draft_email(contact_id: int, email: str = Form(None), db: Session = Depends(get_db)):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        return JSONResponse({"error": "Contact not found"}, status_code=404)

    if email:
        contact.email = email
        db.commit()

    if not contact.email:
        return JSONResponse({"error": "No email provided. Please enter an email first."}, status_code=400)

    draft_email_text = generate_email_ai(contact)
    return {"draft_email": draft_email_text}

@app.post("/contacts/{contact_id}/edit", response_class=JSONResponse)
async def edit_contact(
    contact_id: int,
    company: str = Form(None),
    email: str = Form(None),
    phone: str = Form(None),
    notes: str = Form(None),
    frequency: int = Form(None),
    last_contact: str = Form(None),
    db: Session = Depends(get_db)
):
    contact = db.query(Contact).filter(Contact.id == contact_id).first()
    if not contact:
        return JSONResponse({"error": "Contact not found"}, status_code=404)
    if company is not None: contact.company = company
    if email is not None: contact.email = email
    if phone is not None: contact.phone = phone
    if notes is not None: contact.notes = notes
    if frequency is not None: contact.frequency = int(frequency)
    if last_contact is not None: contact.last_contact = datetime.strptime(last_contact, "%Y-%m-%d")
    db.commit()
    db.refresh(contact)
    return JSONResponse({"success": True})
