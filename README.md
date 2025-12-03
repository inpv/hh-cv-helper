# hh-cv-helper

This project automates the process of checking and publishing resumes on HeadHunter (HH.ru). It leverages the HH OAuth2 API and provides a command-line interface (CLI) to manage resume updates.

## Project Structure

*   **`src/`**: Contains the core Python modules:
    *   `hh_client.py`:  Handles OAuth2 authentication, API interactions (fetching, publishing resumes), and token management.
    *   `main.py`: The main script that parses arguments, loads resume IDs, checks for updates, and publishes resumes.
*   **`app.py`**: A Flask application used for the initial OAuth2 authentication flow.  It redirects the user to HH for authorization and handles the callback.
*   **`default_resumes.json`**: An example file containing a list of resume IDs.  You should replace this with your own file called `resumes.json`.
*   **`requirements.txt`**:  Lists the project's dependencies.
*   `.env`: (Optional) Environment variables for sensitive information (client ID, client secret).

## Installation

1.  **Create a virtual environment (recommended):**

    ```bash
    python3 -m venv .venv
    source .venv/bin/activate  # Linux/macOS
    .venv\Scripts\activate  # Windows
    ```

2.  **Install dependencies:**

    ```bash
    pip install -r requirements.txt
    ```

## Configuration

1.  **HeadHunter Application Credentials:**

    *   You need to register an application on HeadHunter to obtain a `client_id` and `client_secret`.  Go to [https://dev.hh.ru/](https://dev.hh.ru/) to register your app. Choose "Web application" as the app type and set a `redirect_uri` (e.g., `http://localhost:5000/callback`).
    *   Set the following environment variables:

        *   `HH_CLIENT_ID`: Your HeadHunter application's client ID.
        *   `HH_CLIENT_SECRET`: Your HeadHunter application's client secret.

2.  **Environment Variables:**

    *   `HH_REDIRECT_URI`: The redirect URI you configured in your HeadHunter application. Defaults to `http://localhost:5000/callback`.
    *   `HH_TOKENS_PATH`:  The path to the file where tokens are stored. Defaults to `~/.config/hh-bot/tokens.json`.
    *   `HH_DRY_RUN`: If set to "1" (or any truthy value), the script will run in dry-run mode, simulating publications without actually making any changes.  Defaults to "1". Can be changed with command line argument `--dry-run`.
    *   `HH_UPDATE_THRESHOLD_HOURS`: Sets the threshold in hours for when a resume should be updated. Defaults to 4 hours. Can be changed with command line argument `--threshold-hours`.

3.  **Resumes List:**

    *   Create a JSON file (e.g., `resumes.json`) listing the resume IDs you want to manage. The file should contain a JSON array of objects, each with an `id` and a `name` key.
    *   You also need to specify the resume file location using the `--resume-ids` command-line argument.

## Usage

1. **Running the Resume Updater:**

    ```bash
    python main.py --resume-ids path/to/your/resumes.json
    ```

    *   Replace `path/to/your/resumes.json` with the actual path to your resumes file.
    *   To run in dry-run mode (simulating publications):

        ```bash
        python main.py --resume-ids path/to/your/resumes.json --dry-run
        ```

    *   To set a different update threshold:

        ```bash
        python main.py --resume-ids path/to/your/resumes.json --threshold-hours 24
        ```
2. **Initial Authentication:**
    *   If there has been no initial authorization yet, `python app.py` will automatically be launched in a separate process.
    *   The `python app.py` command will be run. It will start a Flask web server on `localhost:5000`.
    *   Open a web browser and go to `http://localhost:5000/`.
    *   Click the "Authorize HeadHunter" link.  This will redirect you to HH for authorization.
    *   After authorizing, HH will redirect you back to `http://localhost:5000/callback`.  The tokens will be saved to the `HH_TOKENS_PATH` file.
    *   Terminate the `app.py` process.  It's only needed for the initial authentication.
    *   If the tokens become invalid at the next moment of launch, they will be automatically refreshed.
    *   The main process will be executed afterwards.

## Deployment on a headless machine (e.g., Raspberry Pi)

TBA

**Scheduling (Optional):**

    *   If you want to run the script automatically at regular intervals, you can use `cron`.  Edit the crontab:

        ```bash
        crontab -e
        ```

        Add a line like this to run the script every day at 3:00 AM:

        ```
        0 3 * * * /usr/bin/python3 /path/to/your/project/main.py --resume-ids /path/to/your/resumes.json
        ```

## Notes

*   The Flask app (`app.py`) is only needed for the initial OAuth2 authentication flow. Once the tokens are saved, you can stop the Flask server.
*   The `HH_TOKENS_PATH` environment variable determines where the tokens are stored.  Make sure this path is writable by the user running the script.
