from flask import Flask, render_template
import requests
from bs4 import BeautifulSoup
import urllib.parse

app = Flask(__name__)

# Base URL of your MediaWiki instance
MEDIAWIKI_BASE_URL = 'http://192.168.0.10/mediawiki/'

# Define a route for the homepage
@app.route('/')
def homepage():
    # Make a request to MediaWiki API to get a list of all pages
    response = requests.get('http://192.168.0.10/mediawiki/api.php', params={'action': 'query', 'list': 'allpages', 'format': 'json'})
    data = response.json()
    
    # Extract page titles from API response
    pages = [page['title'] for page in data['query']['allpages']]
    
    # Fetch content for each page
    page_contents = {}
    for page_title in pages:
        page_response = requests.get('http://192.168.0.10/mediawiki/api.php', params={'action': 'parse', 'page': page_title, 'format': 'json'})
        page_data = page_response.json()
        page_html = page_data['parse']['text']['*']
        
        # Preprocess HTML content to fix image URLs
        page_html = fix_image_urls(page_html)
        
        # Parse HTML content to extract image URLs
        soup = BeautifulSoup(page_html, 'html.parser')
        images = soup.find_all('img')
        image_urls = [urllib.parse.urljoin(MEDIAWIKI_BASE_URL, img['src']) for img in images]
        
        # Store page content and image URLs
        page_contents[page_title] = {'content': page_html, 'images': image_urls}
    
    # Render the base template with the list of pages and their content
    return render_template('base.html', pages=page_contents)

def fix_image_urls(html_content):
    # Replace relative image URLs with absolute URLs using MEDIAWIKI_BASE_URL
    return html_content.replace('src="/mediawiki', 'src="' + MEDIAWIKI_BASE_URL)

# Define other routes and functions as needed for your website

if __name__ == '__main__':
    app.run(debug=True)
