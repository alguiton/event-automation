from scrapers import run_all_scrapers
from utils.logger import get_logger

logger = get_logger(__name__)


def main():
    logger.info("Starting event automation run...")
    run_all_scrapers()
    logger.info("Run complete.")


if __name__ == "__main__":
    main()
