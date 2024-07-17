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

def select_project(projects, user_id, session_key):
    # Filter out archived projects
    active_projects = [project for project in projects if project.get('archived_at') is None]

    print("Available projects:")
    for i, project in enumerate(active_projects, 1):
        print(f"{i}. {project['name']} (ID: {project['uuid']})")
    print(f"{len(active_projects) + 1}. Create new project")

    while True:
        try:
            choice = int(input("Enter the number of the project you want to use (or create new): "))
            if 1 <= choice <= len(active_projects):
                return active_projects[choice - 1]['uuid']
            elif choice == len(active_projects) + 1:
                name = input("Enter the name for the new project: ")
                description = input("Enter a description for the new project (optional): ")
                new_project = create_project(user_id, session_key, name, description)
                print(f"New project created: {new_project['name']} (ID: {new_project['uuid']})")
                return new_project['uuid']
            else:
                print("Invalid choice. Please try again.")
        except ValueError:
            print("Invalid input. Please enter a number.")

def create_project(user_id, session_key, name, description):
    url = f"https://claude.ai/api/organizations/{user_id}/projects"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:128.0) Gecko/20100101 Firefox/128.0',
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.5',
        'Referer': 'https://claude.ai/',
        'Origin': 'https://claude.ai',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json'
    }
    cookies = {'sessionKey': session_key, 'lastActiveOrg': user_id}
    payload = {
        "name": name,
        "description": description,
        "is_private": True
    }

    try:
        response = requests.post(url, headers=headers, cookies=cookies, json=payload)
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        print(f"Error creating project: {str(e)}")
        sys.exit(1)