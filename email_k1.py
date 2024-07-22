"""
Main module for K-1 tax communications processing.

Author: Yakir Havin
"""


import base64
import json
import os

import requests
import pandas as pd
import pdfplumber

import msal_auth
from logger import logger


class K1BatchProcessor:
    def __init__(self):
        self.k1_array = []
        self._gather_files()

    def _gather_files(self):
        """Gather K-1 PDFs from input folder."""
        root_folder_path = "files"

        for asset_folder in os.listdir(root_folder_path):
            asset_folder_path = os.path.join(root_folder_path, asset_folder)
            if os.path.isdir(asset_folder_path):
                for file in os.listdir(asset_folder_path):
                    if file.lower().endswith(".pdf"):
                        self.k1_array.append({
                            "path": f"{asset_folder}/{file}",
                            "investment_name": asset_folder,
                            "issuing_entity": None,
                            "receiving_entity": None
                        })

    def extract_entities(self):
        """Attempt to extract issuing and receiving entity from PDFs."""
        for k1_info in self.k1_array:
            print("EXTRACT: ", k1_info["path"])
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
                                receiving_entity = lines[line_number + 3].strip()
                                k1_info["receiving_entity"] = receiving_entity
                        break

    def create_matching_keys(self):
        """Create keys to match PDFs to investors table."""
        stop_characters_translation_table = str.maketrans({
            " ": "",
            ".": "",
            ",": ""
        })

        for k1_info in self.k1_array:
            print("MAKE KEY:", k1_info["path"])
            k1_info["k1_matching_key"] = f"{k1_info["investment_name"]}#{k1_info["issuing_entity"]}#{k1_info["receiving_entity"]}".lower().translate(stop_characters_translation_table)

    def match_files_and_keys(self):
        """Match K-1 files to investors."""
        investors_df = pd.read_excel("investors.xlsx")

        k1_matching_key_df = pd.DataFrame(self.k1_array)
        print("\nK-1 FILES:\n", k1_matching_key_df["investment_name"].value_counts())
        
        merged_df = pd.merge(investors_df, k1_matching_key_df, on="k1_matching_key", how="left", suffixes=("", "_from_pdf"))
        merged_df["matched_k1_filename"] = merged_df["path"]
        print("\nMATCHED ROWS:\n", merged_df[merged_df["matched_k1_filename"].notna()]["investment_name"].value_counts())

        print("\nUNMATCHED K-1 FILES:\n", k1_matching_key_df[~k1_matching_key_df["k1_matching_key"].isin(merged_df["k1_matching_key"])])

        merged_df = merged_df.drop(columns=["path", "investment_name_from_pdf", "issuing_entity_from_pdf", "receiving_entity_from_pdf"], axis=1)
        merged_df["email_status"] = merged_df["matched_k1_filename"].apply(lambda match: "file found" if pd.notna(match) else None)

        merged_df.to_csv(os.path.join("logs", f"matches_{logger.timestamp}.csv"), index=False)


if __name__ == "__main__":
    k = K1BatchProcessor()
    k.extract_entities()
    k.create_matching_keys()
    k.match_files_and_keys()
    logger.close()



### DISREGARD
### The following method was used when we were parsing filenames to figure out issuing and receiving entities
### Now we are mining the PDFs to extract the names from the schedule K itself

    # def _create_matching_keys(self):
    #     """Create matching keys to match K-1 files to investor rows."""
    #     self.k1_file_matching_keys = []

    #     stop_characters_translation_table = str.maketrans({
    #         " ": "",
    #         ".": "",
    #         ",": ""
    #     })

    #     for k1_file_path in self.k1_file_paths:
    #         split_folder_and_file = k1_file_path.split("/")
    #         investment_name = split_folder_and_file[0]
    #         k1_filename = split_folder_and_file[1]  # Example: 23P_3189 GOTA FOREST PLACE LLC 1 GOTA LLC.pdf

    #         split_filename = k1_filename.split(" ")
    #         roth_id = split_filename[0][4:]  # May use this for matching at some point
    #         split_filename = split_filename[1:]  # Remove Roth ID, for example: GOTA FOREST PLACE LLC 1 GOTA LLC.pdf

    #         for i, filename_part in enumerate(split_filename):
    #             if filename_part.isdigit():
    #                 number_index = i
    #                 break

    #         issuing_entity = "".join(split_filename[:number_index])
    #         receiving_entity = "".join(split_filename[number_index + 1:])[:-4]

    #         matching_key = f"{investment_name}#{issuing_entity}#{receiving_entity}".lower().translate(stop_characters_translation_table)
    #         self.k1_file_matching_keys.append((k1_file_path, matching_key))