# LinkedIn Profile Scraper

**Scrape LinkedIn Profiles Safely and at Scale with Verified Work Emails.**
*(Email deliverability = less than 3% bounce rate)*

A robust, feature-rich Python CLI tool for scraping LinkedIn profiles using the [Lobstr.io LinkedIn Profile Scraper API](https://www.lobstr.io/store/linkedin-profile-scraper).

## Features

-   **Robust Architecture**: Class-based design with separation of concerns (Logic vs. UI).
-   **Interactive & CLI Modes**: Use interactive prompts or command-line arguments for automation.
-   **Squid Management**: Automatically creates, reuses, and manages Lobstr.io "squids" (scrapers) to optimize resource usage.
-   **Account Management**: Interactive selection of LinkedIn accounts configured in Lobstr.io.
-   **Output Handling**: Automatically downloads results in both JSON and CSV formats with timestamped filenames.
-   **Graceful Exits**: Handles interruptions (`CTRL+C`) cleanly, offering to abort the remote run.
-   **Email Enrichment**: Optional flag to enable email discovery.
-   **Configurable**: Uses `.env` for API keys and class constants for easy tweaking.

## Prerequisites

-   Python 3.7+
-   A [Lobstr.io](https://lobstr.io) account.
-   A LinkedIn account connected to your Lobstr.io account.

## Installation

1.  **Clone the repository** (or copy the files):
    ```bash
    git clone <repository_url>
    cd LiProfileScraper
    ```

2.  **Install dependencies**:
    ```bash
    pip install requests python-dotenv
    ```

3.  **Configuration**:
    Create a `.env` file in the project root:
    ```env
    API_KEY=your_lobstr_api_key_here
    ```

## Usage

You can run the script in **Interactive Mode** or using **CLI Arguments**.

### 1. Interactive Mode
Simply run the script without arguments. It will guide you through selecting a squid, an account, and processing the default `urls.txt` file.

```bash
python main.py
```

### 2. Command-Line Arguments
Automate the process by passing arguments.

| Argument | Description | Example |
| :--- | :--- | :--- |
| `-u`, `--url` | Scrape a single LinkedIn profile URL. | `-u "https://www.linkedin.com/in/williamhgates/"` |
| `-l`, `--list` | Specify an input file containing URLs. Default is `urls.txt`. | `-l my_leads.txt` |
| `-e`, `--email` | Enable email enrichment (consumes more credits). | `--email` |

### Examples

**Scrape a single profile:**
```bash
python main.py -u "https://www.linkedin.com/in/example-profile"
```

**Scrape from a custom file with email enrichment:**
```bash
python main.py -l leads.txt --email
```

**Standard run (uses `urls.txt`):**
```bash
python main.py
```

## Input File Format

The input file (default `urls.txt`) should contain one LinkedIn URL per line:

```text
https://www.linkedin.com/in/person-one
https://www.linkedin.com/in/person-two
https://www.linkedin.com/in/person-three
```

## Output

After a successful run, the tool generates the following in the script directory:

-   **CSV Report**: `results_YYYYMMDD_HHMMSS.csv`
-   **JSON Dump**: `results_YYYYMMDD_HHMMSS.json`
-   **Log File**: `scraper.log` (appended with execution details)

## Project Structure

-   `main.py`: The core script containing business logic (`LiProfileScraper`) and the CLI wrapper (`CLIInterface`).
-   `.env`: Configuration file for API keys (not committed to version control).
-   `scraper.log`: Logs for debugging and tracking.
-   `.squid_id`: Cache file to store the ID of the last used scraper for reuse.

## Error Handling

-   **Interruptions**: Pressing `CTRL+C` will pause the script and ask if you want to abort the run on Lobstr.io's servers as well.
-   **Logging**: All errors and info are logged to `scraper.log` for troubleshooting.
