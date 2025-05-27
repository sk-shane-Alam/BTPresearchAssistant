import requests
from bs4 import BeautifulSoup
import logging
import time

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def extract_tags_data_with_sections(url: str, tags_info: dict) -> str:
    logger.info(f"Extracting data from ScienceDirect URL: {url}")
    
    try:
        # Set a user agent to mimic a browser
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        # Make the request
        logger.info(f"Loading URL: {url}")
        response = requests.get(url, headers=headers, timeout=20)
        
        # Check if the request was successful
        if response.status_code != 200:
            logger.error(f"Failed to load URL: {url}, Status code: {response.status_code}")
            return f"Failed to load URL: {url}, Status code: {response.status_code}"
        
        # Parse HTML content
        soup = BeautifulSoup(response.text, 'html.parser')
        logger.info("Successfully loaded and parsed the page")
        
        # String to store extracted information
        extracted_data = ""
        
        # Extract page title
        title = soup.title.text if soup.title else "No title found"
        extracted_data += f"Title: {title}\n\n"

        # Extract elements by IDs
        for element_id in tags_info.get("id", []):
            element = soup.find(id=element_id)
            if element:
                extracted_data += f"ID '{element_id}': {element.get_text(strip=True)}\n"
                logger.info(f"Successfully extracted ID '{element_id}'")
            else:
                logger.warning(f"Failed to find element with ID '{element_id}'")
                extracted_data += f"ID '{element_id}': Not found\n"

        # Extract elements by Classes
        for class_name in tags_info.get("class", []):
            elements = soup.find_all(class_=class_name)
            if elements:
                class_data = " ".join([el.get_text(strip=True) for el in elements])
                extracted_data += f"Class '{class_name}': {class_data}\n"
                logger.info(f"Successfully extracted Class '{class_name}'")
            else:
                logger.warning(f"Failed to find elements with Class '{class_name}'")
                extracted_data += f"Class '{class_name}': Not found\n"

        # Extract sections
        sections = soup.find_all('section')
        section_data = ""
        
        for section in sections:
            section_id = section.get('id', '')
            if section_id and section_id.startswith("sec"):
                section_data += f"Section ID '{section_id}': {section.get_text(strip=True)}\n"
        
        if section_data:
            extracted_data += section_data
            logger.info(f"Successfully extracted {len(sections)} sections")

        # ScienceDirect specific extraction
        abstract = soup.find(["div", "section"], class_=lambda c: c and "abstract" in c.lower())
        if abstract:
            extracted_data += f"Abstract: {abstract.get_text(strip=True)}\n"
            logger.info("Successfully extracted abstract")
            
        # Try to get article content
        article = soup.find("article")
        if article:
            article_text = article.get_text(strip=True)
            if len(article_text) > 200:  # Only include if substantial
                extracted_data += f"Article Content: {article_text[:5000]}\n"
                logger.info("Successfully extracted article content")

        if not extracted_data.strip():
            # Fallback extraction if nothing found with the specified classes/IDs
            logger.warning("No data extracted with specified selectors. Using fallback extraction.")
            
            # Try to find abstract through generic selectors
            abstract_elements = soup.find_all(string=lambda text: text and "abstract" in text.lower())
            abstract = ""
            if abstract_elements:
                for elem in abstract_elements:
                    parent = elem.parent
                    if parent and len(parent.get_text(strip=True)) > 50:
                        abstract = parent.get_text(strip=True)
                        break
            
            # Get some content from paragraphs
            paragraphs = [p.get_text(strip=True) for p in soup.find_all('p') if len(p.get_text(strip=True)) > 100]
            body_text = "\n\n".join(paragraphs[:10])  # Limit to first 10 paragraphs
            
            extracted_data = f"Title: {title}\n\nAbstract: {abstract}\n\nContent: {body_text[:5000]}"
            
        logger.info(f"Extraction completed. Extracted {len(extracted_data)} characters")
        return extracted_data.strip()

    except Exception as e:
        logger.error(f"Error during extraction: {str(e)}")
        return f"Error extracting data: {str(e)}"

def scdir_scrap(url):
    logger.info(f"Starting ScienceDirect scraping for URL: {url}")
    tags_info = {
    "id": ["abstracts", "abs0010"],
    "class": ["title-text", "author", "doi", "abstract","Abstracts"]
    }
    
    try:
        # Add retry mechanism for more reliability
        attempts = 3
        delay = 2  # seconds
        
        for attempt in range(attempts):
            try:
                data = extract_tags_data_with_sections(url, tags_info)
                if data and len(data) >= 50:
                    logger.info(f"Successfully scraped ScienceDirect URL. Data length: {len(data)}")
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
        logger.error(f"Error in scdir_scrap: {str(e)}")
        return f"Error scraping ScienceDirect URL: {str(e)}"

