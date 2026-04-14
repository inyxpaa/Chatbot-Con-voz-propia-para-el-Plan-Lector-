import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from pathlib import Path
import time

base_dir = Path(__file__).resolve().parent.parent
raw_dir = base_dir / "raw"
raw_dir.mkdir(parents=True, exist_ok=True)
output_file = raw_dir / "convozpropia_raw.txt"

START_URL = "https://iescomercio.com/convozpropia/"
DOMAIN = "iescomercio.com"
BASE_PATH = "/convozpropia/"

visited = set()
to_visit = set([START_URL])
all_texts = []

def extract_text_from_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    
    # Try to find the main content block
    content = soup.find('div', class_='entry-content')
    if not content:
        # If not an article, standard extraction
        content = soup.find('main')
    if not content:
        content = soup
        
    text_elements = content.find_all(['p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li'])
    texts = [elem.get_text(separator=" ", strip=True) for elem in text_elements]
    
    # Filter very short texts that might just be UI elements
    texts = [t for t in texts if len(t.split()) > 2]
    return " ".join(texts)

def get_links(soup, current_url):
    links = set()
    for a in soup.find_all('a', href=True):
        href = a['href']
        full_url = urljoin(current_url, href)
        parsed_url = urlparse(full_url)
        
        # Only stay within the convozpropia section
        if parsed_url.netloc == DOMAIN and parsed_url.path.startswith(BASE_PATH):
            links.add(full_url.split('#')[0]) # Remove fragments
    return links

print("Iniciando scraping de la web 'Con Voz Propia'...")

while to_visit:
    current_url = to_visit.pop()
    if current_url in visited:
        continue
        
    print(f"Visitando: {current_url}")
    visited.add(current_url)
    
    try:
        response = requests.get(current_url, timeout=10)
        # Check if it is a text/html page
        if 'text/html' not in response.headers.get('Content-Type', ''):
            continue
            
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Extract text
        text = extract_text_from_html(response.text)
        if text:
            # Add a clear separator or title placeholder to keep context if needed
            title = soup.title.string if soup.title else current_url
            all_texts.append(f"FUENTE: {title}\nURL: {current_url}\n{text}\n\n")
            
        # Get more links
        new_links = get_links(soup, current_url)
        for link in new_links:
            if link not in visited:
                to_visit.add(link)
                
        time.sleep(1) # Be polite
    except Exception as e:
        print(f"Error accediendo a {current_url}: {e}")
        
    # Limit number of pages to prevent infinite crawling if loops occur
    if len(visited) >= 150:
        print("Límite de páginas alcanzado.")
        break

print(f"Extracción completada. Paginas procesadas: {len(visited)}")

with open(output_file, "w", encoding="utf-8") as f:
    f.write("\n==================================\n".join(all_texts))

print(f"Texto guardado en {output_file}")
