from scrapers.ArxivScraper import arxiv_scrap
from scrapers.IeeeScraper import ieee_scrap
from scrapers.ScienceDirectScraper import scdir_scrap
from scrapers.UniversalScraper import universal_scraper
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def store_data(url):
    """
    Process a URL to extract research paper content.
    Uses a universal scraper first and falls back to specialized scrapers if needed.
    """
    try:
        # First try with the universal scraper
        logger.info(f"Attempting to scrape {url} with universal scraper")
        data = universal_scraper(url)
        
        # If universal scraper returns a valid result, use it
        if data and not data.startswith("Failed to extract"):
            return data
        
        # If universal scraper failed, try with specific scrapers based on domain
        logger.info(f"Universal scraper failed, trying specialized scrapers for {url}")
        if "sciencedirect.com" in url:
            data = scdir_scrap(url)
        elif "arxiv.org" in url:
            data = arxiv_scrap(url)
        elif "ieeexplore.ieee.org" in url:
            data = ieee_scrap(url)
        else:
            # For unsupported sites, we already tried the universal scraper
            # Return a more helpful error message
            return f"The URL {url} is not from a supported research site. Here's what we could extract:\n\n{data}"
        
        return data
    except Exception as e:
        logger.error(f"Error while processing URL {url}: {str(e)}")
        return f"Error processing {url}: {str(e)}. Please check if the URL is valid and accessible."

# store_data(url)







