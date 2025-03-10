import os
import pandas as pd
import sendgrid
from sendgrid.helpers.mail import Mail, Email, To, Cc
from fastapi import FastAPI, Request, Form
from fastapi.responses import FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

app = FastAPI()

# ✅ Add session middleware for authentication
app.add_middleware(SessionMiddleware, secret_key="supersecretkey")

# ✅ Serve static files (HTML, CSS, Images)
app.mount("/static", StaticFiles(directory="static"), name="static")

# ✅ Dummy user credentials (Replace with database later)
USERS = {"admin": "password123"}

# ✅ SendGrid API Key (Replace with environment variable for security)
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")
# ✅ Email Templates (Replace with actual SendGrid template IDs)
TEMPLATES = {
    "Intro": "d-00db22748548459f8a86e14049fbf25f",
    "Follow-Up FPCO": "d-1317f11c765f4c5dbaeebfac1b921799",
    "Follow-Up Pest Plan": "d-24b92f6d0a1b4af49bed2188ba82d93e"
}

CSV_FILE = "email_list_fixed.csv"  # ✅ Ensure this CSV file exists


# ✅ Serve the Login Page
@app.get("/login")
def login_page():
    return FileResponse("static/login.html")


# ✅ Handle Login Submission
@app.post("/login")
async def login(request: Request,
                username: str = Form(...),
                password: str = Form(...)):
    if username in USERS and USERS[username] == password:
        request.session["user"] = username  # ✅ Store user in session
        return RedirectResponse("/",
                                status_code=303)  # ✅ Redirect to email sender

    return JSONResponse({"error": "Invalid credentials"},
                        status_code=401)  # ✅ Show login error


# ✅ Logout Route
@app.get("/logout")
async def logout(request: Request):
    request.session.clear()  # ✅ Remove user session
    return RedirectResponse("/login")  # ✅ Redirect user back to login page


# ✅ Protect the Email Sender Page (Only for Logged-in Users)
@app.get("/")
async def home(request: Request):
    if "user" not in request.session:
        return RedirectResponse(
            "/login")  # ✅ Redirect unauthorized users to login

    return FileResponse("static/index.html")  # ✅ Serve email sender page


# ✅ Email Sending Route (Requires Login)
@app.post("/send_email")
async def send_email(request: Request):
    if "user" not in request.session:
        return JSONResponse({"error": "Unauthorized"},
                            status_code=401)  # ✅ Block unauthorized users

    data = await request.json()
    email_type = data.get("email_type")
    max_emails = int(data.get("max_emails", 5))

    df = pd.read_csv(CSV_FILE)

    # ✅ Filter emails that haven’t been sent
    rows = df[df["Sent"] != "Sent"] if email_type == "Intro" else df[
        df["F/U Sent"] != "Follow-Up Sent"]
    emails_sent = 0
    sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)

    for index, row in rows.iterrows():
        if emails_sent >= max_emails:
            break

        recipient_email = row["Email Address"]
        subject_line = f"{row['Customer Name']} - {row['Office Name']}"

        # ✅ Choose the correct email template
        if email_type == "Follow-Up":
            offer_type = row["OFFER RECC"]
            if offer_type == "Offer FPCO":
                template_id = TEMPLATES["Follow-Up FPCO"]
            elif offer_type == "Offer AIR Upgrade":
                template_id = TEMPLATES["Follow-Up Pest Plan"]
            else:
                continue
        else:
            template_id = TEMPLATES["Intro"]

        # ✅ Construct Email with CC to `kskelton@ecoteam.com`
        message = Mail(
            from_email="your-email@domain.com",  # ✅ Replace with your email
            to_emails=To(recipient_email))
        message.add_cc(Cc("kskelton@ecoteam.com"))  # ✅ CC you on all emails
        message.template_id = template_id
        message.dynamic_template_data = {"subject": subject_line}

        try:
            sg.send(message)  # ✅ Send the email
            df.at[index,
                  "Sent" if email_type == "Intro" else "F/U Sent"] = "Sent"
            emails_sent += 1
        except Exception as e:
            print(f"❌ Email failed to {recipient_email}: {str(e)}")

    df.to_csv(CSV_FILE, index=False)  # ✅ Save updated CSV
    return JSONResponse(
        {"message": f"✅ {emails_sent} {email_type} emails sent!"})
