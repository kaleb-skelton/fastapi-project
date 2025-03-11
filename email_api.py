import os
import shutil
import base64
import pandas as pd
import sendgrid
from sendgrid.helpers.mail import Mail, Attachment, FileContent, FileName, FileType, Disposition
from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()

# ✅ Session Middleware (For Login Authentication)
app.add_middleware(SessionMiddleware,
                   secret_key="supersecretkey",
                   session_cookie="email_app_session",
                   same_site="none",
                   max_age=86400,
                   https_only=False)

# ✅ Serve Static Files
app.mount("/static", StaticFiles(directory="static"), name="static")

# ✅ User Credentials (Replace with Database Later)
USERS = {"admin": "password123"}

# ✅ Securely Load SendGrid API Key
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")

# ✅ Branch-Specific Email List
CSV_FILE = "email_list_fixed.csv"


@app.get("/")
async def home(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return FileResponse("static/index.html")


@app.get("/login")
def login_page():
    return FileResponse("static/login.html")


@app.post("/login")
async def login(request: Request,
                username: str = Form(...),
                password: str = Form(...)):
    if username in USERS and USERS[username] == password:
        request.session["user"] = username
        return RedirectResponse(url="/dashboard", status_code=303)
    return JSONResponse({"error": "Invalid credentials"}, status_code=401)


@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/login")


@app.get("/dashboard")
async def dashboard(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return FileResponse("static/dashboard.html")


@app.get("/send_flyer")
async def send_flyer_page(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse(url="/login", status_code=302)
    return FileResponse("static/flyers.html")


@app.post("/send_flyer")
async def send_flyer(
    flyer: UploadFile = File(...),
    branch: str = Form(...),
    subject: str = Form(...),
    body: str = Form(...)
):
    try:
        # ✅ Save the Uploaded PDF
        flyer_path = f"static/uploads/{flyer.filename}"
        with open(flyer_path, "wb") as buffer:
            shutil.copyfileobj(flyer.file, buffer)

        # ✅ Load CSV and Filter by Branch
        df = pd.read_csv(CSV_FILE, encoding="latin1")
        if branch != "all":
            df = df[df["Office Name"].str.strip().str.lower() == branch.lower()]

        if df.empty:
            return JSONResponse({"error": f"No properties found for branch: {branch}"}, status_code=400)

        # ✅ Initialize SendGrid
        sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
        emails_sent = 0

        for _, row in df.iterrows():
            recipient_email = row["Email Address"].strip()
            personalized_body = body.replace("[Customer Name]", row["Customer Name"])  # ✅ Replace placeholder

            message = Mail(
                from_email="kskelton@ecoteam.com",
                to_emails=recipient_email,
                subject=subject,
                html_content=f"""
                <html>
                <body>
                    <p>{personalized_body}</p>
                </body>
                </html>
                """
            )

            # ✅ Attach the PDF Flyer
            with open(flyer_path, "rb") as f:
                flyer_data = f.read()
                encoded_file = base64.b64encode(flyer_data).decode()
                attachment = Attachment(
                    FileContent(encoded_file),
                    FileName(flyer.filename),
                    FileType("application/pdf"),
                    Disposition("attachment")
                )
                message.add_attachment(attachment)

            try:
                sg.send(message)
                emails_sent += 1
            except Exception as e:
                print(f"❌ Email failed to {recipient_email}: {str(e)}")

        return JSONResponse({"message": f"✅ {emails_sent} flyer emails sent!"})

    except Exception as e:
        return JSONResponse({"error": str(e)}, status_code=500)
