# Web_Scrapping_Part2.py
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
    filename='scraping_errors_part2.log',
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

# Updated allowed domains
ALLOWED_DOMAINS = {
    "graduation.utdallas.edu",
    "registrar.utdallas.edu"
    # "suaab.utdallas.edu",
    # "studenthealthcenter.utdallas.edu",
    # "ets.utdallas.edu",
    # "library.utdallas.edu",
    # "urec.utdallas.edu"
}

class UTDScraper:
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
        self.delay = 2 
        self.max_pages = 5000

    def normalize_url(self, url):
        """Strong URL normalization with case insensitivity"""
        parsed = urlparse(url)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        path = re.sub(r'/+$', '', parsed.path) or '/'
        path = re.sub(r'//+', '/', path)
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
                if len(text) > 40:
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
        
        with tqdm(desc="Scraping Progress", unit="page") as pbar:
            while self.queue and len(self.visited) < self.max_pages:
                url = self.queue.pop(0)
                new_links = self.process_page(url)
                
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
    """Get initial URLs for all domains"""
    return [f"https://{domain}/" for domain in ALLOWED_DOMAINS]

if __name__ == "__main__":
    scraper = UTDScraper()
    
    try:
        print("Fetching initial URLs...")
        start_urls = get_initial_urls()
        print(f"Found {len(start_urls)} initial entry points")
        
        print("Starting scraping process...")
        scraper.crawl(start_urls)
        
        print("Saving results...")
        scraper.save_to_csv("utd_graduation_data.csv")
        print(f"Scraping complete. Saved {len(scraper.scraped_data)} pages")

    except Exception as e:
        logging.critical(f"Fatal error: {str(e)}")
        raise
