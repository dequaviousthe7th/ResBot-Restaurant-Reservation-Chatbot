"""
Unit Tests - Restaurant Reservation Chatbot
Khaled Jamal W2018556
6COSC023W Final Year Project
"""

import sys
import unittest
import os
import tempfile
from unittest.mock import MagicMock, patch
from datetime import datetime, timedelta

# Stub tkinter so tests run without a graphical display
sys.modules['tkinter'] = MagicMock()
sys.modules['tkinter.scrolledtext'] = MagicMock()
sys.modules['tkinter.messagebox'] = MagicMock()

from chatbot import ReservationDatabase, RestaurantConfig, ChatBot, State


def future_date(days=30):
    """Return a date string DD/MM/YYYY for N days from today."""
    return (datetime.now() + timedelta(days=days)).strftime('%d/%m/%Y')


def past_date(days=30):
    """Return a date string DD/MM/YYYY for N days in the past."""
    return (datetime.now() - timedelta(days=days)).strftime('%d/%m/%Y')


class TestReservationDatabase(unittest.TestCase):

    def setUp(self):
        self.tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        self.tmp.close()
        os.unlink(self.tmp.name)
        self.db = ReservationDatabase(self.tmp.name)

    def tearDown(self):
        if os.path.exists(self.tmp.name):
            os.unlink(self.tmp.name)

    def test_starts_empty(self):
        self.assertEqual(self.db.get_all(), [])

    def test_add_reservation_returns_id(self):
        res_id = self.db.add_reservation("Alice", 2, future_date(), "19:00")
        self.assertEqual(res_id, 1001)

    def test_add_reservation_increments_id(self):
        id1 = self.db.add_reservation("Alice", 2, future_date(), "19:00")
        id2 = self.db.add_reservation("Bob", 4, future_date(60), "20:00")
        self.assertEqual(id2, id1 + 1)

    def test_get_all_returns_bookings(self):
        self.db.add_reservation("Alice", 2, future_date(), "19:00")
        self.db.add_reservation("Bob", 4, future_date(60), "20:00")
        self.assertEqual(len(self.db.get_all()), 2)

    def test_cancel_reservation_removes_it(self):
        res_id = self.db.add_reservation("Alice", 2, future_date(), "19:00")
        cancelled = self.db.cancel_reservation(res_id)
        self.assertEqual(cancelled['name'], "Alice")
        self.assertEqual(self.db.get_all(), [])

    def test_cancel_nonexistent_returns_none(self):
        result = self.db.cancel_reservation(9999)
        self.assertIsNone(result)

    def test_check_availability_empty_date(self):
        info = self.db.check_availability("01/05/2030")
        self.assertEqual(info['count'], 0)
        self.assertEqual(info['total_guests'], 0)

    def test_check_availability_counts_correctly(self):
        date = future_date()
        self.db.add_reservation("Alice", 3, date, "18:00")
        self.db.add_reservation("Bob", 4, date, "19:00")
        info = self.db.check_availability(date)
        self.assertEqual(info['count'], 2)
        self.assertEqual(info['total_guests'], 7)

    def test_check_availability_only_counts_matching_date(self):
        self.db.add_reservation("Alice", 3, future_date(10), "18:00")
        self.db.add_reservation("Bob", 4, future_date(20), "19:00")
        info = self.db.check_availability(future_date(10))
        self.assertEqual(info['count'], 1)

    def test_data_persists_to_file(self):
        self.db.add_reservation("Alice", 2, future_date(), "19:00")
        db2 = ReservationDatabase(self.tmp.name)
        self.assertEqual(len(db2.get_all()), 1)
        self.assertEqual(db2.get_all()[0]['name'], "Alice")


class MockConfig:
    """Minimal config for ChatBot tests without file I/O."""
    name = "Test Restaurant"
    opening_time = "11:00"
    closing_time = "22:00"
    max_capacity = 50


class TestChatBotCleanName(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        tmp.close()
        os.unlink(tmp.name)
        self.db = ReservationDatabase(tmp.name)
        self.tmp_name = tmp.name
        self.bot = ChatBot(self.db, MockConfig())

    def tearDown(self):
        if os.path.exists(self.tmp_name):
            os.unlink(self.tmp_name)

    def test_plain_name(self):
        self.assertEqual(self.bot.clean_name("john smith"), "John Smith")

    def test_strips_my_name_is(self):
        self.assertEqual(self.bot.clean_name("my name is alice"), "Alice")

    def test_strips_for_prefix(self):
        self.assertEqual(self.bot.clean_name("for bob"), "Bob")

    def test_strips_please_suffix(self):
        self.assertEqual(self.bot.clean_name("Charlie please"), "Charlie")

    def test_strips_under_the_name_of(self):
        self.assertEqual(self.bot.clean_name("under the name of Diana"), "Diana")

    def test_title_case(self):
        self.assertEqual(self.bot.clean_name("EDWARD JONES"), "Edward Jones")

    def test_empty_after_strip_returns_empty(self):
        # Whitespace-only input: strip leaves "", .title() also ""
        self.assertEqual(self.bot.clean_name("  "), "")


class TestChatBotCleanDate(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        tmp.close()
        os.unlink(tmp.name)
        self.db = ReservationDatabase(tmp.name)
        self.tmp_name = tmp.name
        self.bot = ChatBot(self.db, MockConfig())

    def tearDown(self):
        if os.path.exists(self.tmp_name):
            os.unlink(self.tmp_name)

    def test_valid_future_date(self):
        fd = future_date(30)
        self.assertEqual(self.bot.clean_date(fd), fd)

    def test_past_date_returns_past(self):
        self.assertEqual(self.bot.clean_date(past_date(30)), 'past')

    def test_invalid_format_returns_none(self):
        self.assertIsNone(self.bot.clean_date("not a date"))

    def test_wrong_format_returns_none(self):
        self.assertIsNone(self.bot.clean_date("2030-12-01"))

    def test_space_separated_numbers(self):
        fd = future_date(30)
        parts = fd.split('/')
        spaced = f"{parts[0]} {parts[1]} {parts[2]}"
        self.assertEqual(self.bot.clean_date(spaced), fd)

    def test_two_digit_year(self):
        result = self.bot.clean_date("01 06 30")
        self.assertEqual(result, "01/06/2030")

    def test_invalid_day_month(self):
        self.assertIsNone(self.bot.clean_date("99/99/2030"))


class TestChatBotCleanTime(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        tmp.close()
        os.unlink(tmp.name)
        self.db = ReservationDatabase(tmp.name)
        self.tmp_name = tmp.name
        self.bot = ChatBot(self.db, MockConfig())

    def tearDown(self):
        if os.path.exists(self.tmp_name):
            os.unlink(self.tmp_name)

    def test_24hr_format(self):
        self.assertEqual(self.bot.clean_time("19:00"), "19:00")

    def test_12hr_pm(self):
        self.assertEqual(self.bot.clean_time("7pm"), "19:00")

    def test_12hr_am(self):
        self.assertEqual(self.bot.clean_time("11am"), "11:00")

    def test_with_at_prefix(self):
        self.assertEqual(self.bot.clean_time("at 7pm"), "19:00")

    def test_pm_with_minutes(self):
        self.assertEqual(self.bot.clean_time("7:30pm"), "19:30")

    def test_invalid_returns_none(self):
        self.assertIsNone(self.bot.clean_time("teatime"))

    def test_am_pm_with_dots(self):
        self.assertEqual(self.bot.clean_time("7p.m."), "19:00")


class TestChatBotGetNumber(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        tmp.close()
        os.unlink(tmp.name)
        self.db = ReservationDatabase(tmp.name)
        self.tmp_name = tmp.name
        self.bot = ChatBot(self.db, MockConfig())

    def tearDown(self):
        if os.path.exists(self.tmp_name):
            os.unlink(self.tmp_name)

    def test_digit(self):
        self.assertEqual(self.bot.get_number("4"), 4)

    def test_word_two(self):
        self.assertEqual(self.bot.get_number("two"), 2)

    def test_word_in_sentence(self):
        self.assertEqual(self.bot.get_number("there will be three of us"), 3)

    def test_digit_in_sentence(self):
        self.assertEqual(self.bot.get_number("table for 6 please"), 6)

    def test_invalid_returns_none(self):
        self.assertIsNone(self.bot.get_number("some people"))

    def test_a_returns_one(self):
        self.assertEqual(self.bot.get_number("a"), 1)


class TestChatBotProcess(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        tmp.close()
        os.unlink(tmp.name)
        self.db = ReservationDatabase(tmp.name)
        self.tmp_name = tmp.name
        self.bot = ChatBot(self.db, MockConfig())

    def tearDown(self):
        if os.path.exists(self.tmp_name):
            os.unlink(self.tmp_name)

    def test_empty_input(self):
        response = self.bot.process("")
        self.assertIn("Please type something", response)

    def test_whitespace_only(self):
        response = self.bot.process("   ")
        self.assertIn("Please type something", response)

    def test_book_intent(self):
        response = self.bot.process("book")
        self.assertEqual(self.bot.state, State.BOOKING_NAME)

    def test_cancel_intent_from_idle(self):
        response = self.bot.process("cancel")
        self.assertEqual(self.bot.state, State.CANCEL_ID)

    def test_check_intent(self):
        response = self.bot.process("check")
        self.assertEqual(self.bot.state, State.CHECK_DATE)

    def test_help_intent(self):
        response = self.bot.process("help")
        self.assertIn("Commands", response)

    def test_unknown_input(self):
        response = self.bot.process("xyzzy")
        self.assertIn("didn't get that", response)

    def test_mid_flow_cancel_resets_state(self):
        self.bot.process("book")
        self.assertEqual(self.bot.state, State.BOOKING_NAME)
        response = self.bot.process("cancel")
        self.assertEqual(self.bot.state, State.IDLE)
        self.assertIn("starting over", response)

    def test_mid_flow_quit_resets_state(self):
        self.bot.process("book")
        response = self.bot.process("quit")
        self.assertEqual(self.bot.state, State.IDLE)

    def test_mid_flow_start_over_resets(self):
        self.bot.process("book")
        response = self.bot.process("start over")
        self.assertEqual(self.bot.state, State.IDLE)

    def test_help_during_flow_preserves_state(self):
        self.bot.process("book")
        self.bot.process("Alice")
        self.assertEqual(self.bot.state, State.BOOKING_GUESTS)
        response = self.bot.process("help")
        self.assertEqual(self.bot.state, State.BOOKING_GUESTS)
        self.assertIn("Commands", response)

    def test_book_during_booking_asks_restart(self):
        self.bot.process("book")
        response = self.bot.process("book")
        self.assertIn("already making a booking", response)
        self.assertTrue(self.bot._asked_restart)

    def test_yes_after_restart_prompt_restarts(self):
        self.bot.process("book")
        self.bot.process("book")
        self.bot.process("yes")
        self.assertEqual(self.bot.state, State.BOOKING_NAME)
        self.assertFalse(self.bot._asked_restart)

    def test_no_after_restart_prompt_returns_hint(self):
        self.bot.process("book")
        self.bot.process("book")
        response = self.bot.process("no")
        self.assertFalse(self.bot._asked_restart)


class TestChatBotBookingFlow(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        tmp.close()
        os.unlink(tmp.name)
        self.db = ReservationDatabase(tmp.name)
        self.tmp_name = tmp.name
        self.bot = ChatBot(self.db, MockConfig())

    def tearDown(self):
        if os.path.exists(self.tmp_name):
            os.unlink(self.tmp_name)

    def test_full_happy_path(self):
        self.bot.process("book")
        self.assertEqual(self.bot.state, State.BOOKING_NAME)

        self.bot.process("Alice")
        self.assertEqual(self.bot.state, State.BOOKING_GUESTS)
        self.assertEqual(self.bot.booking_data['name'], "Alice")

        self.bot.process("4")
        self.assertEqual(self.bot.state, State.BOOKING_DATE)
        self.assertEqual(self.bot.booking_data['guests'], 4)

        self.bot.process(future_date(30))
        self.assertEqual(self.bot.state, State.BOOKING_TIME)

        response = self.bot.process("19:00")
        self.assertEqual(self.bot.state, State.IDLE)
        self.assertIn("Booking confirmed", response)
        self.assertIn("#", response)
        self.assertEqual(len(self.db.get_all()), 1)

    def test_empty_name_reprompts(self):
        # process() catches whitespace before handle_state; state stays in BOOKING_NAME
        self.bot.process("book")
        response = self.bot.process("   ")
        self.assertEqual(self.bot.state, State.BOOKING_NAME)
        self.assertIn("type something", response.lower())

    def test_past_date_reprompts(self):
        self.bot.process("book")
        self.bot.process("Alice")
        self.bot.process("2")
        response = self.bot.process(past_date(5))
        self.assertEqual(self.bot.state, State.BOOKING_DATE)
        self.assertIn("already passed", response)

    def test_invalid_guest_count_reprompts(self):
        self.bot.process("book")
        self.bot.process("Alice")
        response = self.bot.process("25")
        self.assertEqual(self.bot.state, State.BOOKING_GUESTS)
        self.assertIn("between 1 and 20", response)

    def test_outside_hours_reprompts(self):
        self.bot.process("book")
        self.bot.process("Alice")
        self.bot.process("2")
        self.bot.process(future_date(30))
        response = self.bot.process("03:00")
        self.assertEqual(self.bot.state, State.BOOKING_TIME)
        self.assertIn("only open", response)

    def test_capacity_exceeded_blocks_booking(self):
        # Fill up capacity
        date = future_date(30)
        self.db.add_reservation("Large Group", 50, date, "18:00")

        self.bot.process("book")
        self.bot.process("Alice")
        self.bot.process("2")
        self.bot.process(date)
        response = self.bot.process("19:00")
        self.assertEqual(self.bot.state, State.IDLE)
        self.assertIn("capacity", response.lower())
        # The large group booking is still there; Alice was not added
        self.assertEqual(len(self.db.get_all()), 1)


class TestChatBotCancelFlow(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        tmp.close()
        os.unlink(tmp.name)
        self.db = ReservationDatabase(tmp.name)
        self.tmp_name = tmp.name
        self.bot = ChatBot(self.db, MockConfig())

    def tearDown(self):
        if os.path.exists(self.tmp_name):
            os.unlink(self.tmp_name)

    def test_cancel_existing_booking(self):
        res_id = self.db.add_reservation("Alice", 2, future_date(), "19:00")
        self.bot.process("cancel")
        response = self.bot.process(str(res_id))
        self.assertIn("Cancelled", response)
        self.assertEqual(self.bot.state, State.IDLE)

    def test_cancel_nonexistent_booking(self):
        self.bot.process("cancel")
        response = self.bot.process("9999")
        self.assertIn("Couldn't find", response)
        self.assertEqual(self.bot.state, State.IDLE)

    def test_cancel_invalid_input_reprompts(self):
        self.bot.process("cancel")
        response = self.bot.process("not a number")
        self.assertEqual(self.bot.state, State.CANCEL_ID)
        self.assertIn("reference number", response)


class TestChatBotCheckFlow(unittest.TestCase):

    def setUp(self):
        tmp = tempfile.NamedTemporaryFile(suffix='.json', delete=False)
        tmp.close()
        os.unlink(tmp.name)
        self.db = ReservationDatabase(tmp.name)
        self.tmp_name = tmp.name
        self.bot = ChatBot(self.db, MockConfig())

    def tearDown(self):
        if os.path.exists(self.tmp_name):
            os.unlink(self.tmp_name)

    def test_check_empty_date(self):
        self.bot.process("check")
        response = self.bot.process(future_date(60))
        self.assertIn("No bookings", response)
        self.assertEqual(self.bot.state, State.IDLE)

    def test_check_date_with_bookings(self):
        date = future_date(60)
        self.db.add_reservation("Alice", 3, date, "18:00")
        self.bot.process("check")
        response = self.bot.process(date)
        self.assertIn("1 bookings", response)
        self.assertIn("3 guests", response)


if __name__ == '__main__':
    unittest.main(verbosity=2)
