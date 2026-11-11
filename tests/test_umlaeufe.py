"""Umlaufbildung: wann gehoeren Dienste zusammen, wann nicht."""
from conftest import leg


def test_icao_basis_mit_iata_plan_ergibt_vier_umlaeufe(coordinator, dienstplan_november):
    # Profil kennt EDDF, der Plan schreibt FRA - frueher ein Block ueber vier Wochen
    k = coordinator(profil={"base_airport": "EDDF"})
    u = k._umlaeufe(dienstplan_november)
    assert [x["stationen"] for x in u] == [
        ["FRA", "FRA"], ["FRA", "YVR", "FRA"], ["FRA", "HYD", "FRA"], ["FRA", "CPT", "FRA"]]


def test_simulator_steht_allein_und_ist_als_sim_erkannt(coordinator, dienstplan_november):
    u = coordinator(profil={"base_airport": "EDDF"})._umlaeufe(dienstplan_november)
    assert u[0]["art"] == "simulator"
    assert u[0]["anzahl_legs"] == 1


def test_rueckkehr_vancouver_am_freitag(coordinator, dienstplan_november):
    u = coordinator(profil={"base_airport": "EDDF"})._umlaeufe(dienstplan_november)
    assert u[1]["ankunft"].date().isoformat() == "2026-11-13"
    assert u[1]["mehrtaegig"] is True


def test_option_mit_mehreren_codes(coordinator, dienstplan_november):
    k = coordinator(optionen={"basis_flughafen": "fra, eddf"})
    assert len(k._umlaeufe(dienstplan_november)) == 4


def test_option_hat_vorrang_vor_profil(coordinator, dienstplan_november):
    # Profil sagt Muenchen, Option sagt Frankfurt - die Option gilt
    k = coordinator(optionen={"basis_flughafen": "FRA"}, profil={"base_airport": "EDDM"})
    assert len(k._umlaeufe(dienstplan_november)) == 4


def test_unbekannte_basis_verbindet_alles(coordinator, dienstplan_november):
    # Wer nie an der Basis ist, ist durchgehend unterwegs - erwartetes Verhalten
    k = coordinator(optionen={"basis_flughafen": "XYZ"})
    assert len(k._umlaeufe(dienstplan_november)) == 1


def test_kurzstrecken_tag_bleibt_ein_umlauf(coordinator):
    # Zweimal FRA-MUC-FRA mit 90 min Standzeit an der Basis: ein Dienst
    plan = [
        leg(None, "LH100", "FRA", "MUC", "2026-11-20T06:00", "2026-11-20T07:00"),
        leg(None, "LH101", "MUC", "FRA", "2026-11-20T08:00", "2026-11-20T09:00"),
        leg(None, "LH102", "FRA", "MUC", "2026-11-20T10:30", "2026-11-20T11:30"),
        leg(None, "LH103", "MUC", "FRA", "2026-11-20T12:30", "2026-11-20T13:30"),
    ]
    u = coordinator(profil={"base_airport": "EDDF"})._umlaeufe(plan)
    assert len(u) == 1 and u[0]["anzahl_legs"] == 4


def test_standzeit_ueber_grenze_trennt(coordinator):
    plan = [
        leg(None, "LH100", "FRA", "MUC", "2026-11-20T06:00", "2026-11-20T07:00"),
        leg(None, "LH101", "MUC", "FRA", "2026-11-20T08:00", "2026-11-20T09:00"),
        leg(None, "LH102", "FRA", "MUC", "2026-11-20T13:00", "2026-11-20T14:00"),
    ]
    k = coordinator(profil={"base_airport": "EDDF"}, optionen={"turnaround_minuten": 180})
    assert len(k._umlaeufe(plan)) == 2


def test_web_based_training_loest_keinen_umlauf_aus(coordinator):
    plan = [leg("WBT_RNP", None, None, None, "2026-11-20T08:00", "2026-11-20T10:00",
                kategorie="wbt")]
    assert coordinator(profil={"base_airport": "EDDF"})._umlaeufe(plan) == []


def test_briefing_nur_vor_echten_fluegen(coordinator):
    k = coordinator(profil={"base_airport": "EDDF"}, optionen={"briefing_minuten": 110})
    flug = k._umlaeufe([leg(None, "LH492", "FRA", "YVR", "2026-11-10T09:40", "2026-11-10T19:45"),
                        leg(None, "LH493", "YVR", "FRA", "2026-11-12T21:25", "2026-11-13T07:10")])[0]
    assert (flug["abflug"] - flug["beginn"]).total_seconds() / 60 == 110
    boden = k._umlaeufe([leg("DT_GC", None, None, None, "2026-11-20T08:00", "2026-11-20T16:00")])[0]
    assert boden["art"] == "boden" and boden["beginn"] == boden["abflug"]


def test_basis_codes(coordinator):
    k = coordinator()
    assert k._basis_codes("EDDF") == {"EDDF", "FRA"}
    assert k._basis_codes("muc") == {"MUC", "EDDM"}
    assert k._basis_codes("FRA; XYZ") == {"FRA", "EDDF", "XYZ"}
    assert k._basis_codes("") == set()
