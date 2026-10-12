"""The check for German character names (tools/check_wording.py)."""

import pathlib
import sys
import unittest

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent
                       / "tools"))
import check_wording as W                          # noqa: E402


class TheNamesOfTheApp(unittest.TestCase):

    def test_a_name_translated_by_hand_is_found(self):
        for wrong, right in (("Säufer", "Trunkenbold"),
                             ("Zimmermädchen", "Kammerzofe"),
                             ("Pit-Hag", "Grubenweib")):
            with self.subTest(wrong=wrong):
                found = W.check(f"Der {wrong} wacht auf.")
                self.assertEqual(found[0][:3], ("Fehler", 1, wrong))
                self.assertIn(right, found[0][3])

    def test_the_right_names_pass(self):
        self.assertEqual(W.check("Trunkenbold, Kammerzofe, Grubenweib, "
                                 "Hohepriesterin, General, Fischer."), [])

    def test_a_wrong_name_quoted_on_its_own_is_talked_about(self):
        self.assertEqual(W.check("Es heißt nicht „Säufer“."), [])

    def test_real_names_easy_to_mean_by_mistake_are_only_warned(self):
        kinds = {kind for kind, *_ in W.check("Die Hexe und der Jäger.")}
        self.assertEqual(kinds, {"Prüfen"})


if __name__ == "__main__":
    unittest.main()
