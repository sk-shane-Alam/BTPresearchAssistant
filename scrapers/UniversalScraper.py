import requests
from bs4 import BeautifulSoup
import re
import logging
import time
import urllib.parse

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def universal_scraper(url):
    """
    A universal scraper that can extract content from any research paper website
    using requests and BeautifulSoup.
    """
    logger.info(f"Starting universal scraper for URL: {url}")
    
    # Try extraction with several attempts
    attempts = 3
    delay = 2  # seconds
    
    for attempt in range(attempts):
        try:
            result = extract_with_requests(url)
            if is_valid_content(result):
                logger.info(f"Successfully extracted content, attempt {attempt+1}")
                return result
            else:
                logger.warning(f"Attempt {attempt+1}: Extracted content not valid")
                if attempt < attempts - 1:
                    time.sleep(delay)
                    delay *= 2  # Exponential backoff
        except Exception as e:
            logger.error(f"Extraction attempt {attempt+1} failed: {str(e)}")
            if attempt < attempts - 1:
                time.sleep(delay)
                delay *= 2
    
    # If all extraction attempts fail, try to extract minimal info from URL
    try:
        paper_id = extract_paper_id_from_url(url)
        domain = extract_domain(url)
        if paper_id:
            return f"Title: Research Paper from {domain}\nPaper ID: {paper_id}\nAbstract: Could not extract content from URL. Using minimal information derived from URL."
    except Exception as e:
        logger.error(f"Error extracting paper ID: {str(e)}")
    
    # If all methods fail, return an error message
    logger.error(f"All extraction methods failed for URL: {url}")
    return f"Failed to extract content from {url}. Please check if the URL is valid and accessible."


def extract_with_requests(url):
    """Extract content using requests and BeautifulSoup"""
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    response = requests.get(url, headers=headers, timeout=20)
    if response.status_code != 200:
        logger.warning(f"Request returned non-200 status code: {response.status_code}")
        raise Exception(f"Failed to load URL: {url}, Status code: {response.status_code}")
    
    soup = BeautifulSoup(response.text, 'html.parser')
    logger.info("Successfully loaded and parsed page content")
    
    # Extract title
    title = soup.find('title').get_text(strip=True) if soup.find('title') else "Unknown Title"
    
    # Extract main content
    content = {}
    
    # Try to find abstract
    abstract = extract_abstract(soup)
    
    # Try to find authors
    authors = extract_authors(soup)
    
    # Try to find main content sections
    main_content = extract_main_content(soup)
    
    # Combine all extracted content
    content_text = f"Title: {title}\n\n"
    
    if authors:
        content_text += f"Authors: {authors}\n\n"
        
    if abstract:
        content_text += f"Abstract: {abstract}\n\n"
    
    if main_content:
        content_text += f"Content: {main_content}\n\n"
    else:
        # Fallback to extracting paragraphs
        paragraphs = [p.get_text(strip=True) for p in soup.find_all('p') if len(p.get_text(strip=True)) > 100]
        if paragraphs:
            content_text += f"Content: {' '.join(paragraphs[:10])}\n\n"
    
    # If we didn't get much content, try a site-specific approach based on domain
    if len(content_text) < 500:
        domain = extract_domain(url)
        content_text = apply_site_specific_extraction(soup, domain, url, content_text)
    
    return content_text


def extract_abstract(soup):
    """Extract abstract from soup object"""
    # Try multiple approaches to find abstract
    abstract_candidates = [
        # Direct class or ID match
        soup.find('div', {'id': 'abstract'}),
        soup.find('section', {'id': 'abstract'}),
        soup.find('div', {'class': 'abstract'}),
        soup.find('section', {'class': 'abstract'}),
        
        # Partial class match
        soup.find(lambda tag: tag.name and tag.get('class') and 
                 any('abstract' in c.lower() for c in tag.get('class'))),
                 
        # Abstract section by heading
        soup.find(lambda tag: tag.name in ['h1', 'h2', 'h3'] and 
                 tag.get_text(strip=True).lower() == 'abstract'),
    ]
    
    for candidate in abstract_candidates:
        if candidate:
            # If we found a heading, get the next element
            if candidate.name in ['h1', 'h2', 'h3']:
                next_elem = candidate.find_next()
                if next_elem and len(next_elem.get_text(strip=True)) > 50:
                    return next_elem.get_text(strip=True)
            # Otherwise return the candidate text
            if len(candidate.get_text(strip=True)) > 50:
                return candidate.get_text(strip=True)
    
    # Try finding text with "Abstract" label
    abstract_text = soup.find(string=re.compile(r'Abstract[:\s]'))
    if abstract_text:
        parent = abstract_text.parent
        next_elem = parent.find_next()
        if next_elem and len(next_elem.get_text(strip=True)) > 50:
            return next_elem.get_text(strip=True)
        elif parent and len(parent.get_text(strip=True)) > 100:
            return parent.get_text(strip=True).replace("Abstract:", "").replace("Abstract", "").strip()
    
    return ""


def extract_authors(soup):
    """Extract authors from soup object"""
    # Try multiple approaches to find authors
    author_candidates = [
        # Direct class or ID match
        soup.find('div', {'id': 'authors'}),
        soup.find('section', {'id': 'authors'}),
        soup.find('div', {'class': 'authors'}),
        soup.find('div', {'class': 'author-list'}),
        
        # Partial class match
        soup.find(lambda tag: tag.name and tag.get('class') and 
                 any('author' in c.lower() for c in tag.get('class'))),
                 
        # Authors section by heading
        soup.find(lambda tag: tag.name in ['h1', 'h2', 'h3'] and 
                 tag.get_text(strip=True).lower() in ['authors', 'author']),
    ]
    
    for candidate in author_candidates:
        if candidate:
            # If we found a heading, get the next element
            if candidate.name in ['h1', 'h2', 'h3']:
                next_elem = candidate.find_next()
                if next_elem:
                    return next_elem.get_text(strip=True)
            # Otherwise return the candidate text
            return candidate.get_text(strip=True)
    
    return ""


def extract_main_content(soup):
    """Extract main content from soup object"""
    # Try multiple approaches to find main content
    content_candidates = [
        # Common content containers
        soup.find('div', {'id': 'content'}),
        soup.find('div', {'id': 'main-content'}),
        soup.find('div', {'id': 'body'}),
        soup.find('article'),
        
        # Sections that might contain content
        soup.find_all('section'),
    ]
    
    for candidate in content_candidates:
        if candidate:
            if isinstance(candidate, list):
                # For a list of sections, combine their text
                texts = []
                for section in candidate:
                    text = section.get_text(strip=True)
                    if len(text) > 200:  # Only include substantial sections
                        texts.append(text)
                if texts:
                    return "\n\n".join(texts[:5])  # Limit to first 5 sections
            else:
                # For a single element, get its text
                text = candidate.get_text(strip=True)
                if len(text) > 200:
                    return text[:5000]  # Limit to 5000 chars
    
    return ""


def apply_site_specific_extraction(soup, domain, url, content_text):
    """Apply site-specific extraction based on the domain"""
    logger.info(f"Applying site-specific extraction for domain: {domain}")
    
    if "arxiv.org" in domain:
        # ArXiv specific extraction
        title_elem = soup.find('h1', {'class': 'title'})
        if title_elem:
            title = title_elem.get_text(strip=True).replace('Title:', '').strip()
            content_text = f"Title: {title}\n\n"
        
        abstract_elem = soup.find('blockquote', {'class': 'abstract'})
        if abstract_elem:
            abstract = abstract_elem.get_text(strip=True).replace('Abstract:', '').strip()
            content_text += f"Abstract: {abstract}\n\n"
        
        authors_elem = soup.find('div', {'class': 'authors'})
        if authors_elem:
            authors = authors_elem.get_text(strip=True)
            content_text += f"Authors: {authors}\n\n"
    
    elif "ieee" in domain:
        # IEEE specific extraction
        abstract_elem = soup.find('div', {'class': 'abstract-text'})
        if abstract_elem:
            abstract = abstract_elem.get_text(strip=True)
            content_text = content_text.replace("Abstract:", "")
            content_text += f"Abstract: {abstract}\n\n"
        
        # IEEE often has structured content in sections
        sections = soup.find_all('div', {'class': 'section'})
        if sections:
            section_texts = []
            for section in sections:
                heading = section.find(['h2', 'h3'])
                if heading:
                    section_text = f"{heading.get_text(strip=True)}:\n"
                    section_text += section.get_text(strip=True).replace(heading.get_text(strip=True), "")
                    section_texts.append(section_text)
            if section_texts:
                content_text += "Sections:\n" + "\n\n".join(section_texts[:5]) + "\n\n"
    
    elif "sciencedirect" in domain:
        # ScienceDirect specific extraction
        abstract_elem = soup.find('div', {'class': 'abstract'})
        if abstract_elem:
            abstract = abstract_elem.get_text(strip=True)
            content_text = content_text.replace("Abstract:", "")
            content_text += f"Abstract: {abstract}\n\n"
        
        # ScienceDirect often has structured sections
        sections = soup.find_all('section')
        if sections:
            section_texts = []
            for section in sections:
                if len(section.get_text(strip=True)) > 200:
                    section_texts.append(section.get_text(strip=True))
            if section_texts:
                content_text += "Sections:\n" + "\n\n".join(section_texts[:5]) + "\n\n"
    
    return content_text


def extract_domain(url):
    """Extract domain from URL"""
    parsed_url = urllib.parse.urlparse(url)
    domain = parsed_url.netloc
    return domain


def is_valid_content(content):
    """Check if the extracted content is valid and substantial"""
    if not content:
        return False
    
    # Check if content has enough length
    if len(content) < 200:
        return False
    
    # Check if content contains at least title and some other content
    if "Title:" not in content or len(content.split("Title:")[1].strip()) < 10:
        return False
    
    # Check if we have either abstract or content
    if "Abstract:" not in content and "Content:" not in content:
        return False
    
    return True


def extract_paper_id_from_url(url):
    """Extract paper ID from URL using common patterns"""
    patterns = [
        r'arxiv\.org/abs/(\d+\.\d+)',         # ArXiv ID format
        r'doi\.org/([^/]+/[^/]+)',             # DOI format
        r'(\d{4}\.\d{4,5})',                   # ArXiv ID in URL
        r'paper[=/](\w+)',                     # Generic paper ID
        r'article[=/](\w+)',                   # Generic article ID
        r'document/(\d+)',                     # IEEE format
        r'pii/(S\d+)',                         # ScienceDirect format
        r'([^/]+)$'                            # Last segment as fallback
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None 