from dealfinder.emailer import compose, send


def entry(title, price, normal=None, percent=None, label="real-deal", target=None, hit=False):
    return {"title": title, "store": "DriftHQ", "url": "https://drifthq.com/products/x", "price": price,
            "target_price": target,
            "rating": {"label": label, "normal": normal, "percent_below": percent, "hit_target": hit}}


def test_compose():
    msg = compose([entry("Coilovers", 800, 1000, 20.0),
                   entry("Bucket seat", 1250.5, label="meh", target=1300, hit=True)],
                  "https://nevadaocull.github.io/real-deal-finder/", "me@gmail.com")
    body = msg.get_content()
    assert msg["Subject"] == "2 deal alerts today"
    assert msg["To"] == msg["From"] == "me@gmail.com"
    assert "Coilovers - $800.00 at DriftHQ, 20% below its normal $1,000.00" in body
    assert "Bucket seat - $1,250.50 at DriftHQ, hit your target of $1,300.00" in body
    assert "https://drifthq.com/products/x" in body
    assert "See everything: https://nevadaocull.github.io/real-deal-finder/" in body


def test_compose_single():
    assert compose([entry("Coilovers", 800, 1000, 20.0)], "", "me@gmail.com")["Subject"] == "1 deal alert today"


def test_send_logs_in_and_sends():
    events = []

    class FakeSMTP:
        def __init__(self, host, port):
            events.append(("connect", host, port))

        def __enter__(self):
            return self

        def __exit__(self, *exc):
            events.append(("close",))

        def login(self, user, password):
            events.append(("login", user, password))

        def send_message(self, msg):
            events.append(("send", msg["Subject"]))

    msg = compose([entry("Coilovers", 800, 1000, 20.0)], "", "me@gmail.com")
    send(msg, "me@gmail.com", "app-pass", smtp_factory=FakeSMTP)
    assert events == [("connect", "smtp.gmail.com", 465), ("login", "me@gmail.com", "app-pass"),
                      ("send", "1 deal alert today"), ("close",)]
