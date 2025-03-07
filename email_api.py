from fastapi import FastAPI, Request, Form
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
import pandas as pd
import sendgrid
from sendgrid.helpers.mail import Mail
import os
import uvicorn

app = FastAPI()

@app.get("/")
def home():
    return {"message": "🚀 FastAPI is live on Railway!"}

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))  # Default to 8000 if no PORT is set
    uvicorn.run(app, host="0.0.0.0", port=port)

# ✅ Session Middleware for Authentication
app.add_middleware(SessionMiddleware,
                   secret_key="your_secret_key",
                   session_cookie="email_app_session")

# ✅ Serve static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# ✅ User Credentials (Replace with a database later)
USERS = {"admin": "password123"}

SENDGRID_API_KEY = "your_sendgrid_api_key"
CSV_FILE = "email_list_fixed.csv"

TEMPLATES = {
    "Intro": "d-00db22748548459f8a86e14049fbf25f",
    "Follow-Up FPCO": "d-1317f11c765f4c5dbaeebfac1b921799",
    "Follow-Up Pest Plan": "d-24b92f6d0a1b4af49bed2188ba82d93e"
}


# ✅ **Login Page**
@app.get("/login")
def login_page():
    return FileResponse("static/login.html")


# ✅ **Login Handler**
@app.post("/login")
async def login(request: Request,
                username: str = Form(...),
                password: str = Form(...)):
    if username in USERS and USERS[username] == password:
        request.session["user"] = username  # ✅ Store user in session
        return RedirectResponse(url="/", status_code=303)
    return JSONResponse({"error": "Invalid credentials"}, status_code=401)


# ✅ **Logout Route**
@app.get("/logout")
def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/login")


# ✅ **Protected Email Sender Page**
@app.get("/")
def home(request: Request):
    if "user" not in request.session:
        return RedirectResponse(url="/login")

    return FileResponse("static/index.html")


# ✅ **Send Emails Route**
@app.post("/send_email")
async def send_email(request: Request):
    if "user" not in request.session:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    data = await request.json()
    email_type = data.get("email_type")
    max_emails = int(data.get("max_emails", 5))

    df = pd.read_csv(CSV_FILE)
    rows = df[df["Sent"] != "Sent"] if email_type == "Intro" else df[
        df["F/U Sent"] != "Follow-Up Sent"]
    emails_sent = 0
    sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)

    for index, row in rows.iterrows():
        if emails_sent >= max_emails:
            break

        recipient_email = row["Email Address"]
        subject_line = f"{row['Customer Name']} - {row['Office Name']}"

        template_id = TEMPLATES[
            "Intro"] if email_type == "Intro" else TEMPLATES["Follow-Up FPCO"]

        message = Mail(from_email="kskelton@ecoteam.com",
                       to_emails=recipient_email)
        message.template_id = template_id
        message.dynamic_template_data = {"subject": subject_line}

        sg.send(message)
        df.at[index, "Sent" if email_type == "Intro" else "F/U Sent"] = "Sent"
        emails_sent += 1

    df.to_csv(CSV_FILE, index=False)
    return JSONResponse(
        {"message": f"✅ {emails_sent} {email_type} emails sent!"})
