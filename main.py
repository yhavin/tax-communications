"""
Entry point for K-1 tax communications processing.

Author: Yakir Havin
"""


from k1_processor import K1BatchProcessor
from logger import logger


if __name__ == "__main__":
    sender = "yhavin@beitel.com"
    internal_recipients = ["akessler@beitel.com", "aschmarlberg@beitel.com", "rdancona@beitel.com"]
    tax_year = "2023"
    test_mode = True
    email_limit = 1
    reset_status = True
    run_send_emails = False

    k = K1BatchProcessor(sender=sender, internal_recipients=internal_recipients, tax_year=tax_year, test_mode=test_mode, email_limit=email_limit, reset_status=reset_status)
    k.extract_entities()
    k.print_k1_array()
    k.match_files_and_keys()
    
    if run_send_emails:
        email_number = email_limit if email_limit is not None else "max"
        confirmation = input(f"CAUTION: Are you sure you want to send {email_number} email{"s" if email_number != 1 else ""}? (y/n) ")
        if confirmation.lower() == "y":
            print("\n")
            k.send_emails()
        else:
            print("Email sending aborted by user.")

    logger.close()