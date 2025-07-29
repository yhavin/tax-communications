# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a K-1 tax communications system that automates the process of emailing K-1 tax forms to investors. The system matches K-1 PDFs to investor contacts and sends personalized emails via the Outlook API.

## Key Components

- `main.py`: Entry point that orchestrates the workflow
- `k1_processor.py`: Core `K1BatchProcessor` class handling PDF processing, entity extraction, matching, and email sending
- `config.py`: Runtime configuration (create from `config.pytemplate`)
- `auth.py`: Microsoft Outlook API authentication using MSAL
- `logger.py`: Logging configuration
- `investors.xlsx`: Master investor contact database

## Running the System

The primary workflow is executed through `main.py`:

```bash
python main.py
```

Before running, ensure:
1. `config.py` exists (copy from `config.pytemplate` and configure)
2. K-1 PDFs are placed in `files/` directory organized by investment folders
3. `investors.xlsx` contains current investor data
4. AWS credentials are configured for authentication

## Configuration

Create `config.py` from `config.pytemplate` with these required parameters:
- `sender`: Email address sending the communications
- `internal_recipients`: List of internal emails to CC/BCC
- `tax_year`: Target tax year (YYYY format)
- `test_mode`: Boolean for safety (sends to sender only when True)
- `email_limit`: Optional limit for testing
- `skip_cache_load`: Boolean to bypass entity extraction cache
- `run_send_emails`: Boolean to control email sending

## Data Flow

1. **Initialization**: Creates directory structure, loads investor data
2. **Entity Extraction**: Extracts issuing/receiving entities from K-1 PDFs (cached in `cache/`)
3. **Matching**: Maps extracted entities to investor contacts
4. **Email Sending**: Sends personalized emails with K-1 attachments

## Key Directories

- `files/`: K-1 PDFs organized by investment folders
- `cache/`: Pickle cache of extracted PDF entities
- `logs/`: Execution logs and unmatched file reports
- `snapshots/`: Backup copies of `investors.xlsx`
- `dumps/`: Text extracts from PDF processing

## Dependencies

Key Python packages:
- `pandas`: Data manipulation for investor records
- `pdfplumber`: PDF text extraction
- `msal`: Microsoft authentication
- `requests`: HTTP operations for Outlook API
- `boto3`: AWS services (Parameter Store for credentials)

## Safety Features

- Test mode redirects all emails to sender
- Manual confirmation required before sending emails
- Automatic snapshots of investor data before runs
- Comprehensive logging of all operations
- Step-by-step execution allowing manual intervention

## Authentication

Uses Microsoft Graph API with credentials stored in AWS Parameter Store. Requires proper AWS configuration for credential retrieval.

## S3 Integration

Automatically syncs logs, snapshots, and investor data to S3 when changes occur during processing.