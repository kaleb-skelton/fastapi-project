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

# ✅ Securely load SendGrid API Key from environment variables
SENDGRID_API_KEY = os.getenv("SENDGRID_API_KEY")  # ✅ Fixed issue

# ✅ Email Templates (Replace with actual SendGrid template IDs)
TEMPLATES = {
    "Intro": "d-00db22748548459f8a86e14049fbf25f",
    "Follow-Up FPCO": "d-1317f11c765f4c5dbaeebfac1b921799",
    "Follow-Up Pest Plan": "d-24b92f6d0a1b4af49bed2188ba82d93e"
}

CSV_FILE = "email_list_fixed.csv"  # ✅ Ensure this CSV file exists


@app.get("/download_csv")
async def download_csv():
    return FileResponse("email_list_fixed.csv", media_type="text/csv", filename="email_list_fixed.csv")
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


# ✅ Send Emails with SendGrid
@app.post("/send_email")
async def send_email(request: Request):
    if "user" not in request.session:
        return JSONResponse({"error": "Unauthorized"}, status_code=401)

    data = await request.json()
    email_type = data.get("email_type")
    max_emails = int(data.get("max_emails", 5))

    df = pd.read_csv("email_list_fixed.csv")
    rows = df[df["Sent"] != "Sent"] if email_type == "Intro" else df[
        df["F/U Sent"] != "Follow-Up Sent"]

    emails_sent = 0
    failure_count = 0
    max_failures = 3  # Stop after 3 failures

    sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)

    for index, row in rows.iterrows():
        if emails_sent >= max_emails or failure_count >= max_failures:
            break  # ✅ Stop sending if too many failures

        recipient_email = row["Email Address"].strip()  # ✅ Remove extra spaces
        subject_line = f"{row['Customer Name']} - {row['Office Name']}"

        # ✅ Ensure email type exists in templates
        template_id = TEMPLATES.get(email_type)
        if not template_id:
            print(f"🚨 Invalid email type: {email_type}")
            continue  # Skip if template is invalid

        message = Mail(
            from_email="kskelton@ecoteam.com",
            to_emails=recipient_email  # ✅ Only add recipient here
        )

        # ✅ Now add CC separately:
        message.add_cc("kskelton@ecoteam.com")

        # ✅ Set Template ID
        message.template_id = template_id

        # ✅ Pass dynamic data (subject)
        message.dynamic_template_data = {"subject": subject_line}

        try:
            response = sg.send(message)  # ✅ Attempt to send email
            print(f"✅ Email sent to {recipient_email}: {response.status_code}"
                  )  # ✅ Debugging log
            df.at[index, "Sent"] = "Sent"
            emails_sent += 1
        except Exception as e:
            print(f"❌ Email failed to {recipient_email}: {str(e)}"
                  )  # ✅ Log failure
            if hasattr(e, 'body'):
                print("📌 Full Error Response:",
                      e.body)  # ✅ Show full SendGrid response
            failure_count += 1  # Count failures
            if failure_count >= max_failures:
                print("🚨 Too many failures! Stopping email sending.")
                break  # ✅ Stop sending if max failures reached

    df.to_csv("email_list_fixed.csv", index=False)
    return JSONResponse({"message": f"✅ {emails_sent} emails sent!"})
