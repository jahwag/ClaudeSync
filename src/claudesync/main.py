import argparse
import sys
import time
from watchdog.observers import Observer

from file_handler import FileUploadHandler
from api_utils import fetch_user_id, fetch_projects, select_project
from manual_auth import get_session_key

def main():
    parser = argparse.ArgumentParser(description="Sync local files with Claude.ai projects.")
    parser.add_argument("--session-key", help="Session key for authentication")
    parser.add_argument("--watch-dir", default=".", help="Directory to watch for changes")
    parser.add_argument("--user-id", help="User ID for Claude API (optional, will be fetched if not provided)")
    parser.add_argument("--project-id", help="Project ID for Claude API")
    parser.add_argument("--delete-all", action="store_true", help="Delete all documents in the project")
    parser.add_argument("--delay", type=int, default=5, help="Delay in seconds before uploading (default: 5)")
    args = parser.parse_args()

    if not args.session_key:
        print("No session key provided. Please follow the instructions to obtain your session key.")
        args.session_key = get_session_key()

    if not args.user_id:
        print("User ID not provided. Fetching from Claude API...")
        args.user_id = fetch_user_id(args.session_key)
        print(f"User ID fetched: {args.user_id}")

    if not args.project_id:
        print("Project ID not provided. Fetching available projects...")
        projects = fetch_projects(args.user_id, args.session_key)
        args.project_id = select_project(projects)

    api_endpoint = f"https://claude.ai/api/organizations/{args.user_id}/projects/{args.project_id}/docs"

    handler = FileUploadHandler(api_endpoint, args.session_key, args.watch_dir, args.delay)

    if args.delete_all:
        handler.delete_all_documents()
        print("All documents deleted.")
        sys.exit(0)
    else:
        print(f"Watching directory: {args.watch_dir}")
        print(f"Upload delay: {args.delay} seconds")
        observer = Observer()
        observer.schedule(handler, args.watch_dir, recursive=True)
        observer.start()
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
        observer.join()

if __name__ == "__main__":
    main()