import webbrowser
import os
import json

CONFIG_DIR = os.path.expanduser('~/.claudesync')
CONFIG_FILE = os.path.join(CONFIG_DIR, 'config.json')

def get_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r') as f:
            return json.load(f)
    return {}

def save_config(config):
    os.makedirs(CONFIG_DIR, exist_ok=True)
    with open(CONFIG_FILE, 'w') as f:
        json.dump(config, f, indent=2)

def get_session_key():
    config = get_config()
    stored_session_key = config.get('sessionKey')

    if stored_session_key:
        use_stored = input(f"Found stored sessionKey. Use it? (y/n): ").strip().lower()
        if use_stored == 'y':
            return stored_session_key

    print("To obtain your session key, please follow these steps:")
    print("1. Open your web browser and go to https://claude.ai")
    print("2. Log in to your Claude account if you haven't already")
    print("3. Once logged in, open your browser's developer tools:")
    print("   - Chrome/Edge: Press F12 or Ctrl+Shift+I (Cmd+Option+I on Mac)")
    print("   - Firefox: Press F12 or Ctrl+Shift+I (Cmd+Option+I on Mac)")
    print("   - Safari: Enable developer tools in Preferences > Advanced, then press Cmd+Option+I")
    print("4. In the developer tools, go to the 'Application' tab (Chrome/Edge) or 'Storage' tab (Firefox)")
    print("5. In the left sidebar, expand 'Cookies' and select 'https://claude.ai'")
    print("6. Find the cookie named 'sessionKey' and copy its value")

    try:
        webbrowser.open("https://claude.ai")
    except:
        print("Unable to automatically open the browser. Please navigate to https://claude.ai manually.")

    while True:
        session_key = input("Please enter your sessionKey value: ").strip()
        if session_key:
            config['sessionKey'] = session_key
            save_config(config)
            print(f"SessionKey stored in {CONFIG_FILE}")
            return session_key
        else:
            print("Session key cannot be empty. Please try again.")

def get_or_update_config_value(key, prompt, current_value=None):
    config = get_config()
    stored_value = config.get(key, current_value)

    if stored_value is not None:
        use_stored = input(f"Found stored {key}: {stored_value}. Use it? (y/n): ").strip().lower()
        if use_stored == 'y':
            return stored_value

    while True:
        new_value = input(f"{prompt}: ").strip()
        if new_value:
            config[key] = new_value
            save_config(config)
            print(f"{key} stored in {CONFIG_FILE}")
            return new_value
        elif current_value is not None:
            return current_value
        else:
            print(f"{key} cannot be empty. Please try again.")

if __name__ == "__main__":
    session_key = get_session_key()
    print(f"Session key obtained: {session_key}")