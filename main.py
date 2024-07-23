"""
Main module for K-1 tax communications processing.

Author: Yakir Havin
"""


import base64
import json
import os
import pickle
import re
import shutil
import warnings
warnings.simplefilter(action="ignore", category=FutureWarning)  # Suppress erroneous FutureWarning
from typing import Optional

import requests
import pandas as pd
import pdfplumber

import auth
from logger import logger


class K1BatchProcessor:
    def __init__(self, *, tax_year: str, test_mode: bool=True, email_limit: Optional[int]=None):
        self.tax_year = tax_year
        self.test_mode = test_mode
        self.email_limit = email_limit
        print(f"START: tax_year={self.tax_year}, test_mode={self.test_mode}, email_limit={self.email_limit}\n")

        self._ensure_directory_structure()
        self._save_investors_snapshot()

        self.k1_array = []
        self.cache = "k1_array_cache.pkl"
        self._load_cache()
        self._gather_files()

    def _ensure_directory_structure(self):
        """Ensure required directories exist."""
        directories = ["cache", "dumps", "logs", "queue", "snapshots"]

        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)

    def _save_investors_snapshot(self):
        """Create snapshots of investors.xlsx before any changes get made."""
        try:
            shutil.copy("investors.xlsx", os.path.join("snapshots", f"investors_{logger.timestamp}.xlsx"))
        except FileNotFoundError as e:
            print(e)

    def _load_cache(self):
        """Attempt to load K-1 entity array from cache."""
        if os.path.exists(os.path.join("cache", self.cache)):
            with open(os.path.join("cache", self.cache), "rb") as f:
                self.k1_array = pickle.load(f)
            print(f"CACHE: Loaded {len(self.k1_array)} items\n")
        else:
            print("CACHE: Not found\n")

    def _save_cache(self):
        """Save K-1 entity array to cache."""
        with open(os.path.join("cache", self.cache), "wb") as f:
            pickle.dump(self.k1_array, f)
        print(f"\nCACHE: Saved {len(self.k1_array)} items\n")
        
    def _gather_files(self):
        """Gather K-1 PDFs from input folder."""
        root_folder_path = "files"
        new_k1_files = []

        for asset_folder in os.listdir(root_folder_path):
            asset_folder_path = os.path.join(root_folder_path, asset_folder)
            if os.path.isdir(asset_folder_path):
                for file in os.listdir(asset_folder_path):
                    if file.lower().endswith(".pdf"):
                        if "managers" in file.lower():
                            continue
                        file_path = f"{asset_folder}/{file}"
                        if not any(k1["path"] == file_path for k1 in self.k1_array):
                            new_k1_files.append({
                                "path": f"{asset_folder}/{file}",
                                "investment_name": asset_folder,
                                "issuing_entity": None,
                                "receiving_entity": None
                            })

        self.k1_array.extend(new_k1_files)
        print("GATHER:", f"{len(self.k1_array)} K-1 files ({len(new_k1_files)} new)\n")

    def extract_entities(self):
        """Attempt to extract issuing and receiving entity from PDFs."""
        k1_files_to_extract = [k1_info for k1_info in self.k1_array if k1_info["issuing_entity"] is None and k1_info["receiving_entity"] is None]

        for index, k1_info in enumerate(k1_files_to_extract):
            print(f"EXTRACT {index + 1:03}: {k1_info["path"]}")
            file_path = os.path.join("files", k1_info["path"])
            with pdfplumber.open(file_path) as pdf:
                for page_number, page in enumerate(pdf.pages):
                    text = page.extract_text()
                    if "Schedule K-1 (Form 1065)" in text:
                        lines = text.splitlines()
                        for line_number, line in enumerate(lines):
                            if "Part I Information About the Partnership" in line:
                                issuing_entity = lines[line_number + 3].strip()
                                k1_info["issuing_entity"] = issuing_entity
                            if "Part II Information About the Partner" in line:
                                receiving_entity_index = line_number + 3
                                receiving_entity = lines[receiving_entity_index].strip()
                                if re.search(r"\bst\b", receiving_entity.lower()) or re.search(r"\bstreet\b", receiving_entity.lower()):  # Off-by-one line error
                                    receiving_entity = lines[receiving_entity_index - 1].strip()
                                k1_info["receiving_entity"] = receiving_entity
                        break  # Stop checking pages after K-1 is found

        self._save_cache()           
        print("ISSUING:", len([item for item in self.k1_array if item["issuing_entity"] is not None]), "entities")
        print("RECEIVING:", len([item for item in self.k1_array if item["receiving_entity"] is not None]), "entities")

    def print_k1_array(self):
        """Output K-1 array in pretty-print format."""
        logger.write(json.dumps(self.k1_array, indent=2), print_to_terminal=False)

    def create_matching_keys(self):
        """Create keys to match PDFs to investors table."""
        stop_characters_translation_table = str.maketrans({
            " ": "",
            ".": "",
            ",": ""
        })

        for k1_info in self.k1_array:
            k1_info["k1_matching_key"] = f"{k1_info["investment_name"]}#{k1_info["issuing_entity"]}#{k1_info["receiving_entity"]}".lower().translate(stop_characters_translation_table)

        print(f"MAKE KEYS: {len(self.k1_array)} files")

    def match_files_and_keys(self):
        """Match K-1 files to investors."""
        investors_df = pd.read_excel("investors.xlsx", converters={"email_batch_timestamp": str})

        k1_matching_key_df = pd.DataFrame(self.k1_array)
        k1_matching_key_df = k1_matching_key_df.sort_values(by=["investment_name", "receiving_entity"])
        print("\nK-1 FILES:\n", k1_matching_key_df["investment_name"].value_counts(sort=False))
        
        merged_df = pd.merge(investors_df, k1_matching_key_df, on="k1_matching_key", how="left", suffixes=("", "_from_pdf"))
        merged_df["matched_k1_filename"] = merged_df["path"]
        merged_df = merged_df.sort_values(by=["investment_name", "receiving_entity"])
        print("\nMATCHED ROWS (may contain duplicate matches):\n", merged_df[merged_df["matched_k1_filename"].notna()]["investment_name"].value_counts(sort=False).rename(index=str.upper), "\n")

        unmatched_k1_files_df = k1_matching_key_df[~k1_matching_key_df["k1_matching_key"].isin(merged_df["k1_matching_key"])].sort_values(by="path")
        print("UNMATCHED FILES:", len(unmatched_k1_files_df), "\n")
        print(f"MATCH SUCCESS: {1 - (len(unmatched_k1_files_df) / len(k1_matching_key_df)):.2%}\n")
        unmatched_k1_files_df.to_csv(os.path.join("logs", f"unmatched_{logger.timestamp}.csv"), index=False)

        merged_df = merged_df.drop(columns=["path", "investment_name_from_pdf", "issuing_entity_from_pdf", "receiving_entity_from_pdf"], axis=1)
        merged_df["email_status"] = merged_df.apply(
            lambda row: "file_found" if pd.notna(row["matched_k1_filename"]) and pd.isna(row["email_status"]) else row["email_status"],
            axis=1
        )

        merged_df.to_excel("investors.xlsx", index=False)  # Update main table with filename and status columns

        merged_df = merged_df[merged_df["matched_k1_filename"].notna()]
        merged_df.to_csv(os.path.join("queue", f"matched_{logger.timestamp}.csv"), index=False)  # For logging

    def send_emails(self):
        """Email K-1 PDFs to investors."""
        investors_df = pd.read_excel("investors.xlsx")
        investors_df["active"] = investors_df["active"].apply(lambda value: False if pd.isna(value) or value == "nan" else bool(value))
        investors_df["do_not_send_override"] = investors_df["do_not_send_override"].apply(lambda value: False if pd.isna(value) or value == "nan" else bool(value))

        conditions = (
            (investors_df["matched_k1_filename"].notna()) & 
            (investors_df["active"] == True) &
            (investors_df["do_not_send_override"] == False) &
            (investors_df["email_status"] != "sent")
        )

        investors_to_send_df = investors_df[conditions]

        access_token = auth.get_msal_access_token(*auth.get_msal_credentials())

        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {access_token}"
        }

        base_url = "https://graph.microsoft.com/v1.0"
        sender = "yhavin@beitel.com"
        api_url = f"{base_url}/users/{sender}/sendMail"

        for index, investor in enumerate(investors_to_send_df.itertuples(index=True, name="Investor")):
            if self.email_limit is not None and index >= self.email_limit:
                break

            subject = f"{investor.investment_name} K-1 - Tax Year {self.tax_year} - {investor.receiving_entity}"
            content = f"""
Dear {investor.first_name},
            
I hope this email finds you well.

I am pleased to inform you that your K-1 forms for the tax year {self.tax_year} are now ready. These documents detail your proportionate share of income, deductions, credits, and other related financial data from our partnership.

Please find attached your {self.tax_year} K-1 forms, issued on behalf of {investor.receiving_entity}, for your investment in {investor.investment_name}, in {investor.investment_city}, {investor.investment_state}.

We recommend that you review these forms carefully and consult with your tax advisor to ensure accurate reporting on your tax return.

If there are any questions or if you require further assistance, feel free to reach out to me directly.

Thank you for your continued partnership and trust.
"""
            filename = investor.matched_k1_filename
            with open(os.path.join("files", filename), "rb") as pdf:
                pdf_bytes = base64.b64encode(pdf.read()).decode()

            to_recipients = []
            cc_recipients = []

            for i in range(1, 5):  # Max email addresses == 4
                email_address = getattr(investor, f"email_address_{i}")
                email_type = getattr(investor, f"email_type_{i}")

                if email_address is not None:
                    recipient = {
                        "emailAddress": {
                            "address": sender if self.test_mode else email_address
                        }
                    }
                    if email_type == "to":
                        to_recipients.append(recipient)
                    elif email_type == "cc":
                        cc_recipients.append(recipient)
                    else:  # Default to cc if email type is missing
                        cc_recipients.append(recipient)
                        investors_to_send_df.at[investor.Index, f"email_type_{i}"] = "cc"
                    
            email_message = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "Text",
                        "content": content
                    },
                    "toRecipients": to_recipients,
                    "attachments": [
                        {
                            "@odata.type": "#microsoft.graph.fileAttachment",
                            "name": filename.split("/")[-1],
                            "contentType": "application/pdf",
                            "contentBytes": pdf_bytes
                        }
                    ]
                }
            }

            if cc_recipients:
                email_message["message"]["ccRecipients"] = cc_recipients

            try:
                print(f"START {index + 1:03}: {subject}")
                response = requests.post(url=api_url, headers=headers, data=json.dumps(email_message))

                if response.status_code == 202:
                    print(f"EMAIL {index + 1:03}: {subject}")
                    investors_to_send_df.at[investor.Index, "email_status"] = "sent"
                    investors_to_send_df.at[investor.Index, "email_batch_timestamp"] = str(logger.timestamp)
                else:
                    print(f"FAIL {index + 1:03}: {response.status_code}, {response.text}")
                    investors_to_send_df.at[investor.Index, "email_status"] = f"fail {response.status_code}: {response.text}"
                    investors_to_send_df.at[investor.Index, "email_batch_timestamp"] = None
            except Exception as e:
                print(f"ERROR {index + 1:03}: {e}")
                investors_to_send_df.at[investor.Index, "email_status"] = f"error {e}"
                investors_to_send_df.at[investor.Index, "email_batch_timestamp"] = None

        investors_df.update(investors_to_send_df[["k1_matching_key", "email_status", "email_batch_timestamp"]])
        investors_df.to_excel("investors.xlsx", index=False)


if __name__ == "__main__":
    tax_year = "2023"
    test_mode = True
    email_limit = 1

    k = K1BatchProcessor(tax_year=tax_year, test_mode=test_mode, email_limit=email_limit)
    k.extract_entities()
    k.create_matching_keys()
    k.match_files_and_keys()
    # k.print_k1_array()
    k.send_emails()
    logger.close()