import unittest

from ml_orchestrator.utils.time import build_cron_expression


class TestTimeUtils(unittest.TestCase):
    def test_build_cron_expression_defaults(self) -> None:
        expected = "* * * * *"
        actual = build_cron_expression()
        self.assertEqual(actual, expected)

    def test_build_cron_expression_specific_minute_hour(self) -> None:
        expected = "30 3 * * *"
        actual = build_cron_expression(minute="30", hour="3")
        self.assertEqual(actual, expected)

    def test_build_cron_expression_specific_day_of_week(self) -> None:
        expected = "0 9 * * 1"
        actual = build_cron_expression(minute="0", hour="9", day_of_week="1")
        self.assertEqual(actual, expected)

    def test_build_cron_expression_step_minute(self) -> None:
        expected = "*/15 * * * *"
        actual = build_cron_expression(minute="*/15")
        self.assertEqual(actual, expected)

    def test_build_cron_expression_full_combination(self) -> None:
        expected = "0 12 15 6 3"
        actual = build_cron_expression(minute="0", hour="12", day_of_month="15", month="6", day_of_week="3")
        self.assertEqual(actual, expected)

    def test_build_cron_expression_range_and_list(self) -> None:
        expected = "0-59/2 8-10 * * MON,WED,FRI"
        actual = build_cron_expression(minute="0-59/2", hour="8-10", day_of_week="MON,WED,FRI")
        self.assertEqual(actual, expected)
