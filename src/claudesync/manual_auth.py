import webbrowser

def get_session_key():
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

    # Attempt to open the Claude.ai website for the user
    try:
        webbrowser.open("https://claude.ai")
    except:
        print("Unable to automatically open the browser. Please navigate to https://claude.ai manually. ")

    while True:
        session_key = input("Please enter your sessionKey value: ").strip()
        if session_key:
            return session_key
        else:
            print("Session key cannot be empty. Please try again.")

if __name__ == "__main__":
    session_key = get_session_key()
    print(f"Session key obtained: {session_key}")
