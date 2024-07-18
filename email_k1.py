"""
Main module for K-1 tax communications processing.

Author: Yakir Havin
"""


import base64
import json
import os

import requests
import pandas as pd

import msal_auth


class K1BatchProcessor:
    def __init__(self):
        self.k1_file_paths = []
        self.k1_file_matching_keys = []
        self._gather_files()
        self._create_matching_keys()
        print(self.k1_file_matching_keys)

    def _gather_files(self):
        """Gather K-1 PDFs from input folder."""
        root_folder_path = "files"

        for asset_folder in os.listdir(root_folder_path):
            asset_folder_path = os.path.join(root_folder_path, asset_folder)
            if os.path.isdir(asset_folder_path):
                for file in os.listdir(asset_folder_path):
                    if file.lower().endswith(".pdf"):
                        self.k1_file_paths.append(f"{asset_folder}/{file}")

    def _create_matching_keys(self):
        """Create matching keys to match K-1 files to investor rows."""
        stop_characters_translation_table = str.maketrans({
            " ": "",
            ".": "",
            ",": ""
        })


        for k1_file_path in self.k1_file_paths:
            split_folder_and_file = k1_file_path.split("/")
            investment_name = split_folder_and_file[0]
            k1_filename = split_folder_and_file[1]

            # Example: 23P_3189 GOTA FOREST PLACE LLC 1 GOTA LLC.pdf
            split_filename = k1_filename.split(" ")
            roth_id = split_filename[0][4:]  # May use this for matching at some point
            split_filename = split_filename[1:]  # Remove Roth ID

            # Example: GOTA FOREST PLACE LLC 1 GOTA LLC.pdf
            for i, filename_part in enumerate(split_filename):
                if filename_part.isdigit():
                    number_index = i
                    break

            issuing_entity = "".join(split_filename[:number_index])
            receiving_entity = "".join(split_filename[number_index + 1:])[:-4]

            matching_key = f"{investment_name}#{issuing_entity}#{receiving_entity}".lower().translate(stop_characters_translation_table)
            self.k1_file_matching_keys.append(matching_key)



k = K1BatchProcessor()