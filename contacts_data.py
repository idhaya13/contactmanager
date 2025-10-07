from datetime import datetime, timedelta

contacts = [
    {
        "id": 1,
        "name": "Ravi Kumar",
        "company": "TechNova",
        "email": "ravi@technova.com",
        "phone": "9876543210",
        "last_contact": datetime.now() - timedelta(days=5),
        "frequency": 12,  # times contacted
        "notes": "Talked about SaaS partnership.",
    },
    {
        "id": 2,
        "name": "Priya Sharma",
        "company": "TechNova",
        "email": "priya@technova.com",
        "phone": "9988776655",
        "last_contact": datetime.now() - timedelta(days=70),
        "frequency": 8,
        "notes": "Potential investor meeting.",
    },
    {
        "id": 3,
        "name": "John Mathew",
        "company": "FinEdge",
        "email": "john@finedge.com",
        "phone": "9123456789",
        "last_contact": datetime.now() - timedelta(days=180),
        "frequency": 3,
        "notes": "Discussed fintech collaboration.",
    },
    {
        "id": 4,
        "name": "Ananya Iyer",
        "company": "FinEdge",
        "email": "ananya@finedge.com",
        "phone": "9000011122",
        "last_contact": datetime.now() - timedelta(days=20),
        "frequency": 10,
        "notes": "Follow-up on deal proposal.",
    },
]
