import streamlit as st
import requests
import datetime
import json
import re

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
if "machines_dict" not in st.session_state:
    st.session_state.machines_dict = {}
if "machine_messages" not in st.session_state:
    st.session_state.machine_messages = {}


# ---------------- LOGIN ----------------
def login_page():
    st.title("🔒 Login")
    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        if check_login(username, password):
            st.session_state.logged_in = True
            st.session_state.current_page = "machines"
            # Load and organize messages by MAC address when logging in
            load_and_organize_messages()
            st.success("Login successful!")
            st.rerun()
        else:
            st.error("Wrong credentials")


def check_login(username, password):
    return username == "admin" and password == VIEW_KEY


def extract_mac_address(text):
    """Extract first 17 characters or MAC address pattern from text"""
    if not text:
        return None
    
    # Try to extract MAC address pattern (XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX)
    mac_pattern = r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})'
    match = re.search(mac_pattern, text)
    
    if match:
        return match.group(0)
    
    # If no MAC pattern found, take first 17 characters
    if len(text) >= 17:
        return text[:17].strip()
    
    return None


def load_and_organize_messages():
    """Load messages from server and organize them by MAC address"""
    try:
        response = requests.get(f"{SERVER_URL}/view", params={"key": VIEW_KEY})
        
        if response.status_code == 200:
            messages = response.json()["messages"]
            
            # Clear existing data
            st.session_state.machines_dict = {}
            st.session_state.machine_messages = {}
            
            # Counter for unnamed machines
            machine_counter = 1
            
            for msg in messages:
                # Split line by '|', flexible handling
                parts = [x.strip() for x in msg.split("|")]
                
                if len(parts) < 3:
                    continue  # Skip invalid messages
                
                text = " | ".join(parts[2:-1]) if len(parts) > 3 else parts[2]
                
                # Extract MAC address from text
                mac_address = extract_mac_address(text)
                
                if mac_address:
                    # If this MAC is new, create a new machine entry
                    if mac_address not in st.session_state.machines_dict:
                        machine_name = f"Machine {machine_counter}"
                        st.session_state.machines_dict[mac_address] = machine_name
                        st.session_state.machine_messages[mac_address] = []
                        machine_counter += 1
                    
                    # Add the message to the corresponding machine
                    st.session_state.machine_messages[mac_address].append(msg)
                else:
                    # If no MAC found, add to "Unknown" category
                    if "Unknown" not in st.session_state.machines_dict:
                        st.session_state.machines_dict["Unknown"] = "Unknown Machine"
                        st.session_state.machine_messages["Unknown"] = []
                    
                    st.session_state.machine_messages["Unknown"].append(msg)
    
    except requests.exceptions.RequestException as e:
        st.error(f"Server error: {e}")


# ---------------- MACHINES PAGE ----------------
def machines_page():
    st.title("🖥️ Machines list")
    
    # Refresh button to reload messages
    if st.button("🔄 Refresh Messages"):
        load_and_organize_messages()
        st.success("Messages refreshed!")
        st.rerun()
    
    # Display machine count
    st.write(f"**Total Machines Found:** {len(st.session_state.machines_dict)}")
    
    if not st.session_state.machines_dict:
        st.warning("No machines found. Make sure the server has messages.")
        
        if st.button("Load Messages Now"):
            load_and_organize_messages()
            st.rerun()
    else:
        # Create display options with MAC address and machine name
        options = []
        for mac, name in st.session_state.machines_dict.items():
            message_count = len(st.session_state.machine_messages.get(mac, []))
            options.append(f"{name} - {mac} ({message_count} messages)")
        
        # Set default selection if not set
        if st.session_state.selected_machine is None and st.session_state.machines_dict:
            first_mac = list(st.session_state.machines_dict.keys())[0]
            st.session_state.selected_machine = first_mac
        
        # Find the index of the currently selected machine
        selected_index = 0
        if st.session_state.selected_machine in st.session_state.machines_dict:
            macs = list(st.session_state.machines_dict.keys())
            selected_index = macs.index(st.session_state.selected_machine)
        
        # Create selectbox
        selected_option = st.selectbox(
            "Select a machine",
            options,
            index=selected_index
        )
        
        # Extract MAC address from selected option
        if selected_option:
            # Find the MAC address in the selected option
            mac_pattern = r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})'
            match = re.search(mac_pattern, selected_option)
            
            if match:
                selected_mac = match.group(0)
            else:
                # If no MAC pattern, try to extract from format
                parts = selected_option.split(" - ")
                if len(parts) > 1:
                    # The MAC might be in the second part before the parentheses
                    mac_part = parts[1].split(" (")[0]
                    selected_mac = mac_part
            
            st.session_state.selected_machine = selected_mac
        
        col1, col2 = st.columns(2)
        with col1:
            if st.button("View Machine Info"):
                if st.session_state.selected_machine:
                    st.session_state.current_page = "machine_info"
                    st.rerun()
        
        with col2:
            if st.button("Logout"):
                st.session_state.logged_in = False
                st.session_state.current_page = "login"
                st.session_state.selected_machine = None
                st.rerun()


# ---------------- MACHINE INFO PAGE ----------------
def machine_info_page():
    if not st.session_state.selected_machine:
        st.error("No machine selected!")
        st.session_state.current_page = "machines"
        st.rerun()
        return
    
    machine_mac = st.session_state.selected_machine
    machine_name = st.session_state.machines_dict.get(machine_mac, f"Machine ({machine_mac})")
    
    st.title(f"{machine_name}")
    st.subheader(f"MAC Address: {machine_mac}")
    
    # Get messages for this machine
    machine_msgs = st.session_state.machine_messages.get(machine_mac, [])
    
    st.write(f"**Total Messages:** {len(machine_msgs)}")
    
    if not machine_msgs:
        st.info("No messages found for this machine.")
    else:
        for msg in machine_msgs:
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

    col1, col2 = st.columns(2)
    with col1:
        if st.button("⬅ Back to Machines List"):
            st.session_state.current_page = "machines"
            st.rerun()
    
    with col2:
        if st.button("🔄 Refresh This Machine"):
            load_and_organize_messages()
            st.rerun()


# ---------------- ROUTING ----------------
if not st.session_state.logged_in:
    login_page()
else:
    if st.session_state.current_page == "machines":
        machines_page()
    elif st.session_state.current_page == "machine_info":
        machine_info_page()