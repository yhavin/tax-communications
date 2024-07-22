"""
Main module for K-1 tax communications processing.

Author: Yakir Havin
"""


import base64
import json
import os
import pickle
import re

import requests
import pandas as pd
import pdfplumber

import msal_auth
from logger import logger


class K1BatchProcessor:
    def __init__(self):
        self.k1_array = []
        self.cache = "k1_array_cache.pkl"
        self._load_cache()
        self._gather_files()

    def _load_cache(self):
        """Attempt to load K-1 entity array from cache."""
        if not os.path.exists("cache"):
            os.makedirs("cache")

        if os.path.exists(os.path.join("cache", self.cache)):
            with open(os.path.join("cache", self.cache), "rb") as f:
                self.k1_array = pickle.load(f)
            print(f"CACHE: Loaded {len(self.k1_array)} items")
        else:
            print("CACHE: Not found")

    def _save_cache(self):
        """Save K-1 entity array to cache."""
        with open(os.path.join("cache", self.cache), "wb") as f:
            pickle.dump(self.k1_array, f)
        print(f"CACHE: Saved {len(self.k1_array)} items")
        
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
        print("GATHER:", f"{len(self.k1_array)} K-1 files ({len(new_k1_files)} new)")

    def extract_entities(self):
        """Attempt to extract issuing and receiving entity from PDFs."""
        k1_files_to_extract = [k1_info for k1_info in self.k1_array if k1_info["issuing_entity"] is None and k1_info["receiving_entity"] is None]

        for index, k1_info in enumerate(k1_files_to_extract):
            print(f"EXTRACT {index:03}: {k1_info["path"]}")
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
                                if re.search(r"\bst\b", receiving_entity.lower()) or re.search(r"\bstreet\b", receiving_entity.lower()):  # Off-by-one error sometimes happens
                                    receiving_entity = lines[receiving_entity_index - 1].strip()
                                k1_info["receiving_entity"] = receiving_entity
                        break

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
        investors_df = pd.read_excel("investors.xlsx")

        k1_matching_key_df = pd.DataFrame(self.k1_array)
        print("\nK-1 FILES:\n", k1_matching_key_df["investment_name"].value_counts())
        
        merged_df = pd.merge(investors_df, k1_matching_key_df, on="k1_matching_key", how="left", suffixes=("", "_from_pdf"))
        merged_df["matched_k1_filename"] = merged_df["path"]
        print("\nMATCHED ROWS:\n", merged_df[merged_df["matched_k1_filename"].notna()]["investment_name"].value_counts().rename(index=str.upper), "\n")

        unmatched_k1_files_df = k1_matching_key_df[~k1_matching_key_df["k1_matching_key"].isin(merged_df["k1_matching_key"])].sort_values(by="path")
        print("UNMATCHED ROWS:", len(unmatched_k1_files_df), "\n")
        print(f"SUCCESS RATE: {1 - (len(unmatched_k1_files_df) / len(k1_matching_key_df)):.2%}")
        unmatched_k1_files_df.to_csv(os.path.join("logs", f"unmatched_{logger.timestamp}.csv"), index=False)

        merged_df = merged_df.drop(columns=["path", "investment_name_from_pdf", "issuing_entity_from_pdf", "receiving_entity_from_pdf"], axis=1)
        merged_df["email_status"] = merged_df["matched_k1_filename"].apply(lambda match: "file found" if pd.notna(match) else None)

        merged_df.to_csv(os.path.join("queue", f"matched_{logger.timestamp}.csv"), index=False)


if __name__ == "__main__":
    k = K1BatchProcessor()
    k.extract_entities()
    k.create_matching_keys()
    k.match_files_and_keys()
    # k.print_k1_array()
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