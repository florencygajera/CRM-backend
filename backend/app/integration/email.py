import smtplib
from email.mime.text import MIMEText

def send_email_smtp(*, host: str, port: int, username: str, password: str, to_email: str, subject: str, body: str):
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = subject
    msg["From"] = username
    msg["To"] = to_email

    server = smtplib.SMTP(host, port)
    server.starttls()
    server.login(username, password)
    server.sendmail(username, [to_email], msg.as_string())
    server.quit()
