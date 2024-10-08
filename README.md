# K-1 tax communications

A dynamic system to email K-1 PDFs to investors.

## About
Every tax year we need to send hundreds of K-1 tax forms to investors. We receive these forms from our external accountants. This project automates the process of matching K-1 PDFs to an internal investor contact table and then emailing the attachments with an interpolated email body. The emails are sent via the Outlook API.

## Code structure
- [`k1_processor.py`](k1_processor.py): Contains the `K1BatchProcessor` class that handles all the work
- [`main.py`](main.py): Entry point
- `config.py`: Set running parameters here for each code run (not tracked due to constant changing, but can be recreated from [`config.pytemplate`](config.pytemplate))
- [`auth.py`](auth.py): Microsoft API authentication (more on this below)
- [`logger.py`](logger.py): Logging configuration

Inside the entry point, you can choose which of the external methods get run. The methods are called from outside the class to allow for step-by-step processing, instead of being forced to run everything in one shot. This is specifically built in as a safeguard because emailing investors and handling tax data is extremely sensitive.

## Usage
1. Manually copy K-1 PDFs into the `files` directory into their respective investment folders.
2. Ensure `investors.xlsx` contains correct investor information.
3. Set running parameters in `config.py`, which get imported into the entry point (create `config.py` from [`config.pytemplate`](config.pytemplate) if it does not exist). See the `__init__()` method of `K1BatchProcessor` docstring for explanations of how to set the config parameters.
4. Instantiating the `K1BatchProcessor` class in the entry point (ensures the correct folder structure as explained below and) gathers the K-1s from the folders to prepare for processing. "Managers" K-1s are excluded as they are not emailed to investors.
5. The `extract_entities()` method reads the PDFs and attempts to extract the issuing entity and receiving entity from each. These are stored in a `pickle` cache to speed up future runs on the same files (in the case of staggered emailing or testing or any other required re-run). The cache will be loaded if it exists, otherwise extraction will be run on all gathered files.
6. The `match_files_and_keys()` method attempts to match the extracted entity information from each file to an investor contact in `investors.xlsx` to prepare for emailing.
7. The `send_emails()` method sends emails with K-1 attachments to the matched investors. You will be prompted to `(y/n)` confirm that you want to send emails (another safeguard).

## Additional information

### Directory structure
*These directories and their contents are not tracked, however `logs`, `snapshots`, and `investors.xlsx` are synced to S3.*
- `cache`: Contains a single file `pickle` cache of extracted entities from each K-1 file
- `dumps`: Stores text files of the extracted text from each K-1 page
- `files`: Contains folders for each investment, holding the K-1 PDFs
- `logs`: Stores text logs of standard output (print statements, etc.) from code runs, and csv logs of unmatched files
- `snapshots`: Stores snapshots of `investors.xlsx` as backups

### Logs
- Every time the class is instantiated, a timestamped snapshot of `investors.xlsx` is stored inside the `snapshots` directory for safety
- A timestamped text file is stored inside the `logs` directory, containing the standard output from every code run. The `print_k1_array()` method can be called to include appending of the `k1_array` (i.e., result of the `extract_entities()` method) to this log file. This will not print the `k1_array` to the terminal to avoid crowding
- A timestamped csv file is stored inside the `logs` directory whenever `extract_entities()` is called, containing a table of the K-1 files that did not match to any investor contacts within `investors.xlsx`
- A timestamped csv file is stored inside the `logs` directory whenever `sent_emails()` is run, containing all attempted investor rows along with the sent status and timestamp

### S3 sync
The `logs` directory, `snapshots` directory, and `investors.xlsx` file are synced to S3 whenever changes are made to them. These changes are kept track of during code runs using instance variables as flags (e.g., `self.logs_changed`).

### Authentication
As mentioned, emails are sent via the Outlook API, which uses the `msal` package for authentication inside `auth.py`. The credentials that are fed to `msal` are stored in AWS Parameter Store (we are only using Azure at all because it is required to use the Outlook API, but AWS is our cloud platform). Thus, your environment needs to be configured with AWS credentials in order for the Outlook API to be authenticated.