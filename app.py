from flask import Flask, render_template, Response
import requests
from bs4 import BeautifulSoup

class WikiApp(Flask):
    
    MEDIAWIKI_BASE_URL = 'https://wiki.conceptnull.org/'
    BASE_API = 'api.php?'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
                
        # Define routes
        self.route('/', methods=['GET'])(self.homepage)
        self.route('/<string:title>', methods=['GET'])(self.page_content)
        self.route('/favicon.ico')(self.favicon)
        
    def fetch_pages(self, category):
        # Make a request to MediaWiki API using ask action to get all pages in the specified category
        response = requests.get(self.MEDIAWIKI_BASE_URL + self.BASE_API, params={'action': 'ask', 'query': '[[Concept:'+category+']]', 'format': 'json', 'formatversion': '2'})
        data = response.json()
        
        # Extract page titles
        page_titles = [page['fulltext'] for page in data['query']['results'].values()]
        return page_titles
    
    def homepage(self):
        # Fetch pages for articles, projects, and newsletters
        articles = self.fetch_pages('Articles')
        projects = self.fetch_pages('Projects')
        newsletters = self.fetch_pages('Newsletters')
        nav_elements = self.fetch_pages('MainNavigation')
        
        
        return render_template('homepage.html', articles=articles, projects=projects, newsletters=newsletters, nav_elements=nav_elements)
    
    def page_content(self, title):
        # Make a request to MediaWiki API to get content of a specific page
        response = requests.get(self.MEDIAWIKI_BASE_URL + self.BASE_API, params={'action': 'parse', 'page': title, 'format': 'json'})
        data = response.json()
        print(title)
        # Extract page title and content
        page_title = data['parse']['title']
        page_content = data['parse']['text']['*']
        page_content = self.fix_html(page_content)
        return render_template('page_content.html', title=page_title, content=page_content)
    
    def fix_html(self, page_content):
        soup = BeautifulSoup(page_content, 'html.parser')

        # Find all img tags
        images = soup.find_all('img')

        # Loop through each image and update the src attribute
        for img in images:
            # Append 'https://wiki.conceptnull.org' to the src attribute
            img['src'] = 'https://wiki.conceptnull.org' + img['src']
              
        # Find all a tags with href containing 'index.php'
        links = soup.find_all('a', href=lambda href: href and 'index.php' in href)

        # Loop through each link and modify its href attribute
        for link in links:
            # Remove 'index.php' from the href attribute
            link['href'] = link['href'].replace('/index.php', '')
       
        # Remove any element with class 'mw-editsection'
        edit_sections = soup.find_all(class_='mw-editsection')
      
        for edit_section in edit_sections:
            edit_section.decompose()
            
        # Remove any <a> tag's surrounding 
        file_description_tags = soup.find_all('a', class_='mw-file-description')
        for file_link in file_description_tags:
            file_link.unwrap()
        
        return soup.prettify()
    
    # Route for favicon.ico to prevent Flask from raising an error
    def favicon(self):
        return Response('', status=200)
 

if __name__ == '__main__':
    app = WikiApp(__name__)
    app.run(debug=True)
