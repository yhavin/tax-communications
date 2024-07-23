"""
Entry point for K-1 tax communications processing.

Author: Yakir Havin
"""


from k1_processor import K1BatchProcessor
from logger import logger


if __name__ == "__main__":
    SENDER = "yhavin@beitel.com"
    INTERNAL_RECIPIENTS = ["akessler@beitel.com", "aschmarlberg@beitel.com", "rdancona@beitel.com"]
    TAX_YEAR = "2023"
    TEST_MODE = True
    EMAIL_LIMIT = 1
    SKIP_CACHE_LOAD = True
    RESET_STATUS = True

    RUN_SEND_EMAILS = False

    k = K1BatchProcessor(
        sender=SENDER, 
        internal_recipients=INTERNAL_RECIPIENTS, 
        tax_year=TAX_YEAR, 
        test_mode=TEST_MODE, 
        email_limit=EMAIL_LIMIT, 
        skip_cache_load=SKIP_CACHE_LOAD,
        reset_status=RESET_STATUS
    )
    k.extract_entities()
    k.print_k1_array()
    k.match_files_and_keys()
    
    if RUN_SEND_EMAILS:
        email_number = EMAIL_LIMIT if EMAIL_LIMIT is not None else "max"
        confirmation = input(f"CAUTION: Are you sure you want to send {email_number} email{"s" if email_number != 1 else ""}? (y/n) ")
        if confirmation.lower() == "y":
            print("\n")
            k.send_emails()
        else:
            print("Email sending aborted by user.")

    logger.close()