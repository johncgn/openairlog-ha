"""Konstanten der OpenAirLog-Integration."""
from __future__ import annotations

from datetime import timedelta

DOMAIN = "openairlog"
BASIS_URL = "https://openairlog.de/api/v1"

CONF_API_KEY = "api_key"
CONF_HEIMWEG_MIN = "heimweg_minuten"
CONF_ANFAHRT_MIN = "anfahrt_minuten"
CONF_KATEGORIEN = "kategorien"
CONF_TAGE_VORAUS = "tage_voraus"
CONF_TAGE_RUECK = "tage_rueckblick"
CONF_BRIEFING_MIN = "briefing_minuten"
CONF_DEBRIEFING_MIN = "debriefing_minuten"
CONF_BRIEFING_SIM_MIN = "briefing_sim_minuten"
CONF_DEBRIEFING_SIM_MIN = "debriefing_sim_minuten"
CONF_PUFFER_MIN = "puffer_minuten"
CONF_CODES_SIM = "codes_simulator"
CONF_CODES_WBT = "codes_wbt"
CONF_LH_TABELLE = "lufthansa_tabelle"
CONF_TURNAROUND_MIN = "turnaround_minuten"
CONF_BASIS = "basis_flughafen"
CONF_LH_ID = "lh_client_id"
CONF_LH_SECRET = "lh_client_secret"
CONF_LH_FENSTER = "lh_fenster_stunden"

# OpenAirLog ist Freeware - wir gehen bewusst sparsam mit dem Server um.
# Alle 30 Minuten reicht voellig: Dienstplaene aendern sich nicht im Minutentakt.
# Ergibt rund 48 Abrufe der Dienste pro Tag, dazu die Statistik alle 2 Stunden
# und das Profil genau einmal je Neustart.
UPDATE_INTERVALL = timedelta(minutes=30)
# Statistik nur bei jedem n-ten Durchlauf holen (aendert sich selten).
STATISTIK_JEDER_NTE = 4

STANDARD_TAGE_VORAUS = 60
STANDARD_TAGE_RUECK = 7

# Briefing vor Abflug - je nach Flotte unterschiedlich, deshalb einstellbar.
STANDARD_BRIEFING_MIN = 0
STANDARD_DEBRIEFING_MIN = 30
# Simulator laeuft anders als ein Flug: Vor- UND Nachbereitung sind laenger.
STANDARD_BRIEFING_SIM_MIN = 60
STANDARD_DEBRIEFING_SIM_MIN = 60
# Persoenlicher Sicherheitspuffer: So lange VOR dem Briefing moechte man da
# sein. Zaehlt nicht zum Dienst, verschiebt aber die Losfahrzeit nach vorn -
# und gilt auch fuer Bodendienste und Schulungen, wo es kein Briefing gibt.
STANDARD_PUFFER_MIN = 15
# Kehrt man zwischendurch zur Basis zurueck, gehoert der naechste Flug nur dann
# zum selben Dienst, wenn die Standzeit darunter liegt (Kurzstrecken-Umlauf).
STANDARD_TURNAROUND_MIN = 180

# Das Profil fuehrt die Basis meist als ICAO-Code (EDDF), der Dienstplan
# schreibt die Flughaefen dagegen oft als IATA-Code (FRA). Ohne Abgleich gilt
# man nie als "zuhause", und alle Dienste verschmelzen zu einem Umlauf.
# Liste der gaengigen Crew-Basen; Fehlendes laesst sich in den Optionen als
# "FRA, EDDF" eintragen.
ICAO_ZU_IATA = {
    "EDDF": "FRA", "EDDM": "MUC", "EDDL": "DUS", "EDDH": "HAM", "EDDB": "BER",
    "EDDK": "CGN", "EDDS": "STR", "EDDN": "NUE", "EDDV": "HAJ", "EDDP": "LEJ",
    "EDDW": "BRE", "LSZH": "ZRH", "LSGG": "GVA", "LOWW": "VIE", "EBBR": "BRU",
    "EHAM": "AMS", "EGLL": "LHR", "LFPG": "CDG", "LIRF": "FCO", "LEMD": "MAD",
    "EKCH": "CPH", "ESSA": "ARN", "ENGM": "OSL", "EFHK": "HEL", "EPWA": "WAW",
    "LKPR": "PRG", "LHBP": "BUD", "EIDW": "DUB", "LPPT": "LIS", "LEBL": "BCN",
}

# Die Lufthansa-API kennt nur 5 Tage voraus und hat ein begrenztes Kontingent.
# Deshalb wird nur in einem Fenster um den Flug herum abgefragt.
STANDARD_LH_FENSTER_H = 24

# --- Kategorien -----------------------------------------------------------
# "dienst"   = Anwesenheit an der Basis noetig -> loest Anfahrt/Heizung aus
# "standby"  = Bereitschaft, kann zum Dienst werden
# "schulung" = Praesenztermin (Groundcourse, CRM) -> Weg zur Basis noetig
# "wbt"      = Web Based Training von zuhause -> KEIN Weg, kein Puffer
# "frei"     = kein Dienst
KAT_DIENST = "dienst"
KAT_STANDBY = "standby"
KAT_SCHULUNG = "schulung"
KAT_WBT = "wbt"
KAT_FREI = "frei"

# Ein Eintrag OHNE duty_code, aber MIT Flugnummer, ist ein echter Flug.
KAT_FLUG = KAT_DIENST

# Vorbelegung fuer Lufthansa-artige Dienstcodes. Bewusst als VORSCHLAG:
# jede Airline nutzt eigene Kuerzel, deshalb in den Optionen aenderbar.
STANDARD_KATEGORIEN: dict[str, str] = {
    "U": KAT_FREI,          # Urlaub
    "U1": KAT_FREI,
    "OFF": KAT_FREI,
    "H": KAT_FREI,
    "ORTSTAG": KAT_FREI,
    "Y": KAT_FREI,
    "SIM": KAT_DIENST,      # Simulator
    "DT_GC": KAT_DIENST,    # Dienst am Boden
    "DTMFF_V": KAT_DIENST,
    "SB_S_LR_FF": KAT_STANDBY,
    "WBT_RNP": KAT_WBT,     # Web Based Training - von zuhause
    "AVSEC": KAT_WBT,
    "FCCRM": KAT_SCHULUNG,  # Praesenzschulung - Anfahrt noetig
    "EMCRM": KAT_SCHULUNG,
}

# --- Dienstarten ----------------------------------------------------------
# Bestimmen, welche Briefingzeiten gelten. Nicht mit den Kategorien oben
# verwechseln: die sagen, OB man raus muss - die Art sagt, WIE FRUEH.
ART_FLUG = "flug"          # Briefing vor Abflug, kurzes Debriefing danach
ART_SIM = "simulator"      # laengere Vor- und Nachbereitung
ART_BODEN = "boden"        # Groundcourse, CRM, eCRM: kein Briefing, nur Puffer

# Vorschlag fuer Simulator-Kuerzel - in den Optionen anpassbar.
STANDARD_CODES_SIM = ["SIM", "OPC", "LPC", "LOFT", "FFS", "SIM_FFS"]

# Web Based Training laeuft am eigenen Rechner - kein Weg, kein Puffer.
# Alles, was Praesenz verlangt (Groundcourse, CRM), gehoert NICHT hierher.
# Die mitgelieferte Lufthansa-Symbolliste standardmaessig nutzen. Wer bei einer
# anderen Airline fliegt, schaltet sie ab und traegt eigene Codes ein.
STANDARD_LH_TABELLE = True

STANDARD_CODES_WBT = ["WBT_RNP", "AVSEC", "WBT", "ELEARNING"]
