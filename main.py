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
    k = K1BatchProcessor(
        sender=config["sender"], 
        internal_recipients=config["internal_recipients"], 
        tax_year=config["tax_year"], 
        test_mode=config["test_mode"], 
        email_limit=config["email_limit"], 
        skip_cache_load=config["skip_cache_load"]
    )
    k.extract_entities()
    # k.print_k1_array()
    k.match_files_and_keys()
    
    if config["run_send_emails"]:
        k.send_emails()

    logger.close()