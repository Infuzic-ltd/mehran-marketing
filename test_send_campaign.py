import os
import smtplib
import tempfile

from send_campaign import CAMPAIGNS, run

d = tempfile.mkdtemp()
emails, sent = os.path.join(d, "emails.txt"), os.path.join(d, "sent.txt")
with open(emails, "w") as f:
    f.write("a@x.com\nB@x.com\n\nb@x.com\nbad@x.com\nc@x.com\n")
with open(sent, "w") as f:
    f.write("a@x.com\n")

calls, subjects = [], set()


def fake_send(to, subject, body, html=None):
    assert html and "<b>" in html and "Bilal Shaikh" in body and "Bilal Shaikh" in html
    if to == "bad@x.com":
        raise smtplib.SMTPRecipientsRefused({to: (550, b"no such user")})
    calls.append(to)
    subjects.add(subject)


run("garments", emails, sent, send=fake_send, seed=None, delay=(0, 0))
assert subjects == {CAMPAIGNS["garments"]["subject"]}, subjects  # sends the chosen campaign's pitch
assert calls == ["b@x.com", "c@x.com"], calls  # skips already-sent, dedupes, ignores case
assert open(sent).read().split() == ["a@x.com", "b@x.com", "c@x.com"]
assert open(emails).read().split() == ["bad@x.com"]  # sent ones removed, refused one kept

calls.clear()
run("garments", emails, sent, send=fake_send, seed=None, delay=(0, 0))
assert calls == []  # second run sends nothing

with open(emails, "w") as f:
    f.write("d@x.com\ne@x.com\nf@x.com\n")
run("towel", emails, sent, send=fake_send, seed=None, delay=(0, 0), max_per_run=2)
assert calls == ["d@x.com", "e@x.com"], calls  # stops at the per-run cap
assert open(emails).read().split() == ["f@x.com"]  # rest waits for the next run
dne = os.path.join(d, "do_not_email.txt")
with open(dne, "w") as f:
    f.write("# already in touch\ng@x.com\n@friend.com\n")
with open(emails, "w") as f:
    f.write("g@x.com\nali@friend.com\nh@x.com\n")
calls.clear()
run("towel", emails, sent, send=fake_send, seed=None, delay=(0, 0), do_not_email_file=dne)
assert calls == ["h@x.com"], calls  # skips the listed address and the whole listed domain
assert "g@x.com" not in open(emails).read() and "friend.com" not in open(emails).read()

with open(emails, "w") as f:
    f.write("i@x.com\n")
calls.clear()
run("towel", emails, sent, send=fake_send, seed="me@x.com", delay=(0, 0), do_not_email_file=dne)
assert calls == ["me@x.com", "i@x.com"], calls  # check copy goes first
assert "me@x.com" not in open(sent).read()  # and is never logged as a send
calls.clear()
run("towel", emails, sent, send=fake_send, seed="me@x.com", delay=(0, 0), do_not_email_file=dne)
assert calls == [], calls  # nothing left to send, so no check copy either

# Garments openers: reviewed "ok" ones go in after the greeting; anything else falls back to the plain template
openers = os.path.join(d, "openers.csv")
with open(openers, "w") as f:
    f.write("email,company,facts,opener,status\n"
            "p@x.com,P Co,PHMA,As a knitwear house & PHMA member you print a lot.,ok\n"
            "q@x.com,Q Co,,,template: not enough data\n"
            "r@x.com,R Co,PHMA,Unreviewed text,template: Gemini error\n")
with open(emails, "w") as f:
    f.write("p@x.com\nq@x.com\nr@x.com\n")
bodies, htmls = {}, {}


def capture_send(to, subject, body, html=None):
    bodies[to], htmls[to] = body, html


run("garments", emails, sent, send=capture_send, seed="me@x.com", delay=(0, 0), do_not_email_file=dne, openers_file=openers)
plain = CAMPAIGNS["garments"]
assert "Greetings from Mehran Prints!\n\nAs a knitwear house & PHMA member you print a lot.\n\nWe would like" in bodies["p@x.com"]
assert "<p>As a knitwear house &amp; PHMA member you print a lot.</p>" in htmls["p@x.com"]  # escaped for HTML
assert bodies["q@x.com"] == plain["body"] and htmls["q@x.com"] == plain["html"]  # not enough data: template
assert bodies["r@x.com"] == plain["body"]  # failed status: template
assert "knitwear house" in bodies["me@x.com"]  # check copy shows a personalised example
assert plain["body"].count("knitwear house") == 0  # the shared template itself is untouched
print("ok")
