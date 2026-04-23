ResBot — Voice-Enabled Restaurant Reservation Chatbot
Khaled Jamal W2018556
6COSC023W Final Year Project — University of Westminster

A conversational chatbot with voice input and output for managing restaurant
table reservations. Staff interact via typed commands or spoken phrases; the
system handles bookings, cancellations, and availability checks through a
guided dialogue flow.

----------------------------------------------------------------------
HOW TO RUN
----------------------------------------------------------------------
1. Install Python 3 (python.org) if not already installed
2. Open Command Prompt in this folder
3. Install dependencies:
      pip install SpeechRecognition pyttsx3
      pip install pipwin
      pipwin install pyaudio
4. Run the application:
      python chatbot.py

----------------------------------------------------------------------
HOW TO USE
----------------------------------------------------------------------
Type a command or click one of the quick buttons at the bottom:

  book   — start a new table reservation
  cancel — cancel an existing booking by reference number
  check  — check how many bookings exist on a given date
  view   — list all current reservations
  help   — show available commands and opening hours

During any conversation flow, type "cancel", "quit", or "start over"
to abandon the current operation and return to the main menu.

VOICE INPUT
  Click the microphone (🎤) button and speak your command.
  The Google Speech API transcribes audio to text automatically.

VOICE OUTPUT
  Tick "Voice Output" to have bot replies read aloud via pyttsx3.
  Click "Mute" at any time to silence the text-to-speech engine.

SETTINGS
  Click the "Settings" button in the header to configure the
  restaurant name, opening/closing times, and table layout.

----------------------------------------------------------------------
FILES
----------------------------------------------------------------------
  chatbot.py        Main application (all logic, GUI, voice)
  config.json       Restaurant configuration (name, hours, tables)
  reservations.json Reservation database (auto-created on first run)
  requirements.txt  Python package dependencies
  test_chatbot.py   Unit test suite (62 tests)

----------------------------------------------------------------------
RUNNING THE TESTS
----------------------------------------------------------------------
  python -m unittest test_chatbot -v

----------------------------------------------------------------------
DEPENDENCIES
----------------------------------------------------------------------
  Python 3.x
  tkinter          (built into Python — GUI framework)
  SpeechRecognition (voice input via Google Speech API)
  pyttsx3          (local text-to-speech, no internet required)
  PyAudio          (microphone access)
