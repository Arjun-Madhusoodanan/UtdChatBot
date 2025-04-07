import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse
import pandas as pd
from tqdm import tqdm
import time
import logging
import re

# Configure logging
logging.basicConfig(
    filename='scraping_errors.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Allowed domains (including subdomains)
ALLOWED_DOMAINS = {
    "jindal.utdallas.edu",
    "accounting.utdallas.edu",
    "fin.utdallas.edu",
    "infosystems.utdallas.edu",
    "marketing.utdallas.edu",
    "osim.utdallas.edu",
    "om.utdallas.edu",
    "execed.utdallas.edu",
    "mba.utdallas.edu",
    "sem.utdallas.edu"
}

class JindalScraper:
    def __init__(self):
        self.visited = set()
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept-Language": "en-US,en;q=0.5"
        })
        self.scraped_data = []
        self.queue = []
        self.file_extensions = {'.pdf', '.jpg', '.png', '.docx', '.xlsx'}
        self.delay = 2  # Seconds between requests
        self.max_pages = 10000  # Safety limit

    def normalize_url(self, url):
        """Strong URL normalization with case insensitivity"""
        parsed = urlparse(url)
        # Standardize components
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = re.sub(r'/+$', '', parsed.path) or '/'
        path = re.sub(r'//+', '/', path)  # Remove duplicate slashes
        return urlunparse((scheme, netloc, path, '', '', ''))

    def is_valid_url(self, url):
        """Check if URL is valid for scraping"""
        parsed = urlparse(url)
        if parsed.netloc not in ALLOWED_DOMAINS:
            return False
        if any(ext in parsed.path.lower() for ext in self.file_extensions):
            return False
        return True

    def extract_content(self, soup):
        """Improved content extraction with hierarchy preservation"""
        for element in soup(['script', 'style', 'nav', 'footer', 'header']):
            element.decompose()

        content = []
        main_content = soup.find('main') or soup.body
        
        current_section = None
        for element in main_content.find_all(['h1', 'h2', 'h3', 'p', 'ul', 'ol']):
            if element.name.startswith('h'):
                if current_section:
                    content.append(current_section)
                current_section = {
                    'heading_level': element.name,
                    'heading_text': element.get_text(strip=True),
                    'content': []
                }
            elif current_section and element.get_text(strip=True):
                text = element.get_text(separator=' ', strip=True)
                if len(text) > 40:  # Filter short text blocks
                    current_section['content'].append(text)
        
        if current_section:
            content.append(current_section)
        return content

    def process_page(self, url):
        """Process individual page with error handling"""
        if len(self.visited) >= self.max_pages:
            return []

        normalized_url = self.normalize_url(url)
        if normalized_url in self.visited:
            return []

        self.visited.add(normalized_url)
        new_links = []

        try:
            response = self.session.get(url, timeout=15)
            response.raise_for_status()
            
            if 'text/html' not in response.headers.get('Content-Type', ''):
                return []

            soup = BeautifulSoup(response.text, 'lxml')
            
            page_data = {
                "url": normalized_url,
                "title": soup.title.get_text(strip=True) if soup.title else "No Title",
                "content": self.extract_content(soup),
                "links": []
            }

            # Extract and store internal links
            for link in soup.find_all('a', href=True):
                raw_url = link['href']
                full_url = self.normalize_url(urljoin(url, raw_url))
                
                if self.is_valid_url(full_url) and full_url not in self.visited:
                    page_data["links"].append(full_url)
                    new_links.append(full_url)

            self.scraped_data.append(page_data)
            return new_links

        except Exception as e:
            logging.error(f"Error processing {url}: {str(e)}")
            return []

    def crawl(self, start_urls):
        """Main crawling workflow with progress tracking"""
        self.queue = start_urls.copy()
        processed_count = 0
        
        with tqdm(total=len(self.queue), desc="Scraping Progress") as pbar:
            while self.queue and processed_count < self.max_pages:
                url = self.queue.pop(0)
                new_links = self.process_page(url)
                processed_count += 1
                
                if new_links:
                    self.queue.extend(new_links)
                    pbar.total = len(self.queue)
                    pbar.refresh()
                
                pbar.update(1)
                time.sleep(self.delay)

    def save_to_csv(self, filename):
        """Convert to CSV format with incremental saving"""
        flat_data = []
        for entry in self.scraped_data:
            for section in entry['content']:
                flat_data.append({
                    "URL": entry['url'],
                    "MainTitle": entry['title'],
                    "SectionTitle": section['heading_text'],
                    "Content": " ".join(section['content'])
                })
        
        pd.DataFrame(flat_data).to_csv(filename, index=False)

def get_initial_urls():
    """Get URLs from sitemap with validation"""
    sitemap_url = "https://jindal.utdallas.edu/sitemap/"
    response = requests.get(sitemap_url)
    soup = BeautifulSoup(response.text, 'html.parser')
    urls = set()
    
    for link in soup.find_all('a', href=True):
        raw_url = link['href']
        full_url = urljoin(sitemap_url, raw_url)
        parsed = urlparse(full_url)
        if parsed.netloc in ALLOWED_DOMAINS:
            urls.add(full_url)
    
    return list(urls)

if __name__ == "__main__":
    scraper = JindalScraper()
    
    try:
        print("Fetching initial URLs from sitemap...")
        start_urls = get_initial_urls()
        print(f"Found {len(start_urls)} valid starting URLs")
        
        print("Starting scraping process...")
        scraper.crawl(start_urls)
        
        print("Saving results...")
        scraper.save_to_csv("jindal_comprehensive_data.csv")
        print(f"Scraping complete. Saved {len(scraper.scraped_data)} pages")
        
    except Exception as e:
        logging.critical(f"Fatal error: {str(e)}")
        raise
