"""
Entry point for K-1 tax communications processing.

Author: Yakir Havin
"""


from k1_processor import K1BatchProcessor
from logger import logger
try:
    from config import config
except ImportError:
    print("`config.py` not found. Please create it from `config.pytemplate`.")
    exit(1)


if __name__ == "__main__":
    SENDER = config["sender"]
    INTERNAL_RECIPIENTS = config["internal_recipients"]
    TAX_YEAR = config["tax_year"]
    TEST_MODE = config["test_mode"]
    EMAIL_LIMIT = config["email_limit"]
    SKIP_CACHE_LOAD = config["skip_cache_load"]
    RESET_STATUS = config["reset_status"]
    RUN_SEND_EMAILS = config["run_send_emails"]

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
    # k.print_k1_array()
    k.match_files_and_keys()
    
    if RUN_SEND_EMAILS:
        k.send_emails()

    logger.close()