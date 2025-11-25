import streamlit as st
import requests
import datetime
import json

DASHBOARD_URL = "https://data-collector-fwfz.onrender.com/"
SERVER_URL = "https://mini-server-90un.onrender.com"
VIEW_KEY = "my_secret_key_123"

# Session states
if "current_page" not in st.session_state:
    st.session_state.current_page = "login"
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "selected_machine" not in st.session_state:
    st.session_state.selected_machine = None


# ---------------- LOGIN ----------------
def login_page():
    st.title("🔒 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if check_login(username, password):
            st.session_state.logged_in = True
            st.session_state.current_page = "machines"
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Wrong credentials")


def check_login(username, password):
    return username == "admin" and password == VIEW_KEY


# ---------------- MACHINES PAGE ----------------
def machines_page():
    st.title("🖥️ Machines list")

    machines = {"Machine A": "AA:BB:CC:DD:EE:01",
                "Machine B": "AA:BB:CC:DD:EE:02"}

    options = [f"{name} - {mac}" for name, mac in machines.items()]

    if st.session_state.selected_machine is None:
        st.session_state.selected_machine = list(machines.keys())[0]

    selected_option = st.selectbox(
        "Select a machine",
        options,
        index=list(machines.keys()).index(st.session_state.selected_machine)
    )

    st.session_state.selected_machine = selected_option.split("-")[0].strip()

    if st.button("View Info"):
        st.session_state.current_page = "machine_info"
        st.rerun()

    if st.button("Logout"):
        st.session_state.logged_in = False
        st.session_state.current_page = "login"
        st.rerun()


# ---------------- MACHINE INFO PAGE ----------------
def machine_info_page():
    machine = st.session_state.selected_machine
    st.title(f"{machine}'s Data")

    try:
        response = requests.get(f"{SERVER_URL}/view", params={"key": VIEW_KEY})

        if response.status_code == 200:
            messages = response.json()["messages"]

            for msg in messages:
                # Split line by '|', flexible handling
                parts = [x.strip() for x in msg.split("|")]

                # Defaults
                date_str = ""
                content_type = ""
                text = ""
                filename = "no image"

                if len(parts) >= 1:
                    date_str = parts[0]
                if len(parts) >= 2:
                    content_type = parts[1]
                if len(parts) >= 3:
                    text = " | ".join(parts[2:-1]) if len(parts) > 3 else parts[2]
                if len(parts) >= 4:
                    filename = parts[-1]

                # Format date safely
                try:
                    dt = datetime.datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S.%f")
                    dt = dt + datetime.timedelta(hours=1)
                    formatted_date = dt.strftime("%d %b %Y, %H:%M")
                except:
                    formatted_date = date_str

                st.text(f"📅 Date: {formatted_date}")
                st.text(f"📄 Type: {content_type}")
                st.text(f"📝 Text: {text}")

                # Display file if exists
                if filename != "no image":
                    file_res = requests.get(
                        f"{SERVER_URL}/uploads/{filename}",
                        params={"key": VIEW_KEY}
                    )

                    if file_res.status_code == 200:
                        file_bytes = file_res.content
                        if filename.lower().endswith(".json"):
                            try:
                                st.json(json.loads(file_bytes.decode("utf-8")))
                            except:
                                st.text(file_bytes.decode("utf-8"))
                        else:
                            st.image(file_bytes, caption=filename)
                    else:
                        st.error("⚠ Failed to fetch file")
                else:
                    st.caption("📎 No file attached")

                st.divider()

        else:
            st.error("Failed to fetch machine info")

    except requests.exceptions.RequestException as e:
        st.error(f"Server error: {e}")

    if st.button("⬅ Back to Machines List"):
        st.session_state.current_page = "machines"
        st.rerun()


# ---------------- ROUTING ----------------
if not st.session_state.logged_in:
    login_page()
else:
    if st.session_state.current_page == "machines":
        machines_page()
    elif st.session_state.current_page == "machine_info":
        machine_info_page()
