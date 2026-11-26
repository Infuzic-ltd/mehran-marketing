import os
import smtplib
from email.message import EmailMessage
from email.utils import formataddr, formatdate, make_msgid

GMAIL_USER = os.environ.get("GMAIL_USER", "prints.mehran@gmail.com")
GMAIL_APP_PASSWORD = os.environ.get("GMAIL_APP_PASSWORD", "fplv cknx yshk dpiz")  # 16-char Gmail App Password


def send_mail(to, subject, body, html=None):
    msg = EmailMessage()
    msg["From"] = formataddr(("Mehran Prints", GMAIL_USER))
    msg["To"] = to
    msg["Subject"] = subject
    # A bare address and missing Date/Message-ID are classic spam-filter signals
    msg["Date"] = formatdate(localtime=True)
    msg["Message-ID"] = make_msgid(domain="gmail.com")
    msg.set_content(body)
    if html:
        msg.add_alternative(html, subtype="html")  # plain text stays as fallback

    with smtplib.SMTP_SSL("smtp.gmail.com", 465) as smtp:
        smtp.login(GMAIL_USER, GMAIL_APP_PASSWORD)
        smtp.send_message(msg)


if __name__ == "__main__":
    send_mail("bilal.shaikh@oscar.pk", "Test", "Hello from Python")
