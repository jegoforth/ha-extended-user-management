"""Tests for pin.py, loaded standalone so this doesn't require a real
Home Assistant install: importing the custom_components package normally
would run __init__.py, which imports the real `homeassistant` package.
pin.py itself has no Home Assistant dependency at all, only a relative
import of const.py, so both are loaded directly by file path under a
minimal stub package registered in sys.modules.
"""
import importlib.util
import sys
import types
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PKG_DIR = ROOT / "custom_components" / "extended_user_management"
PKG_NAME = "custom_components.extended_user_management"


def _install_stub_package():
    if "custom_components" not in sys.modules:
        top = types.ModuleType("custom_components")
        top.__path__ = [str(ROOT / "custom_components")]
        sys.modules["custom_components"] = top
    if PKG_NAME not in sys.modules:
        pkg = types.ModuleType(PKG_NAME)
        pkg.__path__ = [str(PKG_DIR)]
        sys.modules[PKG_NAME] = pkg


def _load(filename: str):
    modname = f"{PKG_NAME}.{filename[:-3]}"
    if modname in sys.modules:
        return sys.modules[modname]
    spec = importlib.util.spec_from_file_location(modname, PKG_DIR / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[modname] = module
    spec.loader.exec_module(module)
    return module


_install_stub_package()
_load("const.py")
pin = _load("pin.py")


class PinTests(unittest.TestCase):
    def setUp(self):
        pin._failures.clear()

    def test_looks_like_pin(self):
        self.assertTrue(pin.looks_like_pin("1234"))
        self.assertTrue(pin.looks_like_pin("12345678"))
        self.assertFalse(pin.looks_like_pin("123"))
        self.assertFalse(pin.looks_like_pin("123456789"))
        self.assertFalse(pin.looks_like_pin("12a4"))

    def test_new_pin_record_rejects_invalid_pins(self):
        with self.assertRaises(ValueError):
            pin.new_pin_record("12")
        with self.assertRaises(ValueError):
            pin.new_pin_record("abcd")

    def test_correct_and_incorrect_verification(self):
        record = pin.new_pin_record("4471")
        self.assertTrue(pin.verify("person.shelley", "4471", record))
        pin._failures.clear()
        self.assertFalse(pin.verify("person.shelley", "0000", record))

    def test_missing_record_fails_closed(self):
        self.assertFalse(pin.verify("person.shelley", "1234", None))

    def test_each_record_uses_a_distinct_salt(self):
        first = pin.new_pin_record("1234")
        second = pin.new_pin_record("1234")
        self.assertNotEqual(first["salt"], second["salt"])
        self.assertNotEqual(first["hash"], second["hash"])

    def test_lockout_after_max_attempts(self):
        record = pin.new_pin_record("9999")
        now = 1000.0
        for _ in range(pin.MAX_PIN_ATTEMPTS):
            pin.verify("person.eric", "0000", record, now=now)
        self.assertTrue(pin.locked_out("person.eric", now=now))
        self.assertFalse(pin.verify("person.eric", "9999", record, now=now))
        later = now + pin.LOCKOUT_SECONDS + 1
        self.assertFalse(pin.locked_out("person.eric", now=later))
        self.assertTrue(pin.verify("person.eric", "9999", record, now=later))


if __name__ == "__main__":
    unittest.main()
