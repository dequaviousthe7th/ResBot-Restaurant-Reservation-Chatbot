"""
ResBot — Voice-Enabled Restaurant Reservation Chatbot
Khaled Jamal W2018556
6COSC023W Final Year Project — University of Westminster
"""

import tkinter as tk
from tkinter import scrolledtext, messagebox
import json
import os
import re
import threading
from datetime import datetime

# Voice imports
try:
    import speech_recognition as sr
    SPEECH_AVAILABLE = True
except:
    SPEECH_AVAILABLE = False

try:
    import pyttsx3
    TTS_AVAILABLE = True
except:
    TTS_AVAILABLE = False

CANCEL_PHRASES = {
    'cancel', 'go back', 'start over', 'reset', 'quit',
    'stop', 'exit', 'nevermind', 'never mind', 'abort'
}


class ReservationDatabase:
    def __init__(self, filename='reservations.json'):
        self.filename = filename
        self.data = self.load()

    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    return json.load(f)
            except:
                return {"reservations": [], "next_id": 1001}
        return {"reservations": [], "next_id": 1001}

    def save(self):
        with open(self.filename, 'w') as f:
            json.dump(self.data, f, indent=2)

    def add_reservation(self, name, guests, date, time):
        res_id = self.data["next_id"]
        booking = {
            "id": res_id,
            "name": name,
            "guests": guests,
            "date": date,
            "time": time,
            "created_at": datetime.now().isoformat()
        }
        self.data["reservations"].append(booking)
        self.data["next_id"] += 1
        self.save()
        return res_id

    def cancel_reservation(self, res_id):
        for i, res in enumerate(self.data["reservations"]):
            if res["id"] == res_id:
                cancelled = self.data["reservations"].pop(i)
                self.save()
                return cancelled
        return None

    def check_availability(self, date):
        bookings = [r for r in self.data["reservations"] if r["date"] == date]
        total = sum(r["guests"] for r in bookings)
        return {"count": len(bookings), "total_guests": total, "bookings": bookings}

    def get_all(self):
        return self.data["reservations"]


class RestaurantConfig:
    def __init__(self, filename='config.json'):
        self.filename = filename
        self.config = self.load()

    def load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    return json.load(f)
            except:
                pass
        default = {
            "restaurant": {
                "name": "The Olive Garden",
                "opening_time": "11:00",
                "closing_time": "22:00",
                "max_capacity": 50,
                "setup_complete": False,
                "tables": []
            }
        }
        with open(self.filename, 'w') as f:
            json.dump(default, f, indent=2)
        return default

    def reload(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r') as f:
                    self.config = json.load(f)
            except:
                pass

    def is_setup_complete(self):
        return self.config["restaurant"].get("setup_complete", False)

    @property
    def name(self):
        return self.config["restaurant"]["name"]

    @property
    def opening_time(self):
        return self.config["restaurant"]["opening_time"]

    @property
    def closing_time(self):
        return self.config["restaurant"]["closing_time"]

    @property
    def max_capacity(self):
        return self.config["restaurant"].get("max_capacity", 50)

    @property
    def tables(self):
        return self.config["restaurant"].get("tables", [])


class SetupScreen:
    DEFAULT_TABLES = [
        {"id": 1, "seats": 2}, {"id": 2, "seats": 2},
        {"id": 3, "seats": 4}, {"id": 4, "seats": 4}, {"id": 5, "seats": 4},
        {"id": 6, "seats": 6}, {"id": 7, "seats": 6}, {"id": 8, "seats": 6},
        {"id": 9, "seats": 8}, {"id": 10, "seats": 8},
    ]

    def __init__(self, parent, config):
        self.config = config
        self.completed = False
        self.table_rows = []

        self.win = tk.Toplevel(parent)
        self.win.title("Restaurant Setup")
        self.win.geometry("500x600")
        self.win.configure(bg='#f5f5f5')
        self.win.grab_set()
        self.win.resizable(False, True)

        self._build_ui()
        self._load_existing()

    def _build_ui(self):
        tk.Label(self.win, text="Restaurant Setup", font=('Arial', 14, 'bold'),
                 bg='#34495e', fg='white', pady=10).pack(fill=tk.X)
        tk.Label(self.win, text="Configure your restaurant before using the chatbot",
                 font=('Arial', 9), bg='#f5f5f5', fg='#7f8c8d', pady=4).pack()

        form = tk.Frame(self.win, bg='#f5f5f5', padx=16, pady=8)
        form.pack(fill=tk.X)

        tk.Label(form, text="Restaurant Name:", bg='#f5f5f5', font=('Arial', 10)).grid(
            row=0, column=0, sticky='w', pady=4)
        self.name_var = tk.StringVar()
        tk.Entry(form, textvariable=self.name_var, font=('Arial', 10), width=28).grid(
            row=0, column=1, sticky='ew', padx=(8, 0))

        tk.Label(form, text="Opening Time (HH:MM):", bg='#f5f5f5', font=('Arial', 10)).grid(
            row=1, column=0, sticky='w', pady=4)
        self.open_var = tk.StringVar()
        tk.Entry(form, textvariable=self.open_var, font=('Arial', 10), width=10).grid(
            row=1, column=1, sticky='w', padx=(8, 0))

        tk.Label(form, text="Closing Time (HH:MM):", bg='#f5f5f5', font=('Arial', 10)).grid(
            row=2, column=0, sticky='w', pady=4)
        self.close_var = tk.StringVar()
        tk.Entry(form, textvariable=self.close_var, font=('Arial', 10), width=10).grid(
            row=2, column=1, sticky='w', padx=(8, 0))

        form.columnconfigure(1, weight=1)

        tk.Label(self.win, text="Tables", font=('Arial', 11, 'bold'),
                 bg='#f5f5f5', fg='#2c3e50').pack(anchor='w', padx=16, pady=(8, 0))

        container = tk.Frame(self.win, bg='#f5f5f5')
        container.pack(fill=tk.BOTH, expand=True, padx=16, pady=4)

        self.canvas = tk.Canvas(container, bg='#f5f5f5', highlightthickness=0)
        scrollbar = tk.Scrollbar(container, orient='vertical', command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.table_frame = tk.Frame(self.canvas, bg='#f5f5f5')
        self.canvas_window = self.canvas.create_window((0, 0), window=self.table_frame, anchor='nw')
        self.table_frame.bind('<Configure>', lambda e: self.canvas.configure(
            scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>', lambda e: self.canvas.itemconfig(
            self.canvas_window, width=e.width))

        hdr = tk.Frame(self.table_frame, bg='#ecf0f1')
        hdr.pack(fill=tk.X, pady=(0, 4))
        tk.Label(hdr, text="Table ID", width=8, bg='#ecf0f1', font=('Arial', 9, 'bold')).pack(side=tk.LEFT, padx=4)
        tk.Label(hdr, text="Seats", width=8, bg='#ecf0f1', font=('Arial', 9, 'bold')).pack(side=tk.LEFT, padx=4)

        self.rows_container = tk.Frame(self.table_frame, bg='#f5f5f5')
        self.rows_container.pack(fill=tk.X)

        btn_frame = tk.Frame(self.win, bg='#f5f5f5', padx=16, pady=4)
        btn_frame.pack(fill=tk.X)
        tk.Button(btn_frame, text="+ Add Table", font=('Arial', 9),
                  bg='#27ae60', fg='white', command=self._add_row).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(btn_frame, text="- Remove Last", font=('Arial', 9),
                  bg='#e74c3c', fg='white', command=self._remove_row).pack(side=tk.LEFT)

        tk.Button(self.win, text="Save & Continue", font=('Arial', 11, 'bold'),
                  bg='#3498db', fg='white', pady=8,
                  command=self._save).pack(fill=tk.X, padx=16, pady=8)

    def _load_existing(self):
        r = self.config.config["restaurant"]
        self.name_var.set(r.get("name", "The Olive Garden"))
        self.open_var.set(r.get("opening_time", "11:00"))
        self.close_var.set(r.get("closing_time", "22:00"))
        tables = r.get("tables", [])
        if not tables:
            tables = self.DEFAULT_TABLES
        for t in tables:
            self._add_row(t["id"], t["seats"])

    def _add_row(self, table_id=None, seats=None):
        next_id = len(self.table_rows) + 1 if table_id is None else table_id
        row = tk.Frame(self.rows_container, bg='#f5f5f5')
        row.pack(fill=tk.X, pady=1)
        id_var = tk.IntVar(value=next_id)
        seat_var = tk.IntVar(value=seats if seats else 4)
        tk.Spinbox(row, from_=1, to=999, textvariable=id_var, width=7,
                   font=('Arial', 9)).pack(side=tk.LEFT, padx=4)
        tk.Spinbox(row, from_=1, to=30, textvariable=seat_var, width=7,
                   font=('Arial', 9)).pack(side=tk.LEFT, padx=4)
        self.table_rows.append((row, id_var, seat_var))

    def _remove_row(self):
        if self.table_rows:
            row, _, _ = self.table_rows.pop()
            row.destroy()

    def _validate(self):
        if not self.name_var.get().strip():
            messagebox.showerror("Error", "Restaurant name cannot be empty.", parent=self.win)
            return False
        for label, var in [("Opening", self.open_var), ("Closing", self.close_var)]:
            try:
                datetime.strptime(var.get().strip(), "%H:%M")
            except ValueError:
                messagebox.showerror("Error", f"{label} time must be HH:MM format.", parent=self.win)
                return False
        open_t = datetime.strptime(self.open_var.get().strip(), "%H:%M")
        close_t = datetime.strptime(self.close_var.get().strip(), "%H:%M")
        if open_t >= close_t:
            messagebox.showerror("Error", "Opening time must be before closing time.", parent=self.win)
            return False
        if not self.table_rows:
            messagebox.showerror("Error", "At least one table is required.", parent=self.win)
            return False
        return True

    def _save(self):
        if not self._validate():
            return
        tables = [{"id": id_var.get(), "seats": seat_var.get()}
                  for _, id_var, seat_var in self.table_rows]
        new_config = {
            "restaurant": {
                "name": self.name_var.get().strip(),
                "opening_time": self.open_var.get().strip(),
                "closing_time": self.close_var.get().strip(),
                "max_capacity": sum(t["seats"] for t in tables),
                "tables": tables,
                "setup_complete": True
            }
        }
        with open(self.config.filename, 'w') as f:
            json.dump(new_config, f, indent=2)
        self.completed = True
        self.win.destroy()


class State:
    IDLE = 'idle'
    BOOKING_NAME = 'booking_name'
    BOOKING_GUESTS = 'booking_guests'
    BOOKING_DATE = 'booking_date'
    BOOKING_TIME = 'booking_time'
    CANCEL_ID = 'cancel_id'
    CHECK_DATE = 'check_date'


BOOKING_STATES = (State.BOOKING_NAME, State.BOOKING_GUESTS, State.BOOKING_DATE, State.BOOKING_TIME)


class ChatBot:
    KEYWORDS = {
        'book': ['book', 'reserve', 'reservation', 'table for'],
        'cancel': ['cancel', 'remove', 'delete'],
        'check': ['check', 'available', 'availability', 'free'],
        'help': ['help', 'commands', 'what can', 'options'],
        'view': ['view', 'show', 'list', 'all bookings']
    }

    def __init__(self, db, config):
        self.db = db
        self.config = config
        self.state = State.IDLE
        self.booking_data = {}
        self._asked_restart = False

    def process(self, msg):
        msg = msg.strip()
        if not msg:
            return "Please type something. Try 'help' to see what I can do."

        if self.state != State.IDLE:
            msg_lower = msg.lower()

            # Escape phrases reset the current flow
            if msg_lower in CANCEL_PHRASES:
                self.reset()
                return "No problem, starting over. Type 'help' to see what I can do."

            # Help during a flow shows help without losing state
            if 'help' in msg_lower.split():
                return f"{self.show_help()}\n\n---\n{self._state_hint()}"

            # Trying to book again while already booking
            if self.state in BOOKING_STATES:
                if self.get_intent(msg) == 'book':
                    self._asked_restart = True
                    return "You're already making a booking. Start over? (yes/no)"

            # Yes/No response to the "start over?" prompt
            if self._asked_restart and self.state in BOOKING_STATES:
                if msg_lower in ('yes', 'y'):
                    self._asked_restart = False
                    return self.start_booking()
                if msg_lower in ('no', 'n'):
                    self._asked_restart = False
                    return self._state_hint()

            return self.handle_state(msg)

        intent = self.get_intent(msg)
        if intent == 'book':
            return self.start_booking()
        elif intent == 'cancel':
            return self.start_cancel()
        elif intent == 'check':
            return self.start_check()
        elif intent == 'view':
            return self.view_all()
        elif intent == 'help':
            return self.show_help()
        else:
            return "Sorry I didn't get that. Type 'help' to see what I can do."

    def _state_hint(self):
        hints = {
            State.BOOKING_NAME: "You were booking a table. What name for the reservation?",
            State.BOOKING_GUESTS: f"You were booking for {self.booking_data.get('name', '')}. How many guests?",
            State.BOOKING_DATE: "What date for the reservation? (DD/MM/YYYY)",
            State.BOOKING_TIME: f"What time? We're open {self.config.opening_time} to {self.config.closing_time}",
            State.CANCEL_ID: "What's your booking reference number?",
            State.CHECK_DATE: "What date do you want to check? (DD/MM/YYYY)",
        }
        return hints.get(self.state, "Type 'help' to start over.")

    def get_intent(self, msg):
        msg = msg.lower()
        for intent, words in self.KEYWORDS.items():
            for word in words:
                if word in msg:
                    return intent
        return None

    def handle_state(self, msg):
        if self.state == State.BOOKING_NAME:
            name = self.clean_name(msg)
            if not name:
                return "Name can't be empty. What name for the reservation?"
            self.booking_data['name'] = name
            self.state = State.BOOKING_GUESTS
            return f"Thanks {name}! How many people will be dining?"

        elif self.state == State.BOOKING_GUESTS:
            num = self.get_number(msg)
            if num is None:
                return "That doesn't look like a number. How many guests?"
            if num < 1 or num > 20:
                return "Please enter a number between 1 and 20."
            self.booking_data['guests'] = num
            self.state = State.BOOKING_DATE
            return f"Party of {num}. What date? (DD/MM/YYYY)"

        elif self.state == State.BOOKING_DATE:
            date = self.clean_date(msg)
            if not date:
                return "Please use DD/MM/YYYY format like 15/02/2026."
            if date == 'past':
                return "That date has already passed. Please enter a future date (DD/MM/YYYY)."
            self.booking_data['date'] = date
            self.state = State.BOOKING_TIME
            return f"And what time? We're open {self.config.opening_time} to {self.config.closing_time}"

        elif self.state == State.BOOKING_TIME:
            time = self.clean_time(msg)
            if not time:
                return "Please enter a time like '7pm' or '19:00'."
            if not self._within_hours(time):
                return (f"We're only open {self.config.opening_time} to {self.config.closing_time}. "
                        f"Please choose a time within those hours.")
            self.booking_data['time'] = time
            return self.finish_booking()

        elif self.state == State.CANCEL_ID:
            try:
                res_id = int(msg.replace('#', '').strip())
                return self.finish_cancel(res_id)
            except:
                return "Please enter the booking reference number (like 1001)."

        elif self.state == State.CHECK_DATE:
            date = self.clean_date(msg)
            if not date or date == 'past':
                return "Please use DD/MM/YYYY format."
            return self.finish_check(date)

        return "Something went wrong. Type 'help' to start over."

    def _within_hours(self, time_str):
        try:
            t = datetime.strptime(time_str, '%H:%M')
            open_t = datetime.strptime(self.config.opening_time, '%H:%M')
            close_t = datetime.strptime(self.config.closing_time, '%H:%M')
            return open_t <= t <= close_t
        except:
            return True

    def clean_name(self, msg):
        msg_lower = msg.lower().strip()
        prefixes = ["under the name of ", "my name is ", "call me ", "it's ",
                    "it is ", "name is ", "the name is ", "i am ", "i'm ",
                    "this is ", "put it under ", "put under ", "book under ",
                    "reserve under ", "for ", "name: "]
        for prefix in prefixes:
            if msg_lower.startswith(prefix):
                msg = msg[len(prefix):]
                break
        for suffix in [" please", " thanks", " thank you"]:
            if msg_lower.endswith(suffix):
                msg = msg[:-len(suffix)]
                break
        return msg.strip().title()

    def get_number(self, text):
        text = text.lower().strip()
        words = {
            'one': 1, 'two': 2, 'three': 3, 'four': 4, 'five': 5,
            'six': 6, 'seven': 7, 'eight': 8, 'nine': 9, 'ten': 10,
            'eleven': 11, 'twelve': 12, 'thirteen': 13, 'fourteen': 14,
            'fifteen': 15, 'sixteen': 16, 'seventeen': 17, 'eighteen': 18,
            'nineteen': 19, 'twenty': 20, 'a': 1, 'an': 1
        }
        for word in text.split():
            try:
                return int(word)
            except:
                if word in words:
                    return words[word]
        return None

    def clean_date(self, text):
        text = text.lower().strip()
        today = datetime.now().date()

        try:
            dt = datetime.strptime(text, '%d/%m/%Y')
            return 'past' if dt.date() < today else text
        except:
            pass

        numbers = re.findall(r'\d+', text)
        if len(numbers) >= 3:
            day = numbers[0].zfill(2)
            month = numbers[1].zfill(2)
            year = numbers[2] if len(numbers[2]) == 4 else '20' + numbers[2]
            formatted = f"{day}/{month}/{year}"
            try:
                dt = datetime.strptime(formatted, '%d/%m/%Y')
                return 'past' if dt.date() < today else formatted
            except:
                pass
        return None

    def clean_time(self, time_str):
        time_str = time_str.lower().strip()
        time_str = time_str.replace('a.m.', 'am').replace('p.m.', 'pm')
        if time_str.startswith('at '):
            time_str = time_str[3:].strip()
        for fmt in ['%H:%M', '%I:%M%p', '%I%p', '%I:%M %p', '%I %p']:
            try:
                return datetime.strptime(time_str, fmt).strftime('%H:%M')
            except:
                continue
        return None

    def start_booking(self):
        self.state = State.BOOKING_NAME
        self.booking_data = {}
        self._asked_restart = False
        return f"Sure, I can help you book a table at {self.config.name}.\n\nWhat name should I put the reservation under?"

    def finish_booking(self):
        date = self.booking_data['date']
        guests = self.booking_data['guests']
        info = self.db.check_availability(date)
        if info['total_guests'] + guests > self.config.max_capacity:
            self.reset()
            return (f"Sorry, we don't have enough capacity on {date}. "
                    f"We already have {info['total_guests']} guests booked "
                    f"out of {self.config.max_capacity} total capacity.")
        res_id = self.db.add_reservation(
            self.booking_data['name'], guests, date, self.booking_data['time']
        )
        response = (f"Booking confirmed!\n\n"
                    f"Reference: #{res_id}\n"
                    f"Name: {self.booking_data['name']}\n"
                    f"Guests: {guests}\n"
                    f"Date: {date}\n"
                    f"Time: {self.booking_data['time']}\n\n"
                    f"Please save your reference number!")
        self.reset()
        return response

    def start_cancel(self):
        self.state = State.CANCEL_ID
        return "No problem. What's your booking reference number?"

    def finish_cancel(self, res_id):
        cancelled = self.db.cancel_reservation(res_id)
        self.reset()
        if cancelled:
            return f"Done! Cancelled booking #{cancelled['id']} for {cancelled['name']}"
        return f"Couldn't find booking #{res_id}. Double check the number?"

    def start_check(self):
        self.state = State.CHECK_DATE
        return "What date do you want to check? (DD/MM/YYYY)"

    def finish_check(self, date):
        info = self.db.check_availability(date)
        self.reset()
        if info['count'] == 0:
            return f"No bookings on {date} yet - plenty of space! Want to make a reservation?"
        return (f"On {date}: {info['count']} bookings, {info['total_guests']} guests expected.\n"
                f"Still have availability though!")

    def view_all(self):
        bookings = self.db.get_all()
        if not bookings:
            return "No reservations at the moment."
        response = f"Current bookings at {self.config.name}:\n\n"
        for b in bookings:
            response += f"#{b['id']} - {b['name']}, {b['guests']} guests\n"
            response += f"   {b['date']} at {b['time']}\n\n"
        return response

    def show_help(self):
        return (f"{self.config.name} Reservation Bot\n\n"
                f"Commands:\n"
                f"- 'book' or 'reserve' - make a reservation\n"
                f"- 'cancel' - cancel a booking\n"
                f"- 'check' - check availability\n"
                f"- 'view' - see all bookings\n"
                f"- 'help' - show this message\n\n"
                f"Voice Controls:\n"
                f"- Click the microphone button to speak\n"
                f"- Bot responses can be read aloud\n\n"
                f"Hours: {self.config.opening_time} - {self.config.closing_time}")

    def reset(self):
        self.state = State.IDLE
        self.booking_data = {}
        self._asked_restart = False


class ChatbotGUI:
    def __init__(self):
        self.db = ReservationDatabase()
        self.config = RestaurantConfig()
        self.bot = ChatBot(self.db, self.config)
        self.recording = False
        self.recognizer = None

        if SPEECH_AVAILABLE:
            self.recognizer = sr.Recognizer()
            self.recognizer.pause_threshold = 0.8

        self.window = tk.Tk()
        self.window.title(f"{self.config.name} - Reservation Bot")
        self.window.geometry("550x700")
        self.window.configure(bg='#f5f5f5')
        self.window.minsize(450, 550)

        self.setup_ui()
        self.show_welcome()

        if not self.config.is_setup_complete():
            self.window.after(200, self.open_settings)

    def setup_ui(self):
        # Header
        header = tk.Frame(self.window, bg='#34495e', pady=12)
        header.pack(fill=tk.X)

        tk.Label(header, text=self.config.name, font=('Arial', 16, 'bold'),
                 fg='white', bg='#34495e').pack(side=tk.LEFT, padx=16)
        tk.Button(header, text="Settings", font=('Arial', 9),
                  bg='#7f8c8d', fg='white', command=self.open_settings).pack(side=tk.RIGHT, padx=16)
        tk.Label(header, text="ResBot · Reservation Chatbot", font=('Arial', 10),
                 fg='#bdc3c7', bg='#34495e').pack()

        # Chat area
        chat_frame = tk.Frame(self.window, bg='#f5f5f5', padx=8, pady=8)
        chat_frame.pack(fill=tk.BOTH, expand=True)

        self.chat = scrolledtext.ScrolledText(
            chat_frame, wrap=tk.WORD, font=('Consolas', 10),
            bg='white', state=tk.DISABLED, padx=8, pady=8
        )
        self.chat.pack(fill=tk.BOTH, expand=True)

        self.chat.tag_configure('user', foreground='#2980b9')
        self.chat.tag_configure('bot', foreground='#27ae60')
        self.chat.tag_configure('info', foreground='#7f8c8d')
        self.chat.tag_configure('voice', foreground='#9b59b6')

        # Input area
        input_frame = tk.Frame(self.window, bg='#ecf0f1', padx=8, pady=8)
        input_frame.pack(fill=tk.X)

        self.voice_btn = tk.Button(
            input_frame, text="🎤", font=('Arial', 14),
            bg='#e74c3c', fg='white', width=3,
            command=self.toggle_voice
        )
        self.voice_btn.pack(side=tk.LEFT, padx=(0, 8))

        self.entry = tk.Entry(input_frame, font=('Arial', 11), bg='white')
        self.entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        self.entry.bind('<Return>', lambda e: self.send())

        tk.Button(input_frame, text="Send", font=('Arial', 10),
                  bg='#3498db', fg='white', command=self.send).pack(side=tk.RIGHT)

        # Quick buttons
        btns_frame = tk.Frame(self.window, bg='#ecf0f1', padx=8, pady=4)
        btns_frame.pack(fill=tk.X)

        for text, cmd in [("Book", "book"), ("Cancel", "cancel"), ("Check", "check"),
                          ("View All", "view"), ("Help", "help")]:
            tk.Button(btns_frame, text=text, font=('Arial', 9),
                      bg='#95a5a6', fg='white',
                      command=lambda c=cmd: self.quick_cmd(c)).pack(side=tk.LEFT, padx=2)

        # Voice controls
        voice_frame = tk.Frame(self.window, bg='#ecf0f1', padx=8, pady=4)
        voice_frame.pack(fill=tk.X)

        self.voice_output = tk.BooleanVar(value=True)
        tk.Checkbutton(voice_frame, text="Voice Output",
                       variable=self.voice_output,
                       bg='#ecf0f1', font=('Arial', 9)).pack(side=tk.LEFT)
        tk.Button(voice_frame, text="Mute", font=('Arial', 9),
                  bg='#e74c3c', fg='white',
                  command=self.mute).pack(side=tk.LEFT, padx=(10, 0))

        # Status bar
        self.status_label = tk.Label(
            self.window,
            text=f"Open {self.config.opening_time} - {self.config.closing_time}  |  Capacity: {self.config.max_capacity} guests",
            font=('Arial', 9), fg='#7f8c8d', bg='#34495e', pady=4
        )
        self.status_label.pack(fill=tk.X)

    def open_settings(self):
        setup = SetupScreen(self.window, self.config)
        self.window.wait_window(setup.win)
        if setup.completed:
            self.config.reload()
            self.bot = ChatBot(self.db, self.config)
            self.window.title(f"{self.config.name} - Reservation Bot")
            self.status_label.config(
                text=f"Open {self.config.opening_time} - {self.config.closing_time}  |  Capacity: {self.config.max_capacity} guests"
            )
            messagebox.showinfo("Settings Saved", f"Restaurant updated to: {self.config.name}")

    def show_welcome(self):
        self.display(
            f"Welcome to {self.config.name} reservation system!\n\n"
            f"I can help you book a table, cancel bookings, or check availability.\n\n"
            f"Type a command or click the buttons below.\n"
            f"Type 'help' for more info.",
            'info'
        )

    def toggle_voice(self):
        if not SPEECH_AVAILABLE or not self.recognizer:
            messagebox.showerror("Voice Not Available",
                "Please install: pip install SpeechRecognition pyttsx3 PyAudio")
            return

        if not self.recording:
            self.recording = True
            self.voice_btn.config(bg='#c0392b', text="⏹")
            self.display("🎤 Listening...", 'voice')

            def record():
                try:
                    with sr.Microphone() as source:
                        self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                        audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=5)
                    try:
                        text = self.recognizer.recognize_google(audio)
                        self.window.after(0, lambda: self.process_voice(text))
                    except:
                        self.window.after(0, lambda: self.display("🎤 Could not understand", 'voice'))
                except Exception as e:
                    self.window.after(0, lambda: self.display(f"🎤 Error: {e}", 'voice'))

            threading.Thread(target=record).start()
        else:
            self.recording = False
            self.voice_btn.config(bg='#e74c3c', text="🎤")

    def process_voice(self, text):
        self.recording = False
        self.voice_btn.config(bg='#e74c3c', text="🎤")
        self.display(f"You: {text}", 'user')
        response = self.bot.process(text)
        self.display(f"Bot: {response}", 'bot')
        if self.voice_output.get():
            self.speak(response)

    def send(self):
        msg = self.entry.get().strip()
        if not msg:
            return
        self.entry.delete(0, tk.END)
        self.display(f"You: {msg}", 'user')
        response = self.bot.process(msg)
        self.display(f"Bot: {response}", 'bot')
        if self.voice_output.get():
            self.speak(response)

    def speak(self, text):
        if not TTS_AVAILABLE or not self.voice_output.get():
            return
        clean = re.sub(r'[#*_]', '', text).replace('\n', ' ').strip()
        if not clean:
            return

        def do_speak():
            try:
                engine = pyttsx3.init()
                engine.setProperty('rate', 170)
                engine.setProperty('volume', 0.9)
                voices = engine.getProperty('voices')
                for voice in voices:
                    if 'zira' in voice.name.lower():
                        engine.setProperty('voice', voice.id)
                        break
                engine.say(clean)
                engine.runAndWait()
            except:
                pass

        threading.Thread(target=do_speak, daemon=True).start()

    def mute(self):
        self.voice_output.set(False)
        self.display("Voice muted - check the box to enable again", 'voice')

    def quick_cmd(self, cmd):
        self.entry.delete(0, tk.END)
        self.entry.insert(0, cmd)
        self.send()

    def display(self, msg, tag):
        self.chat.config(state=tk.NORMAL)
        self.chat.insert(tk.END, msg + '\n\n', tag)
        self.chat.see(tk.END)
        self.chat.config(state=tk.DISABLED)

    def run(self):
        self.entry.focus()
        self.window.mainloop()


if __name__ == "__main__":
    app = ChatbotGUI()
    app.run()
