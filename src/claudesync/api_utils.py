import sys
import requests

def fetch_user_id(session_key):
    url = "https://claude.ai/api/bootstrap"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://claude.ai/',
        'Origin': 'https://claude.ai',
        'Connection': 'keep-alive'
    }
    cookies = {'sessionKey': session_key}

    try:
        response = requests.get(url, headers=headers, cookies=cookies)
        response.raise_for_status()
        data = response.json()
        return data['account']['memberships'][0]['organization']['uuid']
    except (requests.RequestException, KeyError, IndexError) as e:
        print(f"Error fetching user ID: {str(e)}")
        sys.exit(1)

def fetch_projects(user_id, session_key):
    url = f"https://claude.ai/api/organizations/{user_id}/projects"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://claude.ai/',
        'Origin': 'https://claude.ai',
        'Connection': 'keep-alive'
    }
    cookies = {'sessionKey': session_key, 'lastActiveOrg': user_id}

    try:
        response = requests.get(url, headers=headers, cookies=cookies)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error fetching projects: {str(e)}")
        sys.exit(1)

def select_project(projects):
    print("Available projects:")
    for i, project in enumerate(projects, 1):
        print(f"{i}. {project['name']} (ID: {project['uuid']})")

    while True:
        try:
            choice = int(input("Enter the number of the project you want to use: "))
            if 1 <= choice <= len(projects):
                return projects[choice - 1]['uuid']
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")