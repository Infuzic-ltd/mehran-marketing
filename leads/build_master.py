"""Rebuild the master database and both campaign lists from it.

usage: python3 -I leads/build_master.py

Reads:   the latest karachi_textile_garment_master_database_v*.xlsx ("Company Contacts" = your own research),
         leads/sources/*.csv (garments leads), towel_exporters.csv + leads/towel_sources/*.csv (towel leads),
         the send logs (sent.txt and towels_sent.txt for the current rounds, garments_sent_*.txt and
         towels_sent_*.txt for archived rounds) and do_not_email.txt.
Writes:  the "Master Contacts" sheet in that same workbook (one row per email, with send status),
         emails.txt (garments queue) and towel_emails.txt (towel queue).
"""
import csv
import glob
import json
import os
import re
import subprocess
import sys
import time
from concurrent.futures import ThreadPoolExecutor

from openpyxl import load_workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

proj = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EMAIL_IN_TEXT = re.compile(r"[a-z0-9._%+-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)*\.[a-z]{2,}", re.I)
EMAIL = re.compile(r"^[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}$")
# The associations', chambers' and fairs' own staff, not member companies
DROP_DOMAINS = {"prgmea.org", "phmaonline.com", "phma.com.pk", "phma.org.pk", "tdap.gov.pk", "kcci.com.pk", "pcfamea.com",
                "pksea.com", "pdmea.com", "messefrankfurt.com", "pakistanchamberusa.org", "towelassociation.com",
                "example.com", "domain.com", "email.com", "sentry.io", "wixpress.com",
                "hostbreak.com", "canvas.com"}  # a web host's and an unrelated site's address picked up from member sites
DROP_ADDRESSES = {"pcfamea@gmail.com", "pbedwear@gmail.com"}
# Job and system mailboxes don't reach anyone who buys printing
DROP_LOCAL = re.compile(r"^(noreply|no-reply|webmaster|postmaster|abuse|privacy|test|careers|jobs|hr|recruitment)$")
DOMAIN_CACHE = os.path.join(proj, "leads", ".domain_cache.json")
CACHE_DAYS = 7


def load(path):
    try:
        return [l.strip().lower() for l in open(path) if l.strip()]
    except FileNotFoundError:
        return []


def campaign_running():
    out = subprocess.run(["ps", "-eo", "args"], capture_output=True, text=True).stdout
    return any(re.search(r"send_campaign[.]py +(garments|towel)", l) for l in out.splitlines())


def latest_master():
    files = glob.glob(os.path.join(proj, "karachi_textile_garment_master_database_v*.xlsx"))
    if not files:
        sys.exit("no karachi_textile_garment_master_database_v*.xlsx found")
    return max(files, key=lambda p: int(re.search(r"_v(\d+)\.xlsx$", p).group(1)))


contacts = {}  # email -> merged record


def add(email, company="", phone="", place="", industry="", source="", url="", notes="", towel=False):
    email = email.strip().lower().strip(" .,;:()[]<>\"'")
    if not email:
        return
    r = contacts.setdefault(email, {"company": "", "phone": "", "place": "", "industry": "", "sources": [],
                                    "url": "", "notes": "", "towel": False})
    for k, v in (("company", company), ("phone", phone), ("place", place), ("industry", industry),
                 ("url", url), ("notes", notes)):
        if v and not r[k]:
            r[k] = str(v).strip()
    if source and source not in r["sources"]:
        r["sources"].append(source)
    r["towel"] |= towel


master = latest_master()
wb = load_workbook(master)

# 1. Your own research first, so its company names, phones and addresses win
for row in list(wb["Company Contacts"].iter_rows(values_only=True))[1:]:
    if not row or not row[1]:
        continue
    company, emails, phone, address, industry, source = (row + (None,) * 10)[:6]
    notes = row[9] if len(row) > 9 else ""
    is_towel = bool(re.search(r"towel|\bTMA\b", f"{industry} {source}", re.I))
    for e in EMAIL_IN_TEXT.findall(str(emails)):
        add(e, company, phone, address, industry, f"Research DB: {source}", "", notes, towel=is_towel)

# 2. Collected garments leads, then towel leads
for path in sorted(glob.glob(os.path.join(proj, "leads", "sources", "*.csv"))):
    for r in csv.DictReader(open(path, newline="", encoding="utf-8", errors="replace")):
        add(r.get("email") or "", r.get("company"), "", r.get("city"), "", os.path.basename(path), r.get("source_url"))
for path in [os.path.join(proj, "towel_exporters.csv")] + sorted(glob.glob(os.path.join(proj, "leads", "towel_sources", "*.csv"))):
    for r in csv.DictReader(open(path, newline="", encoding="utf-8", errors="replace")):
        add(r.get("email") or "", r.get("company"), "", r.get("city"), "Towels / home textiles", os.path.basename(path),
            r.get("source_url"), towel=True)

# 3. Send logs: each archived round (garments_sent_round1.txt, towels_sent_2026-10.txt) gets its own column;
#    sent.txt and towels_sent.txt are the current rounds
def rounds(prefix):
    return {os.path.basename(p)[len(prefix):-4]: set(load(p)) for p in sorted(glob.glob(os.path.join(proj, prefix + "*.txt")))}


garments_rounds, towel_rounds = rounds("garments_sent_"), rounds("towels_sent_")
garments_current = set(load(os.path.join(proj, "sent.txt")))
towel_current = set(load(os.path.join(proj, "towels_sent.txt")))
garments_any = garments_current.union(*garments_rounds.values())
towel_any = towel_current.union(*towel_rounds.values())
for e in garments_any | towel_any:  # people mailed earlier who aren't in any lead file still belong in the master
    add(e, source="send log")
do_not_email = {e for e in load(os.path.join(proj, "do_not_email.txt")) if not e.startswith("#")}


def blocked(e):
    return e in do_not_email or any(d.startswith("@") and e.endswith(d) for d in do_not_email)


def junk(e):
    local, _, dom = e.partition("@")
    return (not EMAIL.match(e) or e in DROP_ADDRESSES or DROP_LOCAL.match(local) or dom.startswith("www.")
            or dom in DROP_DOMAINS or any(dom.endswith("." + d) for d in DROP_DOMAINS))


# 4. Mail-server check; live domains are cached for a week, dead ones rechecked every build because lookups flicker
try:
    cache = json.load(open(DOMAIN_CACHE))
except (FileNotFoundError, ValueError):
    cache = {}


def mail_ok(dom):
    for _ in range(3):
        for rtype in ("MX", "A"):
            if subprocess.run(["dig", "+short", "+time=5", "+tries=3", dom, rtype], capture_output=True, text=True).stdout.strip():
                return True
    return False


now = time.time()
domains = sorted({e.split("@")[1] for e in contacts if not junk(e)})
to_check = [d for d in domains if not (d in cache and now - cache[d] < CACHE_DAYS * 86400)]
with ThreadPoolExecutor(4) as ex:
    for d, ok in zip(to_check, ex.map(mail_ok, to_check)):
        if ok:
            cache[d] = now
        else:
            cache.pop(d, None)
json.dump(cache, open(DOMAIN_CACHE, "w"))
live = {d for d in domains if d in cache}

# 5. Status and next campaign for every email
rows = []
for e, r in contacts.items():
    dom = e.split("@")[1]
    if junk(e):
        nxt = "Excluded: not a usable address"
    elif blocked(e):
        nxt = "Excluded: do not email"
    elif dom not in live:
        nxt = "Excluded: domain has no mail server"
    elif r["towel"]:
        nxt = "Towel round done" if e in towel_current else "Towel queue"
    elif e in garments_current:
        nxt = "Garments round done"
    elif e in towel_any and e not in garments_any:
        nxt = "Held: got the towel email"  # never had the garments pitch; keeps the two pitches apart
    else:
        nxt = "Garments queue"
    rows.append([r["company"], e, r["phone"], r["place"], r["industry"] or ("Towels / home textiles" if r["towel"] else ""),
                 "Towel" if r["towel"] else "Garments & textiles",
                 *["Yes" if e in s else "" for s in garments_rounds.values()],
                 "Yes" if e in garments_current else "",
                 *["Yes" if e in s else "" for s in towel_rounds.values()],
                 "Yes" if e in towel_current else "",
                 "Yes" if blocked(e) else "", nxt, "; ".join(r["sources"]), r["url"], r["notes"]])
rows.sort(key=lambda x: (x[0].lower() or "~", x[1]))

header = (["Company", "Email", "Phone", "Address / City", "Industry / Product Focus", "Segment"]
          + [f"Garments Email {k}" for k in garments_rounds] + ["Garments Email Current Round"]
          + [f"Towel Email {k}" for k in towel_rounds] + ["Towel Email Current Round", "Do Not Email", "Next Campaign",
             "Sources", "Source URL", "Research Notes"])

# 6. Write the sheet: light grey header with black text, white rows, thin light borders, Montserrat
if "Master Contacts" in wb.sheetnames:
    del wb["Master Contacts"]
ws = wb.create_sheet("Master Contacts", 0)
wb.active = 0
ws.append(header)
for row in rows:
    ws.append(row)
font, side = "Montserrat", Side(style="thin", color="D9D9D9")
for c in ws[1]:
    c.font = Font(name=font, size=10, color="000000")
    c.fill = PatternFill("solid", fgColor="E7E6E6")
    c.border = Border(bottom=side)
    c.alignment = Alignment(vertical="center", wrap_text=True)
for row in ws.iter_rows(min_row=2):
    for c in row:
        c.font = Font(name=font, size=10, color="000000")
        c.border = Border(bottom=side)
widths = {"Company": 34, "Email": 34, "Phone": 18, "Address / City": 30, "Industry / Product Focus": 26, "Segment": 16,
          "Next Campaign": 28, "Sources": 36, "Source URL": 36, "Research Notes": 36}
for i, h in enumerate(header, 1):
    ws.column_dimensions[ws.cell(1, i).column_letter].width = widths.get(h, 14)
ws.freeze_panes = "C2"
ws.auto_filter.ref = ws.dimensions

readme = wb["Read Me"]
if not any(r[0].value == "Master Contacts" for r in readme.iter_rows()):
    readme.append(["Master Contacts", "One row per email, merged from Company Contacts, all collected lead files and the "
                   "send logs, with send status and Next Campaign. Rebuilt by leads/build_master.py; edit Company Contacts, "
                   "the lead files or do_not_email.txt, not this sheet."])

tmp = master + ".tmp.xlsx"
wb.save(tmp)
os.replace(tmp, master)

# 7. Campaign queues, unless a campaign is sending right now (it rewrites its own list after every send)
NEXT = header.index("Next Campaign")
queues = {"emails.txt": [r[1] for r in rows if r[NEXT] == "Garments queue"],
          "towel_emails.txt": [r[1] for r in rows if r[NEXT] == "Towel queue"]}
if campaign_running():
    print("campaign running: master updated, queue files left alone until it finishes")
else:
    for name, emails in queues.items():
        path = os.path.join(proj, name)
        with open(path + ".tmp", "w") as f:
            f.writelines(e + "\n" for e in emails)
        os.replace(path + ".tmp", path)

counts = {}
for r in rows:
    counts[r[NEXT]] = counts.get(r[NEXT], 0) + 1
print(f"{os.path.basename(master)}: {len(rows)} emails | " + " | ".join(f"{k}: {v}" for k, v in sorted(counts.items())))
