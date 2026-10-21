"use strict";

const LABELS = {
  "real-deal": "Real deal",
  "meh": "Meh",
  "fake-sale": "Fake sale",
  "no-deal": "No deal",
  "not-enough-history": "Not enough history yet",
  "unavailable": "Couldn't check today",
};

let report = null;

function money(n) {
  if (n == null) return "—";
  return "$" + Number(n).toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function safeUrl(url) {
  return /^https?:\/\//i.test(url || "") ? url : null;
}

// Builds elements with textContent only: every title and URL comes from other websites.
function el(tag, props = {}, children = []) {
  const node = document.createElement(tag);
  for (const [key, value] of Object.entries(props)) {
    if (value == null) continue;
    if (key === "text") node.textContent = value;
    else if (key === "class") node.className = value;
    else node.setAttribute(key, value);
  }
  for (const child of [].concat(children)) if (child) node.append(child);
  return node;
}

function sparkline(history) {
  const points = history.filter((p) => p[1] != null);
  if (points.length < 2) return null;
  const w = 96, h = 32;
  const prices = points.map((p) => p[1]);
  const lo = Math.min(...prices), hi = Math.max(...prices), span = hi - lo || 1;
  const d = points.map((p, i) => {
    const x = (i / (points.length - 1)) * w;
    const y = h - 3 - ((p[1] - lo) / span) * (h - 6);
    return `${i ? "L" : "M"}${x.toFixed(1)},${y.toFixed(1)}`;
  }).join(" ");
  const ns = "http://www.w3.org/2000/svg";
  const svg = document.createElementNS(ns, "svg");
  svg.setAttribute("viewBox", `0 0 ${w} ${h}`);
  svg.setAttribute("class", "spark");
  svg.setAttribute("role", "img");
  svg.setAttribute("aria-label", `Price over ${points.length} days: low ${money(lo)}, high ${money(hi)}`);
  const path = document.createElementNS(ns, "path");
  path.setAttribute("d", d);
  svg.append(path);
  return svg;
}

function card(item) {
  const r = item.rating;
  const url = safeUrl(item.url);
  const title = url
    ? el("a", { href: url, target: "_blank", rel: "noopener", text: item.title })
    : el("span", { text: item.title });
  const pct = r.percent_below > 0 ? el("span", { class: "pct", text: `${r.percent_below}% below normal` }) : null;
  const notes = [];
  if (item.was_price) notes.push(`Store says it was ${money(item.was_price)}`);
  if (item.target_price != null) notes.push(`Your target ${money(item.target_price)}${r.hit_target ? " — hit!" : ""}`);
  if (r.label === "not-enough-history") notes.push(`Tracked ${r.history_days} of 14 days needed`);
  if (item.error) notes.push(item.error);
  const image = safeUrl(item.image) ? el("img", { src: item.image, alt: "", loading: "lazy" }) : el("div", { class: "noimg" });
  return el("article", { class: "card" }, [
    image,
    el("div", { class: "body" }, [
      el("div", { class: "top" }, [el("span", { class: `badge ${r.label}`, text: LABELS[r.label] || r.label }), pct]),
      el("h3", {}, title),
      el("p", { class: "meta", text: [item.store, item.interest].filter(Boolean).join(" · ") }),
      el("div", { class: "row" }, [
        el("dl", { class: "stats" }, [
          el("dt", { text: "Now" }), el("dd", { class: "now", text: money(item.price) }),
          el("dt", { text: "Normal" }), el("dd", { text: money(r.normal) }),
          el("dt", { text: "Lowest seen" }), el("dd", { text: money(r.lowest) }),
        ]),
        sparkline(item.history),
      ]),
      notes.length ? el("p", { class: "note", text: notes.join(" · ") }) : null,
    ]),
  ]);
}

function fillSelect(select, values) {
  for (const value of [...new Set(values.filter(Boolean))].sort()) {
    select.append(el("option", { value, text: value }));
  }
}

function renderDeals() {
  const store = document.getElementById("f-store").value;
  const interest = document.getElementById("f-interest").value;
  const realOnly = document.getElementById("f-real").checked;
  const shown = report.deals.filter((d) =>
    (!store || d.store === store) &&
    (!interest || d.interest === interest) &&
    (!realOnly || d.rating.label === "real-deal"));
  const list = document.getElementById("deal-list");
  list.replaceChildren(...shown.map(card));
  if (!shown.length) list.append(el("p", { class: "empty", text: "No deals match right now. Check back tomorrow." }));
}

function renderProblems() {
  const failed = report.sources.filter((s) => !s.ok);
  const box = document.getElementById("problems");
  box.replaceChildren();
  if (!failed.length) return;
  box.className = "problems";
  box.append(el("strong", { text: "Some checks didn't work today:" }),
    el("ul", {}, failed.map((s) => el("li", { text: `${s.name}: ${s.message}` }))));
}

function renderWatchlist() {
  const list = document.getElementById("watch-list");
  list.replaceChildren(...report.watchlist.map(card));
  if (!report.watchlist.length) {
    list.append(el("p", { class: "empty", text: "Nothing on your watchlist yet. Add product links in the settings file (see the Settings tab)." }));
  }
}

function renderSettings() {
  const s = report.settings;
  const body = document.getElementById("settings-body");
  const interests = Object.entries(s.interests).map(([name, words]) =>
    el("li", { text: `${name}: ${words.join(", ") || "(no search words yet)"}` }));
  body.replaceChildren(
    el("h2", { text: "Real deal means" }),
    el("p", { text: `At least ${s.threshold}% below the item's normal price (its typical price over the last 90 days), or a new lowest price.` }),
    el("h2", { text: "Your interests" }),
    interests.length ? el("ul", {}, interests) : el("p", { text: "None yet." }),
    el("h2", { text: "Shop sale sections watched" }),
    s.shop_sections.length ? el("ul", {}, s.shop_sections.map((u) => el("li", { text: u }))) : el("p", { text: "None." }),
    el("h2", { text: "Watchlist" }),
    el("p", { text: `${s.watch_count} item(s).` }),
    el("h2", { text: "Changing these" }),
    el("p", {}, ["Edit ", el("code", { text: "config/settings.yml" }),
      " in your GitHub repository (or ask Claude to). The next daily check uses the new settings."]),
  );
}

function showTab(name) {
  for (const button of document.querySelectorAll("nav button")) {
    button.classList.toggle("active", button.dataset.tab === name);
  }
  for (const id of ["deals", "watchlist", "settings"]) {
    document.getElementById(id).hidden = id !== name;
  }
}

async function load() {
  const updated = document.getElementById("updated");
  try {
    const response = await fetch("deals.json", { cache: "no-store" });
    if (!response.ok) throw new Error(response.status);
    report = await response.json();
  } catch (e) {
    updated.textContent = "Couldn't load today's deals. The daily check may not have run yet.";
    return;
  }
  const when = new Date(report.generated);
  updated.textContent = `Checked ${when.toLocaleString([], { dateStyle: "medium", timeStyle: "short" })} · ` +
    `${report.deals.filter((d) => d.rating.label === "real-deal").length} real deals`;
  fillSelect(document.getElementById("f-store"), report.deals.map((d) => d.store));
  fillSelect(document.getElementById("f-interest"), report.deals.map((d) => d.interest));
  renderProblems();
  renderDeals();
  renderWatchlist();
  renderSettings();
}

for (const button of document.querySelectorAll("nav button")) {
  button.addEventListener("click", () => showTab(button.dataset.tab));
}
for (const id of ["f-store", "f-interest", "f-real"]) {
  document.getElementById(id).addEventListener("change", renderDeals);
}
load();
