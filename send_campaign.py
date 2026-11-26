import csv
import os
import random
import smtplib
import sys
import time
from datetime import timedelta
from html import escape

from send_mail import send_mail

DELAY_SECONDS = (30, 90)    # random wait between sends; steady bursts look like spam
MAX_PER_RUN = 50            # run once a day; a sudden 180 cold emails from one Gmail gets it flagged
DO_NOT_EMAIL = "do_not_email.txt"  # people already in touch: one address, or @domain.com for a whole company
SEED_EMAIL = "muhammadbilalarifshaikh@gmail.com"  # gets the first copy of every run, to check it lands in the inbox and not spam

# One link instead of many: several links in a first-contact email is a strong spam signal
PHOTOS_FOLDER = "https://drive.google.com/drive/folders/138VMDPtf3zQSWpfVLiZAcgMmDxIybJdS?usp=drive_link"
GARMENT_PHOTOS_FOLDER = "https://drive.google.com/drive/folders/1v-Yy_tIMcq9MgUIx2qASgugMX3C-qZib?usp=drive_link"

INSTAGRAM = "https://www.instagram.com/mehran_prints/"
YOUTUBE = "https://youtube.com/shorts/RBobW7pMQig?feature=share"
FACTORY_ADDRESS = "1D3, ST9, Sector 16B, Federal B Area, Block 22, North Karachi Industrial Area, Karachi, Pakistan."

SIGNATURE = f"""Best Regards,
Bilal Shaikh
Director | Mehran Prints
All Kinds of Fabric Printing

Contact / WhatsApp: +92 312 2211828
Email: prints.mehran@gmail.com
Instagram: {INSTAGRAM}
YouTube – Machine Printing Video: {YOUTUBE}
Factory Address: {FACTORY_ADDRESS}
"""

SIGNATURE_HTML = f"""<p><b>Best Regards,<br>
Bilal Shaikh<br>
Director | Mehran Prints</b><br>
<i>All Kinds of Fabric Printing</i></p>
<p><b>Contact / WhatsApp:</b> <a href="https://wa.me/923122211828">+92 312 2211828</a><br>
<b>Email:</b> <a href="mailto:prints.mehran@gmail.com">prints.mehran@gmail.com</a><br>
<b>Instagram:</b> <a href="{INSTAGRAM}">{INSTAGRAM}</a><br>
<b>YouTube – Machine Printing Video:</b> <a href="{YOUTUBE}">{YOUTUBE}</a><br>
<b>Factory Address:</b> {FACTORY_ADDRESS}</p>"""


def html_email(*paragraphs):
    body = "\n".join(f"<p>{p}</p>" for p in paragraphs)
    return f"""<div style="font-family:Arial,Helvetica,sans-serif;font-size:14px;color:#222;line-height:1.5">
{body}
{SIGNATURE_HTML}
</div>
"""


# Each campaign keeps its own address list and sent log, so re-running one never mails the other's list
CAMPAIGNS = {
    "towel": {
        "emails_file": "towel_emails.txt",
        "sent_file": "towels_sent.txt",
        "subject": "Towel Screen Printing Services | Up to 60-Inch Prints | 20,000+ Pcs Daily Capacity",
        "body": f"""Dear Sir/Madam,

Greetings from Mehran Prints!

We would like to introduce ourselves as an established textile screen printing facility with over 20 years of experience in the industry. We are already serving some of Pakistan's leading towel exporters, providing reliable and high-quality printing services.

Our facility is equipped with screen printing machines and has a production capacity of 20,000+ pieces per day, enabling us to handle bulk orders while maintaining consistent quality and timely delivery.

We specialize in large-format screen printing, with the capability to print designs up to 60 inches on our machine screen printing setup. This makes us well-suited for towels and other textile products requiring large, detailed, and high-quality prints.

We would greatly appreciate the opportunity to work with your company. If you have any towel printing samples, designs, or upcoming developments, we would be happy to develop samples for your review and demonstrate our printing capabilities.

We have also shared some close-up pictures from our current production for your reference, so you can get a better idea of our print quality and finishing:

{PHOTOS_FOLDER}

We look forward to the opportunity to work with you and establish a long-term business relationship.

{SIGNATURE}""",
        "html": html_email(
            "Dear Sir/Madam,",
            "Greetings from <b>Mehran Prints!</b>",
            "We would like to introduce ourselves as an established textile screen printing facility with over <b>20 years of experience</b> in the industry. We are already serving some of Pakistan's leading towel exporters, providing reliable and high-quality printing services.",
            "Our facility is equipped with screen printing machines and has a production capacity of <b>20,000+ pieces per day</b>, enabling us to handle bulk orders while maintaining consistent quality and timely delivery.",
            "We <b>specialize in large-format screen printing, with the capability to print designs up to 60 inches</b> on our machine screen printing setup. This makes us well-suited for towels and other textile products requiring large, detailed, and high-quality prints.",
            "We would greatly appreciate the opportunity to work with your company. If you have any <b>towel printing samples, designs, or upcoming developments</b>, we would be happy to develop samples for your review and demonstrate our printing capabilities.",
            f'We have also shared some <b>close-up pictures from our current production</b> for your reference, so you can get a better idea of our print quality and finishing: <a href="{PHOTOS_FOLDER}">View production photos</a>',
            "We look forward to the opportunity to work with you and establish a long-term business relationship.",
        ),
    },
    "garments": {
        "emails_file": "emails.txt",
        "sent_file": "sent.txt",
        "openers_file": "garments_openers.csv",  # Gemini-written first paragraphs (leads/personalise_garments.py)
        "subject": "Expert Textile Automatic Screen Printing Services | Up to 60-Inch Prints | 20,000+ Pcs Daily Capacity",
        "body": f"""Dear Sir/Madam,

Greetings from Mehran Prints!

We would like to introduce ourselves as an established textile screen printing facility in Karachi with over 20 years of experience in the industry. We are already serving some of Pakistan's leading textile exporters, providing reliable and high-quality printing services.

Our facility is equipped with screen printing machines, heat transfer machines and table printing setups for all your textile printing needs, with a production capacity of 20,000+ pieces per day, enabling us to handle bulk export orders while maintaining consistent quality and timely delivery.

We specialize in all kinds of prints, including Foil, High Density, Puff, Glitter, Silicone, Crack, Flock and other special effect prints.

We print on garment panels, cut pieces and fabric for apparel such as t-shirts, sweatshirts, hoodies, kidswear and sportswear, as well as home textile products. With the capability to print designs up to 60 inches on our machine screen printing setup, we can handle everything from small chest prints to large, detailed artwork.

We would greatly appreciate the opportunity to work with your company. If you have any garment printing requirements, artworks, or upcoming developments, we would be happy to develop samples for your review and demonstrate our printing capabilities.

We have also shared some close-up pictures from our current production for your reference, so you can get a better idea of our print quality and finishing:

{GARMENT_PHOTOS_FOLDER}

We look forward to the opportunity to work with you and establish a long-term business relationship.

{SIGNATURE}""",
        "html": html_email(
            "Dear Sir/Madam,",
            "Greetings from <b>Mehran Prints!</b>",
            "We would like to introduce ourselves as an established textile screen printing facility in Karachi with over <b>20 years of experience</b> in the industry. We are already serving some of Pakistan's leading textile exporters, providing reliable and high-quality printing services.",
            "Our facility is equipped with <b>screen printing machines, heat transfer machines and table printing setups</b> for all your textile printing needs, with a production capacity of <b>20,000+ pieces per day</b>, enabling us to handle bulk export orders while maintaining consistent quality and timely delivery.",
            "We specialize in <b>all kinds of prints, including Foil, High Density, Puff, Glitter, Silicone, Crack, Flock and other special effect prints</b>.",
            "We print on <b>garment panels, cut pieces and fabric</b> for apparel such as <b>t-shirts, sweatshirts, hoodies, kidswear and sportswear</b>, as well as <b>home textile products</b>. With the capability to <b>print designs up to 60 inches</b> on our machine screen printing setup, we can handle everything from small chest prints to large, detailed artwork.",
            "We would greatly appreciate the opportunity to work with your company. If you have any <b>garment printing requirements, artworks, or upcoming developments</b>, we would be happy to develop samples for your review and demonstrate our printing capabilities.",
            f'We have also shared some <b>close-up pictures from our current production</b> for your reference, so you can get a better idea of our print quality and finishing: <a href="{GARMENT_PHOTOS_FOLDER}">View production photos</a>',
            "We look forward to the opportunity to work with you and establish a long-term business relationship.",
        ),
    },
}


def load(path):
    try:
        with open(path) as f:
            return [line.strip().lower() for line in f if line.strip()]
    except FileNotFoundError:
        return []


def save(path, emails):
    # Write to a temp file then swap, so a crash mid-write can't wipe the list
    with open(path + ".tmp", "w") as f:
        f.writelines(e + "\n" for e in emails)
    os.replace(path + ".tmp", path)


def blocked(email, do_not_email):
    return email in do_not_email or any(d.startswith("@") and email.endswith(d) for d in do_not_email)


OPENER_AFTER = ("Greetings from Mehran Prints!\n\n", "<p>Greetings from <b>Mehran Prints!</b></p>\n")


def load_openers(path):
    # Only reviewed, usable openers; anything else (missing file, blank, any non-ok status) means the plain template
    try:
        with open(path, newline="") as f:
            return {r["email"].strip().lower(): r["opener"].strip() for r in csv.DictReader(f)
                    if r.get("status") == "ok" and (r.get("opener") or "").strip()}
    except FileNotFoundError:
        return {}


def personalise(c, opener):
    """The campaign's body and html with the opener as its own paragraph after the greeting, or unchanged."""
    text_mark, html_mark = OPENER_AFTER
    if not opener or text_mark not in c["body"] or html_mark not in c["html"]:
        return c["body"], c["html"]
    return (c["body"].replace(text_mark, f"{text_mark}{opener}\n\n", 1),
            c["html"].replace(html_mark, f"{html_mark}<p>{escape(opener)}</p>\n", 1))


def run(campaign, emails_file=None, sent_file=None, send=send_mail, delay=DELAY_SECONDS, max_per_run=MAX_PER_RUN,
        do_not_email_file=DO_NOT_EMAIL, seed=SEED_EMAIL, openers_file=None):
    c = CAMPAIGNS[campaign]
    emails_file = emails_file or c["emails_file"]
    sent_file = sent_file or c["sent_file"]
    openers_file = openers_file or c.get("openers_file")
    openers = load_openers(openers_file) if openers_file else {}
    sent = set(load(sent_file))
    do_not_email = {e for e in load(do_not_email_file) if not e.startswith("#")}
    remaining = list(dict.fromkeys(e for e in load(emails_file) if e not in sent and not blocked(e, do_not_email)))
    save(emails_file, remaining)  # drops already-sent, do-not-email and duplicate addresses
    pending = remaining[:max_per_run]
    print(f"[{campaign}] {len(sent)} already sent, {len(remaining)} left, sending {len(pending)} this run"
          + (f" | {sum(e in openers for e in pending)} PERSONALIZED, the rest on the template" if openers_file else ""))
    start, count = time.time(), 0

    # Sent first so the inbox can be checked while the run is still going; not logged, so it never counts as a send.
    # It shows a personalised version when this run has one, so the opener can be checked too.
    if seed and pending:
        sample = next((openers[e] for e in pending if e in openers), None)
        body, html = personalise(c, sample)
        try:
            send(seed, c["subject"], body, html=html)
            print(f"Check copy sent to {seed}: make sure it landed in the inbox, not spam")
        except smtplib.SMTPException as e:
            print(f"Check copy to {seed} failed ({e}); carrying on with the campaign")

    for i, email in enumerate(pending, 1):
        body, html = personalise(c, openers.get(email))
        try:
            send(email, c["subject"], body, html=html)
        except smtplib.SMTPRecipientsRefused:
            print(f"[{i}/{len(pending)}] bad address, skipped: {email}")
            continue
        # Written straight away, so a crash or Gmail's daily limit never causes a resend
        with open(sent_file, "a") as f:
            f.write(email + "\n")
        remaining.remove(email)
        save(emails_file, remaining)
        count += 1
        elapsed = timedelta(seconds=int(time.time() - start))
        style = " [PERSONALIZED]" if email in openers else " [template]" if openers_file else ""
        print(f"Email sent successfully to {email}{style} | total sent: {count}/{len(pending)} | total time: {elapsed}")
        if i < len(pending):
            wait = random.uniform(*delay)
            print(f"Waiting {wait:.0f} seconds before the next email...")
            time.sleep(wait)


if __name__ == "__main__":
    # No default campaign: sending the wrong pitch to a whole list can't be undone
    if len(sys.argv) != 2 or sys.argv[1] not in CAMPAIGNS:
        sys.exit(f"usage: python3 send_campaign.py <{'|'.join(CAMPAIGNS)}>")
    run(sys.argv[1])
