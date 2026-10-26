"""MindMitra: an educational CLNLP prototype for cognitive engagement."""

from datetime import datetime
import re
import subprocess
import sys

import pandas as pd
import streamlit as st

from nlp_engine import predict_intent, train_intent_model
from database import (
    add_mood,
    add_reminder,
    add_score,
    initialise_database,
    load_moods,
    load_reminders,
    load_scores,
    update_reminder_status,
)


st.set_page_config(page_title="MindMitra", page_icon="🧠", layout="wide")


def initialise_state():
    # Reload lists if a pre-SQLite Streamlit session is still open.
    storage = {
        "reminders": load_reminders,
        "scores": load_scores,
        "moods": load_moods,
    }
    for key, loader in storage.items():
        existing = st.session_state.get(key, [])
        if key not in st.session_state or any("id" not in item for item in existing):
            st.session_state[key] = loader()

    for key in ("quiz_index", "quiz_correct"):
        if key not in st.session_state:
            st.session_state[key] = 0


@st.cache_resource
def get_intent_model():
    """Train once per app session; refresh automatically when the app restarts."""
    return train_intent_model()


def extract_reminder(text: str):
    """Small rule-based slot extractor, suitable for explaining in a CLNLP viva."""
    time_pattern = r"\b(?:at\s*)?(\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\b"
    found_time = re.search(time_pattern, text.lower())
    when = found_time.group(1).upper() if found_time else "Time not specified"
    task = re.sub(r"\b(remind me to|remind me|at\s*\d{1,2}(?::\d{2})?\s*(?:am|pm)?)\b", "", text, flags=re.I)
    task = task.strip(" .") or "New reminder"
    return task.capitalize(), when


def assistant_reply(text: str):
    intent, confidence = predict_intent(get_intent_model(), text)
    label = f"\n\n*Detected intent: `{intent}` ({confidence:.0f}% confidence)*"
    if intent == "set_reminder":
        task, when = extract_reminder(text)
        st.session_state.reminders.insert(0, add_reminder(task, when))
        return f"I will remind you to **{task.lower()}** at **{when}**.{label}"
    if intent == "mood_check":
        return "Thank you for sharing that. Would you like to try a short, relaxing memory activity or call a family member?" + label
    if intent == "memory_game":
        return "Wonderful. Please open the **Cognitive Games** tab and choose an activity." + label
    if intent == "greeting":
        return "Hello! I am MindMitra. I can set a reminder, ask a memory question, or record how you feel." + label
    return "I can help with reminders, mood check-ins, and cognitive games. For example, say: ‘Remind me to take medicine at 8 PM.’" + label


def save_reminder_completion(index: int, reminder_id: int) -> None:
    """Persist a checkbox change before Streamlit redraws the dashboard metrics."""
    is_done = st.session_state[f"reminder_{reminder_id}"]
    update_reminder_status(reminder_id, is_done)
    st.session_state.reminders[index]["done"] = is_done


def reminder_is_due(reminder: dict, now: datetime) -> bool:
    """Match an unfinished reminder's stored 12-hour time against the current minute."""
    if reminder["done"] or reminder["when"] == "Time not specified":
        return False
    cleaned_time = reminder["when"].replace(" ", "")
    for time_format in ("%I:%M%p", "%I%p"):
        try:
            scheduled = datetime.strptime(cleaned_time, time_format)
            return (scheduled.hour, scheduled.minute) == (now.hour, now.minute)
        except ValueError:
            continue
    return False


def send_desktop_alert(title: str, message: str) -> None:
    """Show a native macOS notification and audible beep for a due reminder."""
    if sys.platform == "darwin":
        safe_title = title.replace('"', "'")
        safe_message = message.replace('"', "'")
        # A native beep is more reliable than browser audio for a local Streamlit demo.
        subprocess.run(["osascript", "-e", "beep 2"], check=False, capture_output=True)
        subprocess.run(
            ["osascript", "-e", f'display notification "{safe_message}" with title "{safe_title}"'],
            check=False,
            capture_output=True,
        )


@st.fragment(run_every="10s")
def reminder_alert_panel() -> None:
    """Poll the local reminder list and alert once per reminder per day."""
    now = datetime.now()
    due_reminders = [reminder for reminder in load_reminders() if reminder_is_due(reminder, now)]
    manual_test = st.session_state.get("show_test_alert", False)

    if not due_reminders and not manual_test:
        st.caption("🔔 Reminder monitoring is active. It checks every 10 seconds while this app is open.")
        return

    if manual_test:
        st.error("🔔 Test reminder alert: It is time to take your medicine.")
        if not st.session_state.get("test_alert_sent", False):
            send_desktop_alert("MindMitra test alert", "It is time to take your medicine.")
            st.session_state.test_alert_sent = True
        if st.button("Dismiss test alert", key="dismiss_test_alert"):
            st.session_state.show_test_alert = False
            st.session_state.test_alert_sent = False
            st.rerun(scope="fragment")

    for reminder in due_reminders:
        st.error(f"🔔 **Reminder due now:** {reminder['task']} ({reminder['when']})")
        alert_key = f"alerted_{now.date().isoformat()}_{reminder['id']}"
        if not st.session_state.get(alert_key, False):
            send_desktop_alert("MindMitra reminder", f"It is time to {reminder['task'].lower()}.")
            st.session_state[alert_key] = True


initialise_database()
initialise_state()

st.title("🧠 MindMitra")
st.caption("A supportive NLP-based cognitive gaming and memory-assistance prototype for elderly users. Educational use only — not a diagnostic tool.")
reminder_alert_panel()

home, games, caregiver, about = st.tabs(["🏠 Assistant", "🎮 Cognitive Games", "👩‍⚕️ Caregiver View", "📘 Project Details"])

with home:
    st.subheader("Talk to MindMitra")
    st.write("Try: **“Remind me to take medicine at 8 PM”**, **“I feel lonely today”**, or **“Start a memory game.”**")
    message = st.text_input("Your message", placeholder="Type here…", key="chat_input")
    if st.button("Send", type="primary") and message.strip():
        st.markdown(f"**MindMitra:** {assistant_reply(message)}")

    st.divider()
    st.subheader("How are you feeling today?")
    mood = st.radio("Choose one", ["Happy", "Calm", "Okay", "Sad", "Worried"], horizontal=True, label_visibility="collapsed")
    if st.button("Save mood"):
        entry = add_mood(datetime.now().strftime("%d %b, %I:%M %p"), mood)
        st.session_state.moods.insert(0, entry)
        st.success("Thank you. Your response has been saved for the caregiver summary.")

with games:
    st.subheader("Word Recall Game")
    words = ["Mango", "River", "Clock"]
    st.info("Remember these three words for 15 seconds: **Mango · River · Clock**")
    answer = st.text_input("Enter the words you remember (any order)", key="recall_answer")
    if st.button("Check recall"):
        remembered = sum(word.lower() in answer.lower() for word in words)
        entry = add_score("Word Recall", remembered, 3, datetime.now().strftime("%d %b"))
        st.session_state.scores.insert(0, entry)
        if remembered == 3:
            st.success("Excellent! You remembered all three words.")
        else:
            st.info(f"You remembered {remembered}/3. The words were: Mango, River, Clock. Nice effort!")

    st.divider()
    st.subheader("Daily Orientation")
    today = datetime.now().strftime("%A")
    choices = ["Monday", "Wednesday", "Friday", "Sunday"]
    orientation = st.radio("What day is it today?", choices, key="orientation")
    if st.button("Check answer"):
        score = int(orientation == today)
        entry = add_score("Orientation", score, 1, datetime.now().strftime("%d %b"))
        st.session_state.scores.insert(0, entry)
        st.success("Correct — well done!" if score else f"Today is {today}. That is okay; let's try again tomorrow.")

with caregiver:
    st.subheader("Caregiver Summary")
    if st.button("🔔 Test reminder alert", help="Shows an on-screen and macOS notification for demonstration."):
        st.session_state.show_test_alert = True
        st.session_state.test_alert_sent = False
        st.rerun()
    col1, col2, col3 = st.columns(3)
    total = len(st.session_state.reminders)
    completed = sum(item["done"] for item in st.session_state.reminders)
    avg_score = (sum(item["score"] / item["out_of"] for item in st.session_state.scores) / len(st.session_state.scores) * 100) if st.session_state.scores else 0
    col1.metric("Reminders completed", f"{completed}/{total}")
    col2.metric("Activities played", len(st.session_state.scores))
    col3.metric("Average activity score", f"{avg_score:.0f}%")

    st.markdown("#### Reminder checklist")
    for index, reminder in enumerate(st.session_state.reminders):
        st.checkbox(
            f"{reminder['task']} — {reminder['when']}",
            value=reminder["done"],
            key=f"reminder_{reminder['id']}",
            on_change=save_reminder_completion,
            args=(index, reminder["id"]),
        )

    if st.session_state.moods:
        st.markdown("#### Recent mood entries")
        st.dataframe(pd.DataFrame(st.session_state.moods).drop(columns="id").iloc[::-1], width="stretch", hide_index=True)
    if st.session_state.scores:
        st.markdown("#### Activity history")
        st.dataframe(pd.DataFrame(st.session_state.scores).drop(columns=["id", "played_at"], errors="ignore").iloc[::-1], width="stretch", hide_index=True)

with about:
    st.subheader("CLNLP Project Components")
    st.markdown("""
    - **Intent classification:** TF-IDF vectorization plus Logistic Regression predicts reminder, mood, game, greeting, and help intents.
    - **Entity extraction:** regular expressions extract a time and task from reminder requests.
    - **Dialogue management:** intent-specific, safe, supportive replies.
    - **Cognitive engagement:** recall and orientation activities with performance logging.
    - **Data persistence:** SQLite saves reminders, mood logs, and game scores locally between sessions.
    - **In-app alerts:** an active app checks due reminders every 10 seconds and displays an on-screen/macOS alert.
    - **Ethics:** this app supports daily engagement; it does not diagnose dementia or replace a clinician.
    """)
    st.code("streamlit run app.py", language="bash")
