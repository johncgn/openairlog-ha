"""Dienstplansymbole der Lufthansa - Vorbelegung fuer die Kategorien.

Grundlage ist die offizielle Symbolliste des Flugbetriebs (Stand 2026).
Sie umfasst rund 600 Kuerzel; die meisten gehoeren zu Familien mit klarem
Praefix (TR1..TR22, CCQ*, SB_*, REQ_*). Deshalb hier ZWEI Ebenen:

  1. EINZELCODES  - unregelmaessige Kuerzel, exakt getroffen
  2. PRAEFIXE     - Familien, der Reihe nach geprueft (laengster zuerst)

Alles hier ist nur ein VORSCHLAG. Jede Airline nutzt eigene Kuerzel, und auch
bei Lufthansa aendert sich die Liste - deshalb bleibt in den Optionen alles
ueberschreibbar. Wer nichts einstellt, faehrt mit diesen Werten schon richtig.

Nicht zugeordnete Codes gelten bewusst als DIENST: lieber einmal umsonst
losfahren als den Dienst verpassen.
"""
from __future__ import annotations

from .const import KAT_DIENST, KAT_FREI, KAT_SCHULUNG, KAT_STANDBY, KAT_WBT

# ---------------------------------------------------------------- Einzelcodes
EINZELCODES: dict[str, str] = {
    # --- frei, Urlaub, Ausgleich ---------------------------------------
    "=": KAT_FREI, "FREE": KAT_FREI, "FR": KAT_FREI, "FRS": KAT_FREI,
    "FTS": KAT_FREI, "FZ": KAT_FREI, "FM/Q": KAT_FREI, "FM54": KAT_FREI,
    "DX": KAT_FREI, "SX": KAT_FREI, "SY": KAT_FREI, "ZWK": KAT_FREI,
    "U": KAT_FREI, "U1": KAT_FREI, "ORTSTAG": KAT_FREI,
    "MOA": KAT_FREI, "FG": KAT_FREI,          # Fatigue-Meldung
    "DTMFF_V": KAT_FREI, "DTMFF_N": KAT_FREI,  # Ausgleich Mixed Fleet Flying
    "DTSFF_V": KAT_FREI, "DTSFF_N": KAT_FREI,
    # --- krank, Unfall, Schutzfristen ----------------------------------
    "K": KAT_FREI, "K0": KAT_FREI, "KO": KAT_FREI, "KD": KAT_FREI,
    "B": KAT_FREI, "B0": KAT_FREI, "T": KAT_FREI, "T0": KAT_FREI,
    "P": KAT_FREI, "DQ": KAT_FREI, "DQ_CC": KAT_FREI,
    "M": KAT_FREI, "Y": KAT_FREI, "Y_FIT": KAT_FREI,
    # --- Teilzeit, Freistellung ----------------------------------------
    "H": KAT_FREI, "HE": KAT_FREI, "HI": KAT_FREI, "HM": KAT_FREI,
    "HN": KAT_FREI, "H_28": KAT_FREI,
    "V": KAT_FREI, "VE": KAT_FREI, "VI": KAT_FREI, "VM": KAT_FREI,
    "VN": KAT_FREI, "V0": KAT_FREI,
    "W": KAT_FREI, "W1": KAT_FREI, "W2": KAT_FREI,
    "PK": KAT_FREI, "PL": KAT_FREI, "UF": KAT_FREI, "S9": KAT_FREI,
    "Q": KAT_FREI, "Q_CC": KAT_FREI, "Q_OPEN": KAT_FREI, "QLCAG": KAT_FREI,
    # --- Sonderurlaub, Kinderbetreuung ---------------------------------
    "D": KAT_FREI, "D_CC": KAT_FREI, "S": KAT_FREI, "S2": KAT_FREI,
    "S3": KAT_FREI, "S4": KAT_FREI, "S5": KAT_FREI, "S6B": KAT_FREI,
    "SL": KAT_FREI, "SL_IHK": KAT_FREI, "SQ": KAT_FREI, "SQ_CC": KAT_FREI,
    "O": KAT_FREI, "Z": KAT_FREI, "OUNFALL": KAT_FREI, "DO": KAT_FREI,
    "S_O": KAT_FREI, "DW": KAT_FREI, "DW_CC": KAT_FREI,
    "FS": KAT_FREI, "FS_CC": KAT_FREI,
    "V2": KAT_FREI, "V4": KAT_FREI, "V2/LCAG": KAT_FREI, "V4/LCAG": KAT_FREI,
    # --- Bereitschaft ---------------------------------------------------
    "SBA": KAT_STANDBY, "SBAO": KAT_STANDBY, "SCU": KAT_STANDBY,
    "SCX": KAT_STANDBY, "RES": KAT_STANDBY, "REP": KAT_STANDBY,
    "REII": KAT_STANDBY, "RB": KAT_STANDBY, "RCU": KAT_STANDBY,
    "RCX": KAT_STANDBY, "RPU": KAT_STANDBY, "RPX": KAT_STANDBY,
    "CD_AP": KAT_STANDBY,
    # --- Web Based Training: von zuhause, KEIN Weg zur Basis -----------
    "AVSEC": KAT_WBT, "AVSEC/N": KAT_WBT, "DB": KAT_WBT, "TKSEC": KAT_WBT,
    "LMHS": KAT_WBT, "LMHS_N": KAT_WBT,
    "TKGR": KAT_WBT, "TKKNO": KAT_WBT, "TKSST": KAT_WBT, "TKSFO": KAT_WBT,
    "TKACE": KAT_WBT, "TKEBT": KAT_WBT, "TK_F/ED": KAT_WBT,
    "TK_F/ED_P": KAT_WBT, "TKTLB1": KAT_WBT, "TKTLB2": KAT_WBT,
    "WBT_RNP": KAT_WBT, "WBT_SFO": KAT_WBT, "WBT_GR": KAT_WBT,
    "WBT_REC": KAT_WBT, "WBT_ALL": KAT_WBT, "WBT_EM": KAT_WBT,
    "WBTLOFT": KAT_WBT,
    # --- Praesenzschulung: Anfahrt noetig ------------------------------
    "EMCRM": KAT_SCHULUNG, "FCCRM": KAT_SCHULUNG, "SECCRM": KAT_SCHULUNG,
    "EM": KAT_SCHULUNG, "EH": KAT_SCHULUNG, "EH_P": KAT_SCHULUNG,
    "MOD": KAT_SCHULUNG, "MOD/N": KAT_SCHULUNG, "MOD2": KAT_SCHULUNG,
    "MOD2/N": KAT_SCHULUNG, "MOD_H": KAT_SCHULUNG,
    "QA": KAT_SCHULUNG, "D4": KAT_SCHULUNG, "DD": KAT_SCHULUNG,
    "SMP": KAT_SCHULUNG, "TK": KAT_SCHULUNG,
    "DTEU": KAT_SCHULUNG, "DT_LPR": KAT_SCHULUNG, "DT_WLCM": KAT_SCHULUNG,
    "DT_BBK": KAT_SCHULUNG, "DT_ASSB": KAT_SCHULUNG,
    "DTTRIIN": KAT_SCHULUNG, "DTTRILS": KAT_SCHULUNG,
    # --- Bodendienst / Buero (Standard, hier nur der Klarheit halber) --
    "DT": KAT_DIENST, "DA": KAT_DIENST, "DM": KAT_DIENST, "CD": KAT_DIENST,
    "EK": KAT_DIENST, "EK_/N": KAT_DIENST, "PR": KAT_DIENST,
    "MED": KAT_DIENST, "MED_P": KAT_DIENST, "AMV": KAT_DIENST,
    "AMV_P": KAT_DIENST, "DTMED": KAT_DIENST, "DTBEH": KAT_DIENST,
    "R": KAT_DIENST, "R_F": KAT_DIENST, "R_S": KAT_DIENST,
    "CA": KAT_DIENST, "CEFO": KAT_DIENST, "SAT": KAT_DIENST,
    "OA": KAT_DIENST, "E": KAT_DIENST,
}

# ------------------------------------------------------------------ Praefixe
# Reihenfolge zaehlt: der laengste Treffer gewinnt (wird beim Pruefen sortiert).
PRAEFIXE: tuple[tuple[str, str], ...] = (
    # Bereitschaft - die groesste Familie ueberhaupt
    ("SB_", KAT_STANDBY), ("RES_", KAT_STANDBY), ("RE12", KAT_STANDBY),
    ("RE13", KAT_STANDBY), ("RB_", KAT_STANDBY), ("RCU", KAT_STANDBY),
    ("RCX", KAT_STANDBY),
    # Krank / Unfall / Schutzfrist "ueber" einen freien Tag: K_OFF, KO_OT, ...
    ("KOX", KAT_FREI), ("KO_", KAT_FREI), ("K_", KAT_FREI),
    ("B_", KAT_FREI), ("T_", KAT_FREI), ("M_", KAT_FREI), ("Y_", KAT_FREI),
    # Freie Tage
    ("OFF", KAT_FREI), ("OF/", KAT_FREI), ("OF", KAT_FREI),
    ("FRN", KAT_FREI), ("FM54", KAT_FREI), ("-_FM54", KAT_FREI),
    # Web Based Training - alles "Placeholder for web based training"
    ("LMN_", KAT_WBT), ("WBT", KAT_WBT),
    # Praesenzseminare der Trainingsabteilung
    ("SEP_", KAT_SCHULUNG), ("TKCRM", KAT_SCHULUNG), ("TKC", KAT_SCHULUNG),
    ("TKS", KAT_SCHULUNG), ("TKL", KAT_SCHULUNG), ("TKI", KAT_SCHULUNG),
    ("TKO", KAT_SCHULUNG), ("TKP", KAT_SCHULUNG), ("TKR", KAT_SCHULUNG),
    ("TKT", KAT_SCHULUNG), ("TK_", KAT_SCHULUNG), ("TK3", KAT_SCHULUNG),
    ("DIF", KAT_SCHULUNG), ("DP_", KAT_SCHULUNG),
    # Bodendienst-Tage im Grundkurs und Buerotage
    ("DT", KAT_DIENST), ("DS_", KAT_DIENST), ("B1", KAT_DIENST),
    ("B2", KAT_DIENST), ("B3", KAT_DIENST), ("PV", KAT_DIENST),
)

# ------------------------------------------------------------------ Simulator
# Alles, was im Simulator stattfindet - dort gelten eigene Briefingzeiten
# (bei Lufthansa je eine Stunde davor und danach).
SIM_EINZELCODES: frozenset[str] = frozenset({
    "CHECK", "SKILL", "BXC", "SKILMPL", "SCREEN", "MANAG", "DFS",
    "LT", "TT", "TTC", "TTC_RNP", "TV", "FPT", "IPT", "FBS", "FBW",
    "BATT", "BLO", "BTFO", "BTSF", "BTT", "B7LT",
    "REF", "REF1", "REF2", "REF3", "KE1", "KE2", "KE_REF",
    "FEA", "AP_EI", "SIM_EI", "ASS_1", "ASS_2", "RH_CH", "RH_EI",
    "CRC_CH", "CRC_REF", "KA_REF", "FO_REF", "SFO", "SFOCH", "SFO_XC",
    "RNP_CH", "ZFTT", "ZFUP", "ZFAM_34", "FAM_78", "TKEBT-I",
    "ADDFPT", "ADDIPT", "ADDLINE", "ADDNL", "LT_BOG",
})

SIM_PRAEFIXE: tuple[str, ...] = (
    "TRI",       # Type Rating Instructor
    "CCQ",       # Cross Crew Qualification
    "CTR",       # Common Type Rating A330->A350
    "OCC",       # Operator Conversion Course (auch OCC1_78 fuer B787)
    "PEC",       # Pre Experience Course B74x -> B787
    "EBT",       # Evidence Based Training
    "REQ_",      # Requalification
    "CHK_",      # Proficiency Check je Muster
    "SKILL",     # Skill Tests
    "ZFTT", "ZFUP",
    "FFS", "LTFT",
    "L1_TT", "L2_TT", "L3_TT", "L4_TT", "LO_TT", "UPRT",
    "SFI3", "TTT_", "REF",
    "SFO_",      # SFO-Ausbildung im SIM
    "CC1", "CC2", "CC3", "CC4", "CC5", "CC6", "CC7", "CC8", "CC9", "CC10",
    "EI_",       # Special-Airport-Einweisungen im SIM
    "BW",        # Bundeswehr-Schulungen (FFS/FPT)
)


def kategorie_vorschlag(code: str) -> str | None:
    """Kategorie fuer einen Dienstcode - None, wenn nichts passt."""
    if not code:
        return None
    c = str(code).upper().strip()
    if c in EINZELCODES:
        return EINZELCODES[c]
    for praefix, kat in sorted(PRAEFIXE, key=lambda p: -len(p[0])):
        if c.startswith(praefix):
            return kat
    return None


def ist_simulator(code: str) -> bool:
    """Findet der Dienst im Simulator statt?

    Achtung bei "TR": Type Rating heisst TR1..TR22, aber TRAIN und TRANSPORT
    sind Bodentransport. Deshalb muss nach dem TR eine Ziffer folgen.
    """
    if not code:
        return False
    c = str(code).upper().strip()
    if c in SIM_EINZELCODES:
        return True
    if c.startswith("TR") and c[2:3].isdigit():
        return True
    return any(c.startswith(p) for p in SIM_PRAEFIXE)
