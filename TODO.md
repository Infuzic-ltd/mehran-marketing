# Garments campaign, round 2 (set up 2026-11-25)
- Round 1 log (685 lines, Oct 21 – Nov 25) archived as `garments_sent_round1.txt`; `sent.txt` now logs round 2 and starts empty. The master shows "Garments Email round1" and "Garments Email Current Round".
- Garments queue: 672 (664 round-1 recipients + 8 never mailed). At 50 a day that is about two weeks. Towel contacts stay in the towel segment and aren't included.

# Gemini personalisation (garments only, from 2026-11-25)
- 2026-11-25 test run: gemini-2.5-flash is closed to new users (404); gemini-flash-latest hit 503 "high demand" and then its free quota after ~6 requests. The script now retries busy errors and falls back through gemini-flash-latest → gemini-flash-lite-latest → gemini-3.1-flash-lite → gemini-2.5-flash-lite (override with `GEMINI_MODEL`, comma-separated). The first openers invented familiarity ("we have long admired"), association membership and a false "close by" claim; the prompt now forbids these and `check()` rejects them, sending that contact to the template.
- `leads/personalise_garments.py` asks Gemini (free tier) for a 1–2 sentence opener per company, using only public facts from the master (product focus, location, associations), never email addresses. Output: `garments_openers.csv` (email, company, facts, opener, status). Run: `export GEMINI_API_KEY=...` then `python3 -I leads/personalise_garments.py`; rerun after a quota stop to continue.
- Fallback to the plain template for: fewer than 2 facts (`GEMINI_MIN_FACTS`, ~450 of 672 contacts), Gemini errors/quota, openers failing the checks (length, links, greetings, invented numbers), and any opener blanked or not "ok" in the CSV.
- `send_campaign.py garments` inserts the opener as its own paragraph after "Greetings from Mehran Prints!"; the rest of the email is unchanged. The check copy shows a personalised example.

# Master database (from 2026-11-25)
- `karachi_textile_garment_master_database_v6.xlsx` is the master (v5 kept untouched as a backup). Its first sheet, "Master Contacts", has one row per email: company, phone, address, industry, segment, Garments Email Sent, Towel Email 2026-10, Towel Email Current Round, Do Not Email, Next Campaign, sources.
- Rebuild everything with `python3 -I leads/build_master.py` (about 10 seconds; mail-server checks are cached in `leads/.domain_cache.json`). It reads your "Company Contacts" sheet, every lead CSV, the send logs and `do_not_email.txt`, rewrites "Master Contacts", and writes `emails.txt` (Garments queue) and `towel_emails.txt` (Towel queue). While a campaign is sending it updates the workbook but leaves the queue files alone.
- Add your own research to "Company Contacts" (not "Master Contacts", which is regenerated). Agents add to `leads/sources/*.csv` (garments) and `leads/towel_sources/*.csv` (towels).
- `leads/build_garments.py` and `leads/build_towels.py` were replaced by `build_master.py`; any instructions below that mention them now mean `build_master.py`. `garment_exporters.csv` and `towel_review.csv` are no longer updated (the master has the same information).
- Next Campaign rules: towel-segment contacts go to the Towel queue until they get the current round's towel email; other contacts go to the Garments queue until they get the garments email; anyone who got a towel email but not the garments one is "Held" to avoid two pitches close together.
- 2026-11-25: the user is updating the master's research ("Company Contacts") themselves, so agent lead collection is paused. Don't start new-source agents unless asked. Candidate sources if asked later: PCFA final voters list 2024-26, PRGMEA South Zone Excel, PDMEA denim members, APTPMA processing mills, PWMA weaving mills, TexBridge directory.

# Status 2026-11-23: back on garments
- Towel round 2 finished: 460 sent, nothing queued.
- Garments resumed: 75 queued after rebuild (firms that got the round-2 towel email are held back); a 50-email garments run started (log in `logs/`). TDAP Ch61/62 lookups restarted (single agent, no sub-agents), appending to `ch6162_sites.csv`; `emails.txt` is rebuilt automatically between runs.

# Towel campaign, round 2 (started 2026-11-16)
- Garments is paused: `sent.txt` (610 sent) and the 94 addresses queued in `emails.txt` are kept as they are. Before resuming garments, rebuild (`python3 -I leads/build_garments.py leads/sources .`) so firms that got the towel email in round 2 are dropped.
- Round 1 towel log archived as `towels_sent_2026-10.txt`. `towels_sent.txt` now logs round 2.
- `towel_emails.txt` = everyone in `towel_exporters.csv` + `leads/towel_sources/*.csv` + earlier logs, minus `do_not_email.txt` and dead domains. Rebuild: `python3 -I leads/build_towels.py` (also rewrites `towel_review.csv`, the same list with company names).
- `do_not_email.txt`: people already in touch (an address, or @domain.com for a whole company). Both campaigns and both builds skip them.
- New towel sources: Heimtextil towel/terry exhibitors, all Pakistan (`heimtextil_towels.csv`, 74 new emails); `more_towels.csv` (14 rows, agent stopped 2026-11-16 while starting on TDAP chapter 63; not yet in `towel_emails.txt` because a campaign run was in progress, so run `python3 -I leads/build_towels.py` after the run finishes).
- 2026-11-20 end of day (all stopped): towel round 2 at 405 sent, 55 queued; garments 610 sent, 82 queued. `more_towels.csv` 30 rows, `ch6162_sites.csv` 62 rows (TDAP Ch61/62 still has ~370 firms to look up; chapter 63 towel lookups not started). Agents kept stopping on permission prompts, so consider standing permissions for curl/pdftotext/python3 -I/WebFetch first.
- Earlier on 2026-11-20: 353 towel emails sent this round, 91 queued; a 50-email towel run started (log in `logs/`). Agents restarted: more towel exporters (TDAP chapter 63, newer TDAP lists, other TMA documents, fairs) appending to `more_towels.csv`, and TDAP Ch61/62 garments lookups appending to `ch6162_sites.csv`. Both lists are rebuilt automatically between campaign runs.
- Every run sends a first check copy to muhammadbilalarifshaikh@gmail.com (not logged) to confirm inbox placement.

# Garments campaign: remaining work
Status (2026-11-11, wrapped up): 573 garment emails sent; `emails.txt` has 131 unsent addresses (Heimtextil 65, home-textile associations 33, TDAP Ch61/62 33). All agents stopped. Remaining work: source 1 (most of the 435 TDAP firms), 5 (apparel fairs), 9b (other home-textile fairs), and website lookups for FBATI's 66 garment/textile firms (names only). While agents run, `emails.txt` is rebuilt every 2 minutes when new rows land (skipped while `send_campaign.py` runs). Each writes rows to `leads/sources/<name>.csv` as it finds them, so a stop keeps everything found; after any stop, rebuild (see Workflow).
Checked and empty (don't redo): PAKSEA member details need a login/subscription; TEXPO "All-textile-31-1.pdf" and TDAP "Sportswear.pdf" are brochures with no exporter list.
## Sources
| # | Source | Status | Output file | Notes |
|---|---|---|---|---|
| – | PHMA member directory (phmaonline.com/all-members.php) | Done | `phma.csv`, `associations.csv` | 285 emails in the list |
| – | TDAP/chamber exporter lists (RMG, denim, clothing PDFs) | Done | `tdap_chambers.csv` | 55 emails in the list |
| 1 | TDAP HS Chapter 61/62 exporter directories (tdap.gov.pk/pakistani-exporters) | Partial: 37 rows (stopped 2026-11-11) | `ch6162_sites.csv` | About 435 Karachi firms to look up; roughly the first 30–40 were done (A–S, garment-sounding names first). Guessed-domain matches need checking: 5 were wrong businesses (gum, foods, tools, pharma, equipment) and were removed; verify each site is a Karachi textile firm before keeping it. The PDFs are slow to download (curl -m 600) |
| 2 | PRGMEA Southern Zone members (Final_Voters_List_2026-2028_SZ.pdf, prgmea.org profiles) | Mostly done: 63 rows | `prgmea_sites.csv` | 197 Karachi members; first website pass done, stopped during cleanup of mismatched sites |
| 3 | PCFA provisional members 2024-26 (pcfa.pk) | Done | `pcfa.csv` | 146 Karachi emails, 122 new after dedupe; CNICs not kept, PDF deleted |
| 4 | PAKSEA members (paksea.com/all-members) | Skipped | – | Member details are behind a login/subscription |
| 5 | Trade-fair exhibitors: TEXPO, Messe Frankfurt (Texworld, Apparel Sourcing), MAGIC, Munich Apparel Source | To do: 0 rows | `fairs.csv` | Was fetching Messe Frankfurt exhibitor pages when stopped. Pakistan / Karachi, apparel only |
| 6 | KATI, FBATI, NKATI, LATI, BQATI industry associations | Done: 44 rows (all LATI) | `industrial_areas.csv` | No other association publishes usable emails: FBATI's directory (fbati.com/members: 28 garment/hosiery + 38 textile firms) has phones only, and its voter PDF carries CNICs; KATI voter PDFs carry CNICs; NKATI has no list; BQATI lists names only; SITE Superhighway's site is "Coming Soon". The FBATI/BQATI names could still go through website lookups like source 1 |
| 8 | Karachi home textiles: PBEA, APTMA South Zone member lists | Done: 41 rows | `home_associations.csv` | PBEA: 10 from the 2014–15 office-bearers PDF (old, expect bounces). APTMA: 31 from 24 mills' own websites; Sapphire's investor-complaints mailbox removed. Not reached: other home-textile associations (web-search limit) |
| 9 | Karachi home textiles: Heimtextil exhibitors | Done (2026-11-11): 117 rows, 68 new | `heimtextil.csv` | Pulled from Messe Frankfurt's public search API: `https://api.messefrankfurt.com/service/esb_api/exhibitor-service/api/2.1/public/exhibitor/search?q=karachi&findEventVariable=HEIMTEXTIL` with the page's public `apikey` header. Other Messe Frankfurt event IDs gave 0–6 Karachi hits (Texworld/Apparel Sourcing aren't on this system) |
| 9b | Other home-textile fairs, TDAP home-textile brochures | To do | `home_fairs.csv` | |
| 7 | Google Places API (official) for garment factories in Karachi industrial areas | Blocked | – | Needs a Google Cloud API key with billing (`GOOGLE_PLACES_API_KEY`). Maps itself must not be scraped |
## Workflow for adding a source
- Save it as `leads/sources/<name>.csv` with header `company,email,city,source_url`. Use only published emails, never guessed ones like info@domain, and Karachi only.
- Rebuild: `python3 -I leads/build_garments.py leads/sources .` This rewrites `emails.txt` and `garment_exporters.csv`. It removes duplicates, skips anyone in `towels_sent.txt` or `sent.txt`, and drops domains with no mail records.
- Don't rebuild while `send_campaign.py` is running, because both write `emails.txt`. Rebuilding between runs is safe.
## Deliberately excluded
- PHMA 2026-28 voter lists (phmaonline.com/Elections.php): copy-protected, watermarked, and they contain CNIC (national ID) numbers. Ask PHMA (membership@phmaonline.com) for permission if the extra ~965 addresses are wanted.
- 17 addresses already mailed in the towel campaign, so nobody gets two cold pitches.
- Domains with no MX/A records, listed in the build output.
## Deliverability (emails landing in spam), not yet decided
- Tried 2026-11-11: a short personalised garments email (company name in subject/greeting, no Drive link). The user preferred the original long version, so it was restored the same day. Still open: 20–25 emails a day instead of 50.
- Long term: send from your own domain (e.g. mehranprints.com on Google Workspace) instead of @gmail.com.
## Other follow-ups
- `send_mail.py` hardcodes the Gmail app password as a fallback. Move it to the `GMAIL_APP_PASSWORD` environment variable only, and revoke and regenerate it if this folder is ever shared or pushed.
- To re-run the towel campaign, put addresses in `towel_emails.txt` and run `python3 send_campaign.py towel`. Its sent log stays in `towels_sent.txt`.
