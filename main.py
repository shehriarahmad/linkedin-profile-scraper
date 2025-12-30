import os
import time
import json
import logging
import requests
import re
import sys
import argparse
from datetime import datetime
from dotenv import load_dotenv

# Determine script directory for robust path handling
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LOG_FILE = os.path.join(SCRIPT_DIR, "scraper.log")

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger("LiProfileScraper")

class LiProfileScraper:
    """
    A class to interact with the Lobstr.io API for LinkedIn profile scraping.
    """
    # Class constants
    LINKEDIN_PROFILE_CRAWLER_ID = "5c11752d8687df2332c08247c4fb655a"
    DEFAULT_INPUT_FILE = "urls.txt"
    CACHE_FILE_NAME = ".squid_id"
    DEFAULT_POLL_INTERVAL = 10  # seconds
    CSV_GENERATION_WAIT = 5  # seconds
    
    def __init__(self):
        # Load environment variables
        load_dotenv()
        self.api_key = os.getenv('API_KEY')
        self.base_url = "https://api.lobstr.io/v1"
        
        # Cache file path
        self.squid_cache_file = os.path.join(SCRIPT_DIR, self.CACHE_FILE_NAME)
        
        # Centralized configuration check
        if not self.api_key:
            logger.error("Missing API_KEY in environment variables.")
            raise ValueError("Configuration error: Check your .env file for API_KEY.")
            
        self.headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": "application/json"
        }

    # ====================
    # SQUID MANAGEMENT
    # ====================
    
    def create_squid(self):
        """Creates a new squid for the specified crawler."""
        logger.info(f"Creating new squid for crawler {self.LINKEDIN_PROFILE_CRAWLER_ID}...")
        url = f"{self.base_url}/squids"
        try:
            response = requests.post(url, headers=self.headers, json={"crawler": self.LINKEDIN_PROFILE_CRAWLER_ID})
            response.raise_for_status()
            squid_id = response.json().get('id')
            logger.info(f"Squid created successfully: {squid_id}")
            return squid_id
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to create squid: {e}")
            raise

    def update_squid(self, squid_hash, account_id, enrich_email=False):
        """Updates squid settings with required parameters."""
        logger.info(f"Updating squid {squid_hash} settings with account {account_id} (Email: {enrich_email})...")
        url = f"{self.base_url}/squids/{squid_hash}"
        payload = {
            "accounts": [account_id],
            "no_line_breaks": True,
            "params": {"functions": {"email": enrich_email}}
        }
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            logger.info(f"Squid {squid_hash} updated successfully.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to update squid {squid_hash}: {e}")
            raise

    def empty_squid(self, squid_hash):
        """Empties the squid of all URLs."""
        logger.info(f"Emptying squid {squid_hash}...")
        url = f"{self.base_url}/squids/{squid_hash}/empty"
        try:
            response = requests.post(url, headers=self.headers, json={"type": "url"})
            response.raise_for_status()
            logger.info(f"Squid {squid_hash} emptied successfully.")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to empty squid {squid_hash}: {e}")
            raise

    def delete_squid(self, squid_hash):
        """Deletes a squid."""
        logger.info(f"Deleting squid {squid_hash}...")
        url = f"{self.base_url}/squids/{squid_hash}"
        try:
            response = requests.delete(url, headers=self.headers)
            response.raise_for_status()
            logger.info(f"Squid {squid_hash} deleted successfully.")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to delete squid {squid_hash}: {e}")
            raise

    def list_squids(self):
        """Lists all squids."""
        logger.info("Listing squids...")
        url = f"{self.base_url}/squids"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Fetched {len(data.get('data', []))} squids.")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to list squids: {e}")
            raise

    def get_linkedin_squids(self):
        """Returns only LinkedIn Profile Scraper squids."""
        squids_data = self.list_squids()
        all_squids = squids_data.get('data', [])
        return [s for s in all_squids if s.get('crawler') == self.LINKEDIN_PROFILE_CRAWLER_ID]

    # ====================
    # ACCOUNT MANAGEMENT
    # ====================

    def list_accounts(self):
        """Lists available accounts."""
        logger.info("Listing accounts...")
        url = f"{self.base_url}/accounts"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Fetched {len(data.get('data', []))} accounts.")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to list accounts: {e}")
            raise

    def get_linkedin_accounts(self):
        """Returns only LinkedIn sync accounts."""
        accounts_data = self.list_accounts()
        all_accounts = accounts_data.get('data', [])
        return [a for a in all_accounts if a.get('type') == 'linkedin-sync']

    # ====================
    # TASK MANAGEMENT
    # ====================

    def add_tasks(self, squid_hash, input_source, is_file=True):
        """Reads URLs from file OR uses single URL, and adds them to the squid."""
        urls = []
        if is_file:
            # Handle file input (absolute path)
            file_path = os.path.join(SCRIPT_DIR, input_source)
            if not os.path.exists(file_path):
                logger.error(f"Task file not found: {file_path}")
                raise FileNotFoundError(f"File {file_path} not found.")

            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    urls = [line.strip() for line in f if line.strip()]
            except IOError as e:
                logger.error(f"Error reading {file_path}: {e}")
                raise
        else:
            # Handle single URL input
            if input_source and input_source.strip():
                urls = [input_source.strip()]
        
        if not urls:
            logger.warning("No URLs found to process.")
            return 0

        logger.info(f"Adding {len(urls)} tasks to squid {squid_hash}...")
        url = f"{self.base_url}/tasks"
        payload = {"tasks": [{"url": u} for u in urls], "squid": squid_hash}
        try:
            response = requests.post(url, headers=self.headers, json=payload)
            response.raise_for_status()
            logger.info(f"Successfully added {len(urls)} tasks.")
            return len(urls)
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to add tasks: {e}")
            raise

    # ====================
    # RUN MANAGEMENT
    # ====================

    def abort_run(self, run_hash):
        """Aborts a running squid execution."""
        logger.info(f"Aborting run {run_hash}...")
        url = f"{self.base_url}/runs/{run_hash}/abort"
        try:
            response = requests.post(url, headers=self.headers)
            response.raise_for_status()
            logger.info(f"Run {run_hash} aborted successfully.")
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to abort run {run_hash}: {e}")
            raise

    def run_and_poll(self, squid_hash):
        """Starts a run and polls for completion."""
        logger.info(f"Starting run for squid {squid_hash}...")
        url = f"{self.base_url}/runs"
        try:
            response = requests.post(url, headers=self.headers, json={"squid": squid_hash})
            response.raise_for_status()
            run_hash = response.json().get('id')
            logger.info(f"Run started: {run_hash}")
            
            stats_url = f"{self.base_url}/runs/{run_hash}/stats"
            while True:
                try:
                    res = requests.get(stats_url, headers=self.headers)
                    res.raise_for_status()
                    stats = res.json()
                    percent = stats.get('percent_done', 0)
                    logger.info(f"Progress: {percent}% done...")
                    
                    if stats.get('is_done'):
                        logger.info("Run completed.")
                        break
                    time.sleep(self.DEFAULT_POLL_INTERVAL)
                except KeyboardInterrupt:
                    print("\n[!] Execution interrupted by user.")
                    choice = input("Abort the remote run as well? (y/N): ").strip().lower()
                    if choice == 'y':
                        self.abort_run(run_hash)
                    else:
                        logger.info("Exiting script without aborting run.")
                    raise  # Re-raise to exit script
            return run_hash
        except requests.exceptions.RequestException as e:
            logger.error(f"Error during run or polling: {e}")
            raise

    # ====================
    # RESULTS MANAGEMENT
    # ====================

    def fetch_results(self, run_hash):
        """Retrieves and returns the results of a run."""
        logger.info(f"Fetching results for run {run_hash}...")
        url = f"{self.base_url}/results"
        try:
            response = requests.get(url, headers=self.headers, params={"run": run_hash})
            response.raise_for_status()
            data = response.json()
            logger.info(f"Fetched {len(data)} results.")
            return data
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch results: {e}")
            raise

    def save_to_json(self, data, filename=None):
        """Saves data to a JSON file with an optional timestamped name."""
        if not filename:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"results_{timestamp}.json"
        
        # Ensure path is absolute
        file_path = os.path.join(SCRIPT_DIR, filename)
            
        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            logger.info(f"Successfully saved {len(data)} profiles to {file_path}")
        except IOError as e:
            logger.error(f"Failed to save data to {file_path}: {e}")
            raise

    def download_csv(self, run_hash, filename=None):
        """Downloads the results as CSV."""
        logger.info(f"Initiating CSV download for run {run_hash}...")
        url = f"{self.base_url}/runs/{run_hash}/download"
        try:
            response = requests.get(url, headers=self.headers)
            response.raise_for_status()
            s3_url = response.json().get('s3')
            
            if not s3_url:
                logger.error("No S3 URL returned for CSV download.")
                return

            logger.info(f"Waiting {self.CSV_GENERATION_WAIT} seconds for CSV generation...")
            time.sleep(self.CSV_GENERATION_WAIT)
            
            # Download file content
            csv_response = requests.get(s3_url)
            csv_response.raise_for_status()
            
            if not filename:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"results_{timestamp}.csv"
            
            # Ensure path is absolute
            file_path = os.path.join(SCRIPT_DIR, filename)

            with open(file_path, 'wb') as f:
                f.write(csv_response.content)
            logger.info(f"Successfully downloaded CSV to {file_path}")
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to download CSV: {e}")
            raise
        except IOError as e:
            logger.error(f"Failed to save CSV file: {e}")
            raise

    # ====================
    # UTILITY METHODS
    # ====================

    def _cache_squid_id(self, squid_id):
        """Helper to write squid ID to cache."""
        try:
            with open(self.squid_cache_file, 'w') as f:
                f.write(squid_id)
        except IOError as e:
            logger.warning(f"Failed to write squid cache: {e}")


# ====================
# CLI INTERFACE
# ====================

class CLIInterface:
    """Handles all interactive command-line prompts and user interaction."""
    
    def __init__(self, scraper):
        self.scraper = scraper
    
    def prompt_squid_selection(self):
        """Interactively allows the user to choose an existing squid or create a new one."""
        squids = self.scraper.get_linkedin_squids()
        
        if not squids:
            logger.info("No existing LinkedIn squids found. Creating a new one.")
            new_id = self.scraper.create_squid()
            self.scraper._cache_squid_id(new_id)
            return new_id, True

        print("\n--- Available LinkedIn Squids ---")
        for idx, squid in enumerate(squids):
            print(f"[{idx + 1}] ID: {squid.get('id')} | Name: {squid.get('name')} | Created: {squid.get('created_at')}")
        print("[N] Create New Squid")
        print("---------------------------------")

        choice = input("Select a Squid (number) or 'N' for new: ").strip().lower()

        if choice == 'n':
            new_id = self.scraper.create_squid()
            self.scraper._cache_squid_id(new_id)
            return new_id, True
        
        try:
            selection_idx = int(choice) - 1
            if 0 <= selection_idx < len(squids):
                selected_id = squids[selection_idx].get('id')
                logger.info(f"Selected existing squid: {selected_id}")
                self.scraper._cache_squid_id(selected_id)
                return selected_id, False
            else:
                print("Invalid selection. Creating new squid.")
                new_id = self.scraper.create_squid()
                self.scraper._cache_squid_id(new_id)
                return new_id, True
        except ValueError:
            print("Invalid input. Creating new squid.")
            new_id = self.scraper.create_squid()
            self.scraper._cache_squid_id(new_id)
            return new_id, True

    def prompt_account_selection(self):
        """Interactively allows the user to choose an account."""
        accounts = self.scraper.get_linkedin_accounts()
        
        if not accounts:
            logger.error("No LinkedIn accounts found. Please add a LinkedIn account on Lobstr.io first.")
            raise ValueError("No LinkedIn accounts available.")

        # If only one account, auto-select it
        if len(accounts) == 1:
            acc = accounts[0]
            logger.info(f"Auto-selecting only available LinkedIn account: {acc.get('username')}")
            return acc.get('id')

        print("\n--- Available Accounts ---")
        for idx, acc in enumerate(accounts):
            print(f"[{idx + 1}] ID: {acc.get('id')} | Username: {acc.get('username')} | Type: {acc.get('type')}")
        print("--------------------------")

        while True:
            choice = input("Select an Account (number): ").strip()
            try:
                selection_idx = int(choice) - 1
                if 0 <= selection_idx < len(accounts):
                    selected_id = accounts[selection_idx].get('id')
                    logger.info(f"Selected account: {selected_id}")
                    return selected_id
                else:
                    print("Invalid selection. Try again.")
            except ValueError:
                print("Invalid input. Please enter a number.")

    def prompt_empty_squid(self, squid_hash):
        """Prompts user to empty an existing squid."""
        confirm = input("Empty existing tasks from this Squid? (y/N): ").lower()
        if confirm == 'y':
            self.scraper.empty_squid(squid_hash)

    def run_interactive_scrape(self, input_source, is_file, enrich_email):
        """Orchestrates the scraping process with interactive prompts."""
        try:
            # 1. Choose Squid (Reuse or New)
            s_hash, is_new = self.prompt_squid_selection()
            
            # 2. Choose Account
            account_id = self.prompt_account_selection()
            
            # 3. Update Squid with selected account
            self.scraper.update_squid(s_hash, account_id, enrich_email=enrich_email)

            # 4. Prompt to empty if reusing
            if not is_new:
                self.prompt_empty_squid(s_hash)
            
            # 5. Add Tasks
            count = self.scraper.add_tasks(s_hash, input_source, is_file=is_file)
            if count == 0:
                logger.info("Nothing to process. Exiting.")
                return

            # 6. Run & Export
            r_hash = self.scraper.run_and_poll(s_hash)
            final_data = self.scraper.fetch_results(r_hash)
            self.scraper.save_to_json(final_data)
            
            # 7. CSV Export
            self.scraper.download_csv(r_hash)
            
        except Exception as e:
            logger.critical(f"Scraper execution failed: {e}")


# ====================
# MAIN ENTRY POINT
# ====================

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="LinkedIn Profile Scraper using Lobstr.io")
    parser.add_argument('-u', '--url', type=str, help="Single LinkedIn profile URL to scrape")
    parser.add_argument('-l', '--list', type=str, default='urls.txt', help="File containing list of URLs (default: urls.txt)")
    parser.add_argument('-e', '--email', action='store_true', help="Enable email enrichment")
    
    args = parser.parse_args()

    # Determine input source
    if args.url:
        input_src = args.url
        is_file_input = False
    else:
        input_src = args.list
        is_file_input = True

    scraper = LiProfileScraper()
    cli = CLIInterface(scraper)
    
    try:
        cli.run_interactive_scrape(input_source=input_src, is_file=is_file_input, enrich_email=args.email)
    except KeyboardInterrupt:
        logger.info("Script execution interrupted by user (Exit).")
        sys.exit(0)
