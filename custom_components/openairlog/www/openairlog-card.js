/* OpenAirLog-Karte - zeigt den naechsten bzw. laufenden Umlauf.
   Bewusst ohne Build-Schritt und ohne Abhaengigkeiten, damit die Karte
   direkt aus der Integration ausgeliefert werden kann. */

const WT = ["So", "Mo", "Di", "Mi", "Do", "Fr", "Sa"];

function d(v) { return v ? new Date(v) : null; }
function hhmm(x) {
  return x ? x.toLocaleTimeString("de-DE", { hour: "2-digit", minute: "2-digit" }) : "--:--";
}
function tag(x) {
  return x ? `${WT[x.getDay()]} ${String(x.getDate()).padStart(2, "0")}.${String(x.getMonth() + 1).padStart(2, "0")}.` : "";
}
function kalendertage(ziel) {
  // Kalendertage zaehlen, nicht 24-Stunden-Bloecke: Sonst ergaeben 59,5 h
  // "in 3 Tagen" und 57,5 h "in 2 Tagen", obwohl beides derselbe Tag ist.
  const a = new Date(); a.setHours(0, 0, 0, 0);
  const b = new Date(ziel); b.setHours(0, 0, 0, 0);
  return Math.round((b - a) / 86400000);
}

function restzeit(ziel) {
  if (!ziel) return "";
  const min = Math.round((ziel - new Date()) / 60000);
  if (min <= 0) return "jetzt";
  if (min < 60) return `in ${min} min`;
  const tage = kalendertage(ziel);
  if (tage <= 0) return `in ${Math.round(min / 60)} Std.`;
  if (tage === 1) return "morgen";
  if (tage === 2) return "übermorgen";
  return `in ${tage} Tagen`;
}

class OpenAirLogCard extends HTMLElement {
  setConfig(config) {
    this._config = { titel: "Dienst", ...config };
    if (!this.shadowRoot) {
      this.attachShadow({ mode: "open" });
    }
  }

  static getStubConfig(hass) {
    const e = Object.keys(hass.states).find((x) =>
      x.endsWith("_naechster_dienst") || x.endsWith("_nachster_dienst"));
    return { entity: e || "sensor.openairlog_naechster_dienst" };
  }

  getCardSize() { return 4; }

  set hass(hass) {
    this._hass = hass;
    this._render();
  }

  _finde(...teile) {
    const ids = Object.keys(this._hass.states);
    for (const teil of teile) {
      if (!teil) continue;
      const hit = ids.find((x) => x.endsWith(`_${teil}`) || x.endsWith(`.${teil}`));
      if (hit) return hit;
    }
    return undefined;
  }

  _render() {
    if (!this._hass || !this.shadowRoot) return;
    const s = this._hass.states;
    const imDienst = (s[this._finde("im_dienst")] || {}).state === "on";
    const naechster = s[this._config.entity]
      || s[this._finde("naechster_dienst")]
      || s[this._finde("nachster_dienst")];
    const ende = s[this._finde("dienstende")];
    // Waehrend des Dienstes gehoeren Beine und Zeiten zum laufenden Umlauf
    // (Dienstende-Sensor), nicht zum naechsten.
    const haupt = (imDienst && ende) ? ende : naechster;
    if (!haupt) {
      this.shadowRoot.innerHTML = `<ha-card><div class="leer">OpenAirLog: keine Daten</div>${this._css()}</ha-card>`;
      return;
    }

    const a = haupt.attributes || {};
    const los = s[this._finde(
      "losfahren", "naechster_schritt", "zuruck_zuhause", "zurueck_zuhause")];
    const heim = s[this._finde("voraussichtlich_zuhause", "zuhause")];

    const beginn = d(a.briefing) || (!imDienst ? d(haupt.state) : null);
    const endeD = d(ende && ende.state);
    const legs = Array.isArray(a.legs) ? a.legs : [];
    const mehrtaegig = a.mehrtaegig;

    const kopf = imDienst ? "Im Dienst" : (legs.length > 1 ? "Nächster Umlauf" : "Nächster Dienst");

    // Zeitmarken vor dem Dienst. Was zaehlt, haengt von der Art ab:
    //   Flug      -> Briefing und Abflug
    //   Simulator -> Briefing (Vor- und Nachbereitung sind laenger)
    //   Boden     -> nur, wann man da sein muss (kein Briefing)
    const art = a.art || (legs.length && legs[0].flug ? "flug" : "boden");
    const puffer = Number(a.puffer_minuten || 0);
    const vorOrt = d(a.vor_ort);
    const briefing = d(a.briefing) || beginn;
    const abflug = d(a.abflug);
    const marken = [];
    if (puffer > 0 && vorOrt) marken.push(`Vor Ort <b>${hhmm(vorOrt)}</b>`);
    if (art === "boden") {
      marken.push(`Beginn <b>${hhmm(briefing)}</b>`);
    } else {
      marken.push(`Briefing <b>${hhmm(briefing)}</b>`);
      if (art === "flug" && abflug) marken.push(`Abflug <b>${hhmm(abflug)}</b>`);
    }

    // Der Losfahren-Sensor wechselt seine Bedeutung: vor dem Dienst enthaelt er
    // die Anfahrt, waehrenddessen die Heimkehr. Das Attribut "richtung" sagt,
    // was gerade drinsteht - sonst stuende im Fuss "losfahren 19:00".
    const richtung = los && los.attributes ? los.attributes.richtung : null;
    const losD = richtung === "anfahrt" ? d(los.state) : null;
    const bezug = losD || beginn;
    const minBis = bezug ? (bezug - new Date()) / 60000 : null;
    let stufe = "";
    if (imDienst) stufe = "gruen";
    else if (minBis !== null && minBis <= 0) stufe = "rot";
    else if (minBis !== null && minBis <= 60) stufe = "rot";
    else if (minBis !== null && minBis <= 180) stufe = "gelb";
    const badge = imDienst ? "läuft"
      : (minBis !== null && minBis <= 0 ? "jetzt los!" : restzeit(beginn));

    // --- Abschnitte als Zeitstrahl ---
    let strecke = "";
    if (legs.length) {
      strecke = legs.map((l) => {
        const ab = d(l.ab), an = d(l.an);
        const nacht = ab && an && ab.getDate() !== an.getDate();
        return `
          <div class="leg">
            <div class="lz">${hhmm(ab)}</div>
            <div class="lp ort">${l.von || "?"}</div>
            <div class="ll"><span class="lf">${l.flug || ""}</span></div>
            <div class="lp ort">${l.nach || "?"}</div>
            <div class="lz">${hhmm(an)}${nacht ? "<sup>+1</sup>" : ""}</div>
          </div>`;
      }).join("");
    }

    const fuss = [];
    if (losD && los.state !== haupt.state) {
      const kl = stufe === "rot" ? "rot" : (stufe === "gelb" ? "gelb" : "");
      fuss.push(`<div class="fz"><ha-icon icon="mdi:train-car"></ha-icon>` +
        `<span>Losfahren <b class="${kl}">${restzeit(losD)}</b> um ${hhmm(losD)}</span></div>`);
    }
    if (heim && heim.state) {
      const h = d(heim.state);
      fuss.push(`<div class="fz"><ha-icon icon="mdi:home-clock-outline"></ha-icon>` +
        `<span>Du bist <b>${tag(h)} um ${hhmm(h)}</b> zurück</span></div>`);
    }

    this.shadowRoot.innerHTML = `
      <ha-card>
        <div class="kopf">
          <ha-icon icon="${imDienst ? "mdi:airplane-takeoff"
            : (art === "simulator" ? "mdi:monitor-dashboard"
            : (art === "boden" ? "mdi:school-outline" : "mdi:airplane-clock"))}"></ha-icon>
          <span class="titel">${kopf}</span>
          <span class="badge ${stufe}">${badge}</span>
        </div>

        <div class="zeit">
          <span class="gross">${tag(beginn)} ${hhmm(beginn)}</span>
          <span class="bis">– ${mehrtaegig ? tag(endeD) + " " : ""}${hhmm(endeD)}</span>
        </div>

        <div class="marken">
          ${marken.join(" · ")}
          ${puffer > 0 ? `<span class="puffer">inkl. ${puffer} min Puffer</span>` : ""}
        </div>

        <div class="unter">
          ${a.dienstcode ? `<span class="chip k-${a.kategorie || "dienst"}">${a.dienstcode}</span>` : ""}
          ${a.flugnummern ? `<span class="chip akzent">${a.flugnummern}</span>` : ""}
          ${legs.length > 1 ? `<span class="chip">${legs.length} Abschnitte</span>` : ""}
          ${!legs.length && a.stationen ? `<span class="chip">${a.stationen}</span>` : ""}
        </div>

        ${strecke ? `<div class="strecke">${strecke}</div>` : ""}
        ${fuss.length ? `<div class="fuss">${fuss.join("")}</div>` : ""}
      </ha-card>
      ${this._css()}`;
  }

  _css() {
    return `<style>
      ha-card { padding: 14px 16px; }
      .kopf { display:flex; align-items:center; gap:8px; margin-bottom:10px; }
      .kopf ha-icon { color: var(--primary-color); --mdc-icon-size: 20px; }
      .titel { font-weight:600; }
      .badge { margin-left:auto; font-size:12px; padding:2px 8px; border-radius:10px;
               background: var(--secondary-background-color); color: var(--secondary-text-color); }
      .badge.gruen { background: var(--success-color, #22c55e); color:#fff; }
      .badge.gelb  { background: var(--warning-color, #ffc107); color:#000; }
      .badge.rot   { background: var(--error-color, #f44336); color:#fff; }
      .chip.akzent { background: color-mix(in srgb, var(--primary-color) 18%, transparent);
                     color: var(--primary-color); }
      .chip.k-standby  { background: color-mix(in srgb, var(--warning-color, #ffc107) 20%, transparent);
                         color: var(--warning-color, #ffc107); }
      .chip.k-schulung { background: var(--secondary-background-color); }
      .chip.k-dienst   { background: color-mix(in srgb, var(--primary-color) 14%, transparent);
                         color: var(--primary-color); }
      .ort { color: var(--primary-color); }
      .fuss .rot  { color: var(--error-color, #f44336) !important; font-weight:700; }
      .fuss .gelb { color: var(--warning-color, #ffc107) !important; font-weight:700; }
      .zeit { display:flex; align-items:baseline; gap:8px; }
      .gross { font-size:24px; font-weight:600; }
      .bis { color: var(--secondary-text-color); }
      .marken { margin-top:6px; font-size:13px; color: var(--secondary-text-color); }
      .marken b { color: var(--primary-text-color); font-weight:600; }
      .puffer { margin-left:8px; font-size:11px; opacity:.65; white-space:nowrap; }
      .unter { display:flex; flex-wrap:wrap; gap:6px; margin-top:8px; }
      .chip { font-size:12px; padding:2px 8px; border-radius:8px;
              background: var(--secondary-background-color); color: var(--secondary-text-color); }
      .strecke { margin-top:12px; border-top:1px solid var(--divider-color); padding-top:10px; }
      .leg { display:grid; grid-template-columns:48px 52px 1fr 52px 56px;
             align-items:center; gap:4px; padding:3px 0; font-size:13px; }
      .lz { color: var(--secondary-text-color); font-variant-numeric: tabular-nums; }
      .lp { font-weight:600; }
      .ll { position:relative; text-align:center; color: var(--secondary-text-color); font-size:11px; }
      .ll::before { content:""; position:absolute; left:0; right:0; top:50%;
                    border-top:1px dashed var(--divider-color); z-index:0; }
      .lf { position:relative; z-index:1; background: var(--ha-card-background, var(--card-background-color));
            padding:0 6px; }
      .fuss { margin-top:12px; padding-top:10px; font-size:13px;
              border-top:1px solid var(--divider-color); color: var(--secondary-text-color); }
      .fz { display:flex; align-items:center; gap:8px; padding:2px 0; }
      .fz ha-icon { --mdc-icon-size: 18px; color: var(--secondary-text-color); }
      .fz b { color: var(--primary-text-color); font-weight:600; }
      .leer { color: var(--secondary-text-color); }
      sup { font-size:9px; }
    </style>`;
  }
}

// Doppeltes Registrieren abfangen: Wird die Datei zweimal geladen (Ressource
// und Rueckfallweg), wuerde customElements.define sonst werfen - und die Karte
// bliebe als "Konfigurationsfehler" stehen.
if (!customElements.get("openairlog-card")) {
  customElements.define("openairlog-card", OpenAirLogCard);
}

window.customCards = window.customCards || [];
if (!window.customCards.some((k) => k.type === "openairlog-card")) {
  window.customCards.push({
    type: "openairlog-card",
    name: "OpenAirLog Dienst",
    description: "Zeigt den nächsten oder laufenden Umlauf mit allen Abschnitten.",
    preview: true,
  });
}
