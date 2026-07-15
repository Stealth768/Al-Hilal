from django.test import TestCase

from .views import build_milestones_for_year


class EidVisibilityTests(TestCase):
    def test_eid_fitr_for_2026_moves_to_next_day_when_crescent_is_visible(self):
        milestones = build_milestones_for_year(2026)
        eid = next(item for item in milestones if item['name'] == 'Eid al-Fitr')

        self.assertEqual(eid['date'], '2026-03-21')
