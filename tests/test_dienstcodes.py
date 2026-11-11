"""Simulator erkennen - aus der Lufthansa-Tabelle und aus den eigenen Codes."""
import pytest

from conftest import leg
from openairlog.dienstcodes import ist_simulator, kategorie_vorschlag


@pytest.mark.parametrize("code", ["TTC", "ttc", " TTC ", "TR1", "TR12", "FFS1", "CHK_A320", "EBT2"])
def test_lufthansa_tabelle_erkennt_simulator(code):
    assert ist_simulator(code)


@pytest.mark.parametrize("code", ["", None, "TRAIN", "TRANSPORT", "LH492", "OFF", "U"])
def test_kein_simulator(code):
    # TR ohne Ziffer ist Bodentransport, kein Type Rating
    assert not ist_simulator(code)


@pytest.mark.parametrize("code", ["SIM", "OPC", "LPC"])
def test_standard_simcodes_aus_den_einstellungen(coordinator, code):
    # SIM/OPC/LPC stehen nicht in der LH-Tabelle, sondern in der Standardliste
    k = coordinator()
    assert k._ist_sim({"code": code, "flugnummer": None}, k._codes("codes_simulator", ["SIM", "OPC", "LPC"]))


def test_simulator_im_flugbuch_als_flug_getarnt(coordinator):
    # SIM-Schichten stehen im Flugbuch als Flug: "TTC B748 748", EDDF->EDDF
    k = coordinator(profil={"base_airport": "EDDF"})
    u = k._umlaeufe([leg(None, "TTC B748 748", "EDDF", "EDDF", "2026-11-08T22:00", "2026-11-09T02:00")])
    assert u[0]["art"] == "simulator"


def test_unbekannter_code_ohne_vorschlag():
    assert kategorie_vorschlag("XYZ_GIBTSNICHT") is None
