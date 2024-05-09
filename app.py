from flask import Flask, render_template, Response
import requests
from bs4 import BeautifulSoup
from datetime import datetime

class WikiApp(Flask):
    
    MEDIAWIKI_BASE_URL = 'https://wiki.conceptnull.org/'
    BASE_API = 'api.php?'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
                
        # Define routes
        # self.route('/', methods=['GET'])(self.homepage)
        self.route('/', methods=['GET'])(self.homepage_new)
        self.route('/publications', methods=['GET'])(self.fetch_publications)
        self.route('/meetups', methods=['GET'])(self.fetch_meetups)
        self.route('/<string:title>', methods=['GET'])(self.page_content)
        self.route('/favicon.ico')(self.favicon)
        self.route('/archive/<string:collection>', methods=['GET'])(self.get_collection)
    
    def homepage_new(self):
        pages = ['Homepage']
        homepage_content = ''
        for page in pages:
            # Make a request to MediaWiki API to get content of a specific page
            response = requests.get(self.MEDIAWIKI_BASE_URL + self.BASE_API, params={'action': 'parse', 'page': page, 'format': 'json'})
            data = response.json()
            # Extract page title and content
            page_content = data['parse']['text']['*']
            page_content = self.fix_html(page_content)
            homepage_content += page_content
            
        return render_template('cn-home.html', nav_elements=self.get_nav_menu(), content=homepage_content)
        
    def fetch_publications(self):
        concepts = ['Newsletters', 'Projects']
        publication_page_list = self.fetch_all_pages(concepts)
        updated_cat_list = self.fetch_pages_cat(publication_page_list)
        projects = updated_cat_list.get('Projects', [])
        newsletters = updated_cat_list.get('Newsletters', [])
        nav_elements = self.get_nav_menu()
        
        return render_template('publications.html', projects=projects, newsletters=newsletters, nav_elements=nav_elements)
    
    def fetch_meetups(self):
        concepts = ['Meetups']
        # publication_page_list = self.fetch_all_pages(concepts)
        # updated_cat_list = self.fetch_pages_cat(publication_page_list)
        # meetups = updated_cat_list.get('Meetups', [])
        nav_elements = self.get_nav_menu() 
        meetup_content = self.fetch_page('Meetups')
        
        return render_template('meetups.html', content=meetup_content, nav_elements=nav_elements)
        
    def fetch_pages_cat(self, category_page_list):
        all_pages_string = '|'.join(page for pages in category_page_list.values() for page in pages)
        thumb_resp = requests.get(self.MEDIAWIKI_BASE_URL + self.BASE_API, params={
			'action': 'query',
			'titles': all_pages_string,
			'format': 'json',
			'prop': 'pageimages',
			'pithumbsize': 700,
		})
        thumb_data = thumb_resp.json()
        pages_thumb_data = thumb_data.get('query', {}).get('pages', {})
        
        for key, value in pages_thumb_data.items():
            title = value.get('title')
            pageid = value.get('pageid')
            source = value.get('thumbnail', {}).get('source')
            for category, pages in category_page_list.items():
                #	print(category, pages)
                if title in pages:
                    for index, page_title in enumerate(category_page_list[category]):
                        if title == page_title:
                            category_page_list[category][page_title].update({'pageid':pageid, 'title': title, 'source': source })
                            
        return category_page_list
      
    def fetch_all_pages(self, categories):
        category_page_list = {} 
        for category in categories:
            response = requests.get(self.MEDIAWIKI_BASE_URL + self.BASE_API, params={'action': 'ask', 'query': '[[Concept:'+category+']]|?Article:Date', 'format': 'json', 'formatversion': '2'})
            data = response.json()
            page_title_timestamps = {}
            for page_title, page_data in data['query']['results'].items():
                if 'printouts' in page_data and 'Article:Date' in page_data['printouts']:
                    raw_timestamp = page_data['printouts']['Article:Date'][0]['raw']
                    raw_timestamp = raw_timestamp[2:]
                    lol = datetime.strptime(raw_timestamp, "%Y/%m/%d")
                    formatted_date = lol.strftime("%d.%m.%Y")
                    page_title_timestamps[page_title] = {'date': formatted_date}
                    
            category_page_list[category] = page_title_timestamps
        return category_page_list
             
    def homepage(self):
        # Fetch pages for articles, projects, and newsletters
        categories = ['Articles', 'Projects', 'Newsletters']
        category_page_list = self.fetch_all_pages(categories)
        updated_cat_list = self.fetch_pages_cat(category_page_list)
        articles = updated_cat_list.get('Articles', [])
        projects = updated_cat_list.get('Projects', [])
        newsletters = updated_cat_list.get('Newsletters', [])
        nav_elements = self.get_nav_menu()
        
        return render_template('home.html', articles=articles, projects=projects, newsletters=newsletters, nav_elements=nav_elements)
    
    def page_content(self, title):
        # Make a request to MediaWiki API to get content of a specific page
        response = requests.get(self.MEDIAWIKI_BASE_URL + self.BASE_API, params={'action': 'parse', 'page': title, 'format': 'json'})
        data = response.json()
        # Extract page title and content
        page_title = data['parse']['title']
        page_content = data['parse']['text']['*']
        page_content = self.fix_html(page_content)
        return render_template('article.html', nav_elements=self.get_nav_menu(), title=page_title, content=page_content)
    
    def fetch_page(self, title):
        # Make a request to MediaWiki API to get content of a specific page
        response = requests.get(self.MEDIAWIKI_BASE_URL + self.BASE_API, params={'action': 'parse', 'page': title, 'format': 'json'})
        data = response.json()
        # Extract page title and content
        page_title = data['parse']['title']
        page_content = data['parse']['text']['*']
        page_content = self.fix_html(page_content)
        return page_content
    
    def get_nav_menu(self):
        response = requests.get(self.MEDIAWIKI_BASE_URL + self.BASE_API, params={'action': 'ask', 'query': '[[Concept:MainNavigation]]', 'format': 'json', 'formatversion': '2'})
        data = response.json()
        main_navigation_elements = {}
        for page_title, page_data in data['query']['results'].items():
            main_navigation_elements[page_title] = {'title':page_data.get('fulltext', '')}
        reversed_main_navigation = list(main_navigation_elements.items())[::-1]
        reversed_main_navigation = dict(reversed_main_navigation)
        return reversed_main_navigation
    
    def fix_html(self, page_content):
        soup = BeautifulSoup(page_content, 'html.parser')

        # Find all img tags
        images = soup.find_all('img')

        # Loop through each image and update the src attribute
        for img in images:
            # Append 'https://wiki.conceptnull.org' to the src attribute
            img['src'] = 'https://wiki.conceptnull.org' + img['src']
              
        # Find all a tags with href not containing 'index.php'
        links = soup.find_all('a', href=lambda href: href and 'index.php' not in href and not href.startswith('#') and not href.startswith('/File:'))
       
        # Loop through each link and modify its href attribute
        for link in links:
            # Add _blank to href
            link['target'] = '_blank'
            link.string = link.string.strip() + " ↗"
            
        # Find all a tags with href containing 'index.php'
        links = soup.find_all('a', href=lambda href: href and 'index.php' in href)
        
        # Loop through each link and modify its href attribute
        for link in links:
            # Remove 'index.php' from the href attribute
            link['href'] = link['href'].replace('/index.php', '')
           
            
        
        # print(links)
        # Remove any element with class 'mw-editsection'
        edit_sections = soup.find_all(class_='mw-editsection')
        for edit_section in edit_sections:
            edit_section.decompose()
            
        # Remove any <a> tag's surrounding 
        file_description_tags = soup.find_all('a', class_='mw-file-description')
        for file_link in file_description_tags:
            file_link.unwrap()
            
        soup = self.remove_thumbnail_img(soup)
        
        return soup.prettify()
    
    def remove_thumbnail_img(self, soup):
        thumbnail = soup.find_all(attrs={"typeof": "mw:File/Thumb"})
        for img in thumbnail:
            img.decompose()
        return soup
    
    def get_collection(self, collection):
        resp = self.fetch_all_pages([collection])
        data = self.fetch_pages_cat(resp)
        return render_template('collection.html', nav_elements=self.get_nav_menu(), title=collection, collection=resp[collection])
    
    # Route for favicon.ico to prevent Flask from raising an error
    def favicon(self):
        return Response('', status=200)
 

if __name__ == '__main__':
    app = WikiApp(__name__)
    app.run(debug=True)
