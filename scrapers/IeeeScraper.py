import time
import re
import logging
import requests
from bs4 import BeautifulSoup

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def scraper(url: str):
    logger.info(f"Starting IEEE scraping for URL: {url}")
    
    try:
        # Set a user agent to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Make the request
        logger.info(f"Loading IEEE URL: {url}")
        response = requests.get(url, headers=headers, timeout=20)
        
        # Check if the request was successful
        if response.status_code != 200:
            logger.error(f"Failed to load URL: {url}, Status code: {response.status_code}")
            return f"Failed to load URL: {url}, Status code: {response.status_code}"
        
        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        logger.info("Successfully loaded and parsed the page")
        
        # Initialize scraped text
        scraped_txt = ""
        
        # Try to find main content
        main_content = soup.find_all(class_="col-24-24")
        if main_content:
            logger.info(f"Found {len(main_content)} entries with class col-24-24")
            for elem in main_content:
                elem_text = elem.get_text(strip=True)
                if len(elem_text) > len(scraped_txt):
                    scraped_txt = elem_text
        
        # If no good text found, try alternate methods
        if not scraped_txt or len(scraped_txt) < 100:
            logger.warning("Primary extraction method yielded insufficient data. Trying alternate methods.")
            
            # Try to get title
            title = soup.title.text if soup.title else "Unknown Title"
            title_elem = soup.find(class_="document-title")
            if title_elem:
                title = title_elem.get_text(strip=True)
            
            # Try to get abstract
            abstract = ""
            abstract_elems = soup.find_all(["div", "section"], class_=lambda c: c and "abstract" in c.lower())
            if not abstract_elems:
                abstract_elems = soup.find_all(id=lambda i: i and "abstract" in i.lower())
            
            if abstract_elems:
                abstract = "\n".join([a.get_text(strip=True) for a in abstract_elems if a.get_text(strip=True)])
            
            # Try to get content sections
            content = ""
            sections = soup.find_all("section")
            if sections:
                content = "\n\n".join([s.get_text(strip=True) for s in sections if len(s.get_text(strip=True)) > 50])
            
            # Try to get main content if not found yet
            if not content:
                paragraphs = soup.find_all("p")
                if paragraphs:
                    content = "\n\n".join([p.get_text(strip=True) for p in paragraphs if len(p.get_text(strip=True)) > 50])
            
            scraped_txt = f"Title: {title}\n\nAbstract: {abstract}\n\n{content}"
            
        logger.info(f"Extracted {len(scraped_txt)} characters of text")
        
        # Process the text into a structured format if possible
        result = store(scraped_txt)
        return result
        
    except Exception as e:
        logger.error(f"Error during IEEE scraping: {str(e)}")
        return f"Error scraping IEEE URL: {str(e)}"


def store(txt: str):
    try:
        lst = txt.split(sep="\n")
        logger.info(f"Processing {len(lst)} lines of text")
        
        # Prepare a more resilient processing method
        result = {
            "Title": "",
            "Authors": "",
            "Abstract": "",
            "Keywords": "",
            "Content": ""
        }
        
        # Try to extract structured data
        try:
            if len(lst) > 1:
                result["Title"] = lst[0]
                
            for i, line in enumerate(lst):
                if "Abstract" in line and i < len(lst)-1:
                    result["Abstract"] = lst[i+1] if i+1 < len(lst) else ""
                if "Author" in line or "AUTHORS" in line:
                    result["Authors"] = line.replace("Authors:", "").strip()
                if "Keyword" in line or "KEYWORDS" in line:
                    result["Keywords"] = line.replace("Keywords:", "").strip()
        except Exception as e:
            logger.warning(f"Error during structured extraction: {str(e)}")
            
        # Fallback to raw text if structured extraction fails
        if not result["Title"] and not result["Abstract"]:
            result["Content"] = txt[:5000]  # Limit to first 5000 chars
            
        # Format as a string for return
        formatted_txt = f"Title: {result['Title']}\n\nAuthors: {result['Authors']}\n\nAbstract: {result['Abstract']}\n\nKeywords: {result['Keywords']}\n\nContent: {result['Content']}"
        logger.info("Successfully processed IEEE paper data")
        return formatted_txt
        
    except Exception as e:
        logger.error(f"Error processing IEEE paper data: {str(e)}")
        # Return raw text if processing fails
        return f"Title: IEEE Paper\n\nContent: {txt[:5000]}"


def ieee_scrap(url):
    logger.info(f"IEEE scraper called for URL: {url}")
    try:
        # Add retry mechanism for more reliability
        attempts = 3
        delay = 2  # seconds
        
        for attempt in range(attempts):
            try:
                data = scraper(url)
                if data and len(data) >= 50:
                    logger.info(f"Successfully scraped IEEE URL. Data length: {len(data)}")
                    return data
                else:
                    logger.warning(f"Attempt {attempt+1}: Extracted data too short or empty")
                    if attempt < attempts - 1:
                        time.sleep(delay)
                        delay *= 2  # Exponential backoff
            except Exception as e:
                logger.error(f"Attempt {attempt+1} failed: {str(e)}")
                if attempt < attempts - 1:
                    time.sleep(delay)
                    delay *= 2
        
        return f"Failed to extract meaningful content from {url} after {attempts} attempts"
    except Exception as e:
        logger.error(f"Error in ieee_scrap: {str(e)}")
        return f"Error scraping IEEE URL: {str(e)}"


# URL = "https://ieeexplore.ieee.org/document/4460684"
# scraper(URL)
# print("\n\n Document2:\n")
# URL = "https://ieeexplore.ieee.org/document/9497989"
# scraper(URL)
# print("Program end.")