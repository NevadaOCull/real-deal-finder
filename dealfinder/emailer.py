import smtplib
from email.message import EmailMessage


def _money(amount):
    return f"${amount:,.2f}"


def _line(item):
    rating = item["rating"]
    parts = [f"{item['title']} - {_money(item['price'])} at {item['store']}"]
    if rating["label"] == "real-deal" and rating.get("normal") is not None:
        parts.append(f"{rating['percent_below']:g}% below its normal {_money(rating['normal'])}")
    if rating.get("hit_target") and item.get("target_price") is not None:
        parts.append(f"hit your target of {_money(item['target_price'])}")
    return ", ".join(parts) + f"\n  {item['url']}"


def compose(alerts: list[dict], site_url: str, address: str) -> EmailMessage:
    count = len(alerts)
    msg = EmailMessage()
    msg["Subject"] = f"{count} deal alert{'' if count == 1 else 's'} today"
    msg["From"] = address
    msg["To"] = address
    body = "\n\n".join(_line(item) for item in alerts)
    if site_url:
        body += f"\n\nSee everything: {site_url}"
    msg.set_content(body + "\n")
    return msg


def send(msg: EmailMessage, address: str, app_password: str, smtp_factory=smtplib.SMTP_SSL) -> None:
    with smtp_factory("smtp.gmail.com", 465) as smtp:
        smtp.login(address, app_password)
        smtp.send_message(msg)
