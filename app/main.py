from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

# 1️⃣ Create app FIRST
app = FastAPI()

# 2️⃣ Import router from CORRECT location
from app.automation.automation import router as automation_router

# 3️⃣ Include router
app.include_router(automation_router)

# 4️⃣ Templates
templates = Jinja2Templates(directory="app/templates")

# 5️⃣ Static files
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# ---------------- ROUTES ----------------

@app.get("/")
def root():
    return {
        "message": "Automation Platform is Running",
        "dashboard": "/dashboard",
        "history": "/history",
        "docs": "/docs"
    }

@app.get("/dashboard")
def dashboard(request: Request):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request}
    )

@app.get("/history")
def history(request: Request):
    return templates.TemplateResponse(
        "history.html",
        {"request": request}
    )
