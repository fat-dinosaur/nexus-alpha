/* NEXUS ALPHA — local-only, offline financial evidence UI preview.
 * No remote requests, AI calls, fake live quotes or trading functionality.
 */
"use strict";

const TAGS = [
  ["revenue", "Revenue", "metricRevenue", "periodRevenue"],
  ["gross_profit", "Gross profit", "metricGrossProfit", "periodGrossProfit"],
  ["net_income", "Net income", "metricNetIncome", "periodNetIncome"],
  ["operating_cash_flow", "Operating cash flow", "metricCashFlow", "periodCashFlow"],
  ["operating_income", "Operating income", null, null],
  ["diluted_eps", "Diluted EPS", null, null],
];

const sample = {
  schema_version: "0.1.0", ticker: "EXMP", cik: "0000000000",
  company_name: "Example Semiconductors · Fictional Issuer",
  is_demo: true, retrieved_at_utc: "2025-12-01T12:00:00+00:00", as_of: null,
  source: { provider: "SYNTHETIC EXAMPLE", kind: "fixture", url: null },
  metrics: Object.fromEntries(TAGS.map(([id], index) => [id, {
    value: [15200000000, 6200000000, 2900000000, 4100000000, 3850000000, 2.14][index],
    unit: id === "diluted_eps" ? "USD/shares" : "USD",
    concept: "synthetic:demo",
    period_start: "2025-01-01", period_end: "2025-09-30", filed: "2025-10-15",
    form: "DEMO", accession: "SYNTHETIC-NOT-AN-SEC-FILING"
  }]))
};

const $ = (id) => document.getElementById(id);
let snapshot = sample;
let isDemo = true;
let toastTimer;

function toast(message) {
  const el = $("toast");
  el.textContent = message;
  el.classList.add("visible");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => el.classList.remove("visible"), 3300);
}

function formatMoney(fact) {
  if (!fact || typeof fact.value !== "number" || !Number.isFinite(fact.value)) return "—";
  const n = fact.value;
  if (fact.unit === "USD/shares") return `$${n.toLocaleString("en-US", { maximumFractionDigits: 2 })}`;
  if (fact.unit !== "USD") return `${n.toLocaleString("en-US")} ${fact.unit || ""}`;
  const abs = Math.abs(n);
  const scales = [[1e12, "T"], [1e9, "B"], [1e6, "M"]];
  for (const [divider, suffix] of scales) {
    if (abs >= divider) return `${n < 0 ? "−" : ""}$${(abs / divider).toFixed(2)}${suffix}`;
  }
  return `${n < 0 ? "−" : ""}$${abs.toLocaleString("en-US", { maximumFractionDigits: 2 })}`;
}

function setText(id, value) { $(id).textContent = value == null ? "—" : String(value); }

function addCell(row, value, className) {
  const cell = document.createElement("td");
  cell.textContent = value;
  if (className) cell.className = className;
  row.appendChild(cell);
  return cell;
}

function renderTable() {
  const body = $("evidenceRows");
  body.replaceChildren();
  for (const [id, label] of TAGS) {
    const fact = snapshot.metrics[id];
    const row = document.createElement("tr");
    const metric = addCell(row, label, "metric-cell");
    const sub = document.createElement("small");
    sub.textContent = fact?.concept || "Not reported";
    metric.appendChild(sub);
    addCell(row, formatMoney(fact), fact ? "value-cell" : "no-value");
    addCell(row, fact?.period_end || "—");
    addCell(row, fact?.filed || "—");
    const cell = document.createElement("td");
    const chip = document.createElement("span");
    chip.className = `source-chip${isDemo ? " demo" : ""}`;
    chip.textContent = isDemo ? "◇ SYNTHETIC" : fact?.accession ? "↗ " + fact.accession : "NOT AVAILABLE";
    if (!isDemo && fact?.accession && snapshot.source?.url?.startsWith("https://data.sec.gov/")) {
      const link = document.createElement("a");
      link.href = snapshot.source.url;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.title = `Original SEC Company Facts API · accession ${fact.accession}`;
      link.appendChild(chip);
      cell.appendChild(link);
    } else {
      cell.appendChild(chip);
    }
    row.appendChild(cell);
    body.appendChild(row);
  }
}

function render(data, demo) {
  snapshot = data;
  isDemo = demo;
  setText("companyName", data.company_name || "Unknown issuer");
  setText("ticker", data.ticker || "UNKNOWN");
  setText("cik", demo ? "SYNTHETIC COMPANY" : `CIK ${data.cik || "?"}`);
  setText("retrievedDate", demo ? "Illustrative dataset" : (data.retrieved_at_utc || "Unknown").slice(0, 10));
  const badge = $("dataBadge");
  badge.className = demo ? "badge-demo" : "badge-real";
  badge.textContent = demo ? "SYNTHETIC DEMO DATA" : "IMPORTED SEC DATA";
  for (const [id, , metricId, periodId] of TAGS) {
    if (!metricId) continue;
    const fact = data.metrics?.[id];
    setText(metricId, formatMoney(fact));
    setText(periodId, fact?.period_end ? `${fact.form || "FILING"} · ${fact.period_end}` : "Unavailable from source");
  }
  const available = TAGS.filter(([id]) => data.metrics?.[id] != null).length;
  const percentage = Math.round(100 * available / TAGS.length);
  $("healthRing").style.setProperty("--coverage", `${percentage}%`);
  setText("coveragePercent", `${percentage}%`);
  setText("factsCount", `${available} / ${TAGS.length}`);
  setText("providerName", demo ? "Demo fixture" : "SEC EDGAR");
  setText("integrityStatus", demo ? "Synthetic" : "Source linked");
  setText("dataNotice", demo
    ? "Synthetic numbers are for visual evaluation only. They are not real company data."
    : "Imported file loaded locally. SEC facts preserve filing periods; no AI or valuation inference has been applied.");
  renderTable();
}

function isValidSnapshot(data) {
  return data && typeof data === "object" && !Array.isArray(data)
    && typeof data.ticker === "string" && typeof data.metrics === "object" && data.metrics !== null
    && typeof data.source === "object" && data.source !== null;
}

async function loadFile(file) {
  if (!file) return;
  try {
    if (file.size > 2_000_000) throw new Error("JSON exceeds the 2MB preview limit.");
    const data = JSON.parse(await file.text());
    if (!isValidSnapshot(data)) throw new Error("Not a NEXUS ALPHA snapshot JSON.");
    if (data.is_demo !== true && (data.source.provider !== "SEC EDGAR" || !String(data.source.url || "").startsWith("https://data.sec.gov/"))) {
      throw new Error("Real-data mode accepts only SEC EDGAR snapshots generated by the PoC.");
    }
    render(data, data.is_demo === true);
    toast(`Loaded ${data.ticker} · ${data.is_demo ? "demo" : "SEC data"}`);
  } catch (err) {
    toast(`Import failed: ${err.message}`);
  }
}

function downloadCurrent() {
  const blob = new Blob([JSON.stringify(snapshot, null, 2) + "\n"], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = `${(snapshot.ticker || "snapshot").toLowerCase()}-nexus-alpha.json`;
  anchor.click();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
  toast(isDemo ? "Synthetic example exported · not real market data" : "Snapshot exported");
}

document.addEventListener("DOMContentLoaded", () => {
  render(sample, true);
  try { $("researchNote").value = localStorage.getItem("nexus-alpha-note") || ""; } catch (_) { /* local storage may be unavailable */ }
  const openPicker = () => $("fileInput").click();
  $("uploadButton").addEventListener("click", openPicker);
  $("chooseFile").addEventListener("click", openPicker);
  $("fileInput").addEventListener("change", async (event) => {
    await loadFile(event.target.files[0]);
    event.target.value = "";
  });
  $("resetDemo").addEventListener("click", () => { render(sample, true); toast("Restored clearly labeled synthetic preview"); });
  $("downloadSnapshot").addEventListener("click", downloadCurrent);
  $("saveNote").addEventListener("click", () => {
    try { localStorage.setItem("nexus-alpha-note", $("researchNote").value); setText("noteStatus", "Saved in this browser"); toast("Research draft saved locally"); }
    catch (_) { toast("Browser storage unavailable. Copy your note to preserve it."); }
  });
  for (const nav of document.querySelectorAll(".nav-item")) {
    nav.addEventListener("click", () => {
      document.querySelectorAll(".nav-item").forEach((item) => item.classList.remove("active"));
      nav.classList.add("active");
    });
  }
  document.addEventListener("dragover", (e) => { if ([...e.dataTransfer.types].includes("Files")) e.preventDefault(); });
  document.addEventListener("drop", (e) => {
    if ([...e.dataTransfer.types].includes("Files")) { e.preventDefault(); loadFile(e.dataTransfer.files[0]); }
  });
});
