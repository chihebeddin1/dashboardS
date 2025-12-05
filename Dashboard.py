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
if "original_texts" not in st.session_state:
    st.session_state.original_texts = {}


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


def extract_and_remove_mac_address(text):
    """Extract MAC address and return it along with text without MAC"""
    if not text:
        return None, text
    
    # Try to extract MAC address pattern (XX:XX:XX:XX:XX:XX or XX-XX-XX-XX-XX-XX)
    mac_pattern = r'([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})'
    match = re.search(mac_pattern, text)
    
    if match:
        mac_address = match.group(0)
        # Remove the MAC address from the text
        text_without_mac = text.replace(mac_address, "", 1).strip()
        return mac_address, text_without_mac
    
    # If no MAC pattern found, check for first 17 characters
    if len(text) >= 17:
        # Check if first 17 chars could be a MAC (contains : or -)
        first_17 = text[:17]
        if ':' in first_17 or '-' in first_17:
            # Try to find a complete MAC pattern within first 20 chars
            extended_text = text[:20]
            mac_match = re.search(mac_pattern, extended_text)
            if mac_match:
                mac_address = mac_match.group(0)
                text_without_mac = text.replace(mac_address, "", 1).strip()
                return mac_address, text_without_mac
            
            # Otherwise use first 17 chars as MAC
            mac_address = first_17.strip()
            text_without_mac = text[17:].strip()
            return mac_address, text_without_mac
    
    return None, text


def load_and_organize_messages():
    """Load messages from server and organize them by MAC address"""
    try:
        response = requests.get(f"{SERVER_URL}/view", params={"key": VIEW_KEY})
        
        if response.status_code == 200:
            messages = response.json()["messages"]
            
            # Clear existing data
            st.session_state.machines_dict = {}
            st.session_state.machine_messages = {}
            st.session_state.original_texts = {}
            
            # Counter for unnamed machines
            machine_counter = 1
            
            for msg in messages:
                # Split line by '|', flexible handling
                parts = [x.strip() for x in msg.split("|")]
                
                if len(parts) < 3:
                    continue  # Skip invalid messages
                
                original_text = " | ".join(parts[2:-1]) if len(parts) > 3 else parts[2]
                
                # Extract MAC address and get text without MAC
                mac_address, text_without_mac = extract_and_remove_mac_address(original_text)
                
                # Store the original message with MAC removed in a modified version
                if text_without_mac != original_text:
                    # Create a modified message with MAC removed
                    modified_parts = parts.copy()
                    if len(parts) > 3:
                        # Reconstruct the modified text part
                        text_parts = parts[2:-1]
                        modified_text = text_without_mac
                        modified_parts[2] = modified_text
                        for i in range(3, len(modified_parts)-1):
                            modified_parts[i] = ""
                        # Remove empty parts
                        modified_parts = [p for p in modified_parts if p != ""]
                        if len(modified_parts) < len(parts):
                            # Adjust to maintain structure
                            while len(modified_parts) < len(parts):
                                modified_parts.append("")
                    else:
                        modified_parts[2] = text_without_mac
                    
                    modified_msg = " | ".join(modified_parts)
                else:
                    modified_msg = msg
                
                if mac_address:
                    # If this MAC is new, create a new machine entry
                    if mac_address not in st.session_state.machines_dict:
                        machine_name = f"Machine {machine_counter}"
                        st.session_state.machines_dict[mac_address] = machine_name
                        st.session_state.machine_messages[mac_address] = []
                        machine_counter += 1
                    
                    # Add the modified message (without MAC) to the corresponding machine
                    st.session_state.machine_messages[mac_address].append(modified_msg)
                else:
                    # If no MAC found, add to "Unknown" category
                    if "Unknown" not in st.session_state.machines_dict:
                        st.session_state.machines_dict["Unknown"] = "Unknown Machine"
                        st.session_state.machine_messages["Unknown"] = []
                    
                    st.session_state.machine_messages["Unknown"].append(modified_msg)
    
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
                else:
                    selected_mac = "Unknown"
            
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
            
            # Display text (already has MAC address removed)
            if text:
                st.text(f"📝 Text: {text}")
            else:
                st.text("📝 Text: [No text content]")

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