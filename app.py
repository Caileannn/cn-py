from flask import Flask, render_template, Response
import requests
import re
from bs4 import BeautifulSoup, Comment
from datetime import datetime
from dateutil.relativedelta import relativedelta

class WikiApp(Flask):
    
    MEDIAWIKI_BASE_URL = 'https://wiki.conceptnull.org/'
    BASE_API = 'api.php?'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
                
        # Define routes
        self.route('/', methods=['GET'])(self.home)
        self.route('/activities', methods=['GET'])(self.activities)
        self.route('/data', methods=['GET'])(self.data_int)
        self.route('/generate-nl', methods=['GET'])(self.create_nl)
        self.route('/newsletter/<string:title>', methods=['GET'])(self.generate_newsletter)
        self.route('/<string:title>', methods=['GET'])(self.page_content)
        self.route('/favicon.ico')(self.favicon)
        
    # Return Homepage
    def home(self):    
        pages = ['Homepage']
        homepage_content = ''
        for page in pages:
            # Make a request to MediaWiki API to get content of a specific page
            response = requests.get(self.MEDIAWIKI_BASE_URL + self.BASE_API, params={'action': 'parse', 'page': page, 'format': 'json'})
            data = response.json()
            # Extract page title and content
            page_content = data['parse']['text']['*']
            page_content, table = self.fix_html(page_content)
            homepage_content += page_content
        return render_template('index.html', cont=homepage_content, table=table)
    
    def activities(self):
        # fetch publications as test
        activity_list = self.get_activities()
        return render_template('activities.html', title="Activities", activities=activity_list)
    
    def get_activities(self):
        concepts = ['Activities']
        publication_page_list = self.fetch_all_activies(concepts)
        updated_cat_list = self.fetch_pages_cat(publication_page_list)
        activities = updated_cat_list.get('Activities', [])
        srted_activities = dict(sorted(activities.items(), key=lambda item: datetime.strptime(item[1]['date'], "%d.%m.%Y" ), reverse=True) )
        # projects = updated_cat_list.get('Projects', [])
        # sorted_prj = dict(sorted(projects.items(), key=lambda item: datetime.strptime(item[1]['date'], "%d.%m.%Y" ), reverse=True) )
        # newsletters = updated_cat_list.get('Newsletters', [])
        # sorted_nl = dict(sorted(newsletters.items(), key=lambda item: datetime.strptime(item[1]['date'], "%d.%m.%Y" ), reverse=True) )
        return srted_activities
       
    def data_int(self):
        return render_template('data.html')
    
    def create_nl(self):
        # Function for generating a newsletter
        pass
         
    def generate_newsletter(self, title):
        content, title, date = self.fetch_page(title)
        given_date = datetime.strptime(date, "%Y-%m-%d")
        new_date_opp = given_date + relativedelta(months=2)
        new_date_events = given_date + relativedelta(weeks=4)
        opportunites_dict = self.fetch_opportunities(given_date.date(), new_date_opp.date())
        events_dict = self.fetch_events(given_date.date(), new_date_events.date())
        
        spotlight = False
        # Loop through the events and check the spotlight attribute
        for category, events in events_dict.items():
            for event in events:
                if event['spotlight']:
                    spotlight = True
                    break
        
        return render_template('newsletter.html', nav_elements=self.get_nav_menu(), cont=content, title=title, events=events_dict, opportunities=opportunites_dict, spotlight=spotlight)

    def fetch_opportunities(self, pub_date, future_date):
        all_opportunities = self.fetch_all_opportunities(pub_date, future_date)
        if not all_opportunities:
            return {}
        else:
            titles = ''
            for value in all_opportunities.values():
                if isinstance(value, list):
                    for entry in value:
                        titles += entry['pagetitle'] + '|'
                        
            titles = titles[:-1]
            resp = requests.get(self.MEDIAWIKI_BASE_URL + self.BASE_API, params={
    			'action': 'query',
    			'titles': titles,
    			'format': 'json',
    			'prop': 'extracts',
    			'exlimit': '20',
    			'explaintext': 'true',
    			'exintro': 'true'
    		})
            
            
            data = resp.json()
            
            opp_data = data.get('query', {}).get('pages', {})
            for residency_entry in all_opportunities.values():
                for open_call_entry in opp_data.values():
                        for opp in residency_entry:
                            if opp['pagetitle'] == open_call_entry['title']:
                                try:
                                    opp['text'] = open_call_entry['extract']
                                except:
                                    opp['text'] = "No text information found."
                        
            sorted_data = {key: sorted(value, key=lambda x: x['deadline'], reverse=True) for key, value in all_opportunities.items()}        
            new_order = ['Open Call', 'Residency', 'Funding', 'Job Opportunity', 'Workshop', 'Studio Vacancy']
            category_mapping = {
				'Open Call': '📯 Open Calls',
				'Residency': '🏠 Residencies',
				'Funding': '💰 Funding',
				'Job Opportunity': '🦺 Job Opportunities',
				'Workshop': '🛠️ Workshops',
				'Studio Vacancy': '🔓 Studio Vacancies'
			}
            reordered_dict = {category_mapping[category]: sorted_data[category] for category in new_order if category in sorted_data}
            return reordered_dict
             
    def fetch_all_opportunities(self, pub_date, future_date):
        opp_page_list = {}
        categories = ['Opportunities'] 
        for category in categories:
            response = requests.get(self.MEDIAWIKI_BASE_URL + self.BASE_API, params={'action': 'ask', 'query': '[[Concept:'+category+']] [[Opportunities:Deadline::<=' + future_date.strftime("%Y-%m-%d") + ']] [[Opportunities:Deadline::>='+ pub_date.strftime("%Y-%m-%d") + ']] |?Opportunities:Deadline|?Opportunities:Name|?Opportunities:Location|?Opportunities:Organiser/s|?Opportunities:Type|?Opportunities:Source', 'format': 'json', 'formatversion': '2'})
            data = response.json()
            opp_info = {}
            if not data['query']['results']:
                return {}
            else:
                for page_title, page_data in data['query']['results'].items():
                    if 'printouts' in page_data and 'Opportunities:Deadline' in page_data['printouts']:
                        try:
                            type = page_data['printouts']['Opportunities:Type'][0]
                            name = page_data['printouts']['Opportunities:Name'][0]
                            deadline = page_data['printouts']['Opportunities:Deadline'][0]['raw']
                            deadline = deadline[2:]
                            lol = datetime.strptime(deadline, "%Y/%m/%d")
                            formatted_deadline = lol.strftime("%d-%m-%Y")
                            location = page_data['printouts']['Opportunities:Location'][0]
                            source = page_data['printouts']['Opportunities:Source'][0]
                            org = page_data['printouts']['Opportunities:Organiser/s'][0]['fulltext']
                            
                            opp_info = {'pagetitle': page_title, 'name': name, 'deadline': formatted_deadline, 'location': location, 'source' : source, 'org': org, 'text': ''}
                            
                            if type not in opp_page_list:
                                opp_page_list[type] = []
                            
                            opp_page_list[type].append(opp_info)
                        except:
                            print(f"issue with parsing, {page_title}")
        
        return opp_page_list
    
    def fetch_events(self, pub_date, future_date):
        all_events = self.fetch_all_events(pub_date, future_date)
        if not all_events:
            return {}
        else:
            titles = ''
    
            for value in all_events.values():
                if isinstance(value, list):
                    for entry in value:
                        titles += entry['pagetitle'] + '|'
                        
            titles = titles[:-1]
            resp = requests.get(self.MEDIAWIKI_BASE_URL + self.BASE_API, params={
    			'action': 'query',
    			'titles': titles,
    			'format': 'json',
    			'prop': 'extracts',
    			'exlimit': '20',
    			'explaintext': 'true',
    			'exintro': 'true'
    		})
            
            data = resp.json()
			
            opp_data = data.get('query', {}).get('pages', {})
            
            for residency_entry in all_events.values():
                for open_call_entry in opp_data.values():
                        for opp in residency_entry:
                            if opp['pagetitle'] == open_call_entry['title']:
                                opp['text'] = open_call_entry['extract']
                        
            sorted_data = {key: sorted(value, key=lambda x: x['deadline'], reverse=False) for key, value in all_events.items()}
            return sorted_data
    
    def fetch_all_events(self, pub_date, future_date):
        opp_page_list = {}
        categories = ['Events'] 
        for category in categories:
            response = requests.get(self.MEDIAWIKI_BASE_URL + self.BASE_API, params={'action': 'ask', 'query': '[[Concept:'+category+']] [[Event:Date::<=' + future_date.strftime("%Y-%m-%d") + ']] [[Event:Date::>='+ pub_date.strftime("%Y-%m-%d") + ']] |?Event:Date|?Event:EndDate|?Event:Name|?Event:Location|?Event:Organiser/s|?Event:Source|?Event:Spotlight', 'format': 'json', 'formatversion': '2'})
            data = response.json()
            opp_info = {}
            if not data['query']['results']:
                return {}
            else:
                for page_title, page_data in data['query']['results'].items():
                    if 'printouts' in page_data and 'Event:Date' in page_data['printouts']:
                        type = 'Events'
                        name = page_data['printouts']['Event:Name'][0]
                        deadline = page_data['printouts']['Event:Date'][0]['raw']
                        deadline = deadline[2:]
                        lol = datetime.strptime(deadline, "%Y/%m/%d")
                        formatted_deadline = lol.strftime("%d-%m-%Y")
                        try:
                            endDate = page_data['printouts']['Event:EndDate'][0]['raw']
                            endDate = endDate[2:]
                            lol_2 = datetime.strptime(endDate, "%Y/%m/%d")
                            formatted_EndDate = lol_2.strftime("%d-%m-%Y")
                        except:
                            formatted_EndDate = "(っ °Д °;)っ"
						
                        
                        location = page_data['printouts']['Event:Location'][0]
                        source = page_data['printouts']['Event:Source'][0]
                        org = page_data['printouts']['Event:Organiser/s'][0]['fulltext']
                        
                        try:
                            spotlight = page_data['printouts']['Event:Spotlight'][0]
                            if spotlight == 't':
                                spotlight = True
                            else:
                                spotlight = False
                        except:
                            spotlight = False
                        
                        
                        opp_info = {'pagetitle': page_title, 'name': name, 'deadline': formatted_deadline, 'endDate': formatted_EndDate,'location': location, 'source' : source, 'org': org, 'spotlight': spotlight, 'text': ''}
                        
                        if type not in opp_page_list:
                            opp_page_list[type] = []
                        
                        opp_page_list[type].append(opp_info)
        
        return opp_page_list
        
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
        sorted_prj = dict(sorted(projects.items(), key=lambda item: datetime.strptime(item[1]['date'], "%d.%m.%Y" ), reverse=True) )
        newsletters = updated_cat_list.get('Newsletters', [])
        sorted_nl = dict(sorted(newsletters.items(), key=lambda item: datetime.strptime(item[1]['date'], "%d.%m.%Y" ), reverse=True) )
        most_recent_newsletter = next(iter(sorted_nl.items()))
        nav_elements = self.get_nav_menu()
        
        return render_template('publications.html', latest_title=most_recent_newsletter[0], projects=sorted_prj, newsletters=sorted_nl, nav_elements=nav_elements)
    
    def fetch_meetups(self):
        meetup_content, page_title = self.fetch_page('Meetups')
        return render_template('meetups.html', content=meetup_content, nav_elements=self.get_nav_menu() )
        
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
                
                if title in pages:
                    for index, page_title in enumerate(category_page_list[category]):
                        if title == page_title:
                            category_page_list[category][page_title].update({'pageid':pageid, 'title': title, 'source': source })
                            
        return category_page_list
    
    def fetch_all_activies(self, categories):
        category_page_list = {} 
        for category in categories:
            response = requests.get(self.MEDIAWIKI_BASE_URL + self.BASE_API, params={'action': 'ask', 'query': '[[Concept:'+category+']]|?Activities:Date|?Activities:Draft', 'format': 'json', 'formatversion': '2'})
            data = response.json()
            page_title_timestamps = {}
            for page_title, page_data in data['query']['results'].items():
                if 'printouts' in page_data and 'Activities:Date' in page_data['printouts']:
                    raw_timestamp = page_data['printouts']['Activities:Date'][0]['raw']
                    raw_timestamp = raw_timestamp[2:]
                    lol = datetime.strptime(raw_timestamp, "%Y/%m/%d")
                    formatted_date = lol.strftime("%d.%m.%Y")
                    if(page_data['printouts']['Activities:Draft'][0] == 'f'):
                        page_title_timestamps[page_title] = {'date': formatted_date, 'draft': page_data['printouts']['Activities:Draft'][0]}
                    
            category_page_list[category] = page_title_timestamps
        return category_page_list
      
    def fetch_all_pages(self, categories):
        category_page_list = {} 
        for category in categories:
            response = requests.get(self.MEDIAWIKI_BASE_URL + self.BASE_API, params={'action': 'ask', 'query': '[[Concept:'+category+']]|?Article:Date|?Article:Draft', 'format': 'json', 'formatversion': '2'})
            data = response.json()
            page_title_timestamps = {}
            for page_title, page_data in data['query']['results'].items():
                if 'printouts' in page_data and 'Article:Date' in page_data['printouts']:
                    raw_timestamp = page_data['printouts']['Article:Date'][0]['raw']
                    raw_timestamp = raw_timestamp[2:]
                    lol = datetime.strptime(raw_timestamp, "%Y/%m/%d")
                    formatted_date = lol.strftime("%d.%m.%Y")
                    if(page_data['printouts']['Article:Draft'][0] == 'f'):
                        page_title_timestamps[page_title] = {'date': formatted_date, 'draft': page_data['printouts']['Article:Draft'][0]}
                    
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
        try:
            page_title = data['parse']['title']
            page_content = data['parse']['text']['*']
            page_content, table = self.fix_html(page_content)
        except:
            page_title = 'Page not found'
            page_content = 'The page you are looking for does not exist.'
            table = None
        
        return render_template('index.html', title=page_title, cont=page_content, table=table)
        
    
    def fetch_page(self, title):
        # Make a request to MediaWiki API to get content of a specific page
        response = requests.get(self.MEDIAWIKI_BASE_URL + self.BASE_API, params={'action': 'parse', 'page': title, 'format': 'json'})
        data = response.json()
        # Extract page title and content
        page_title = data['parse']['title']
        page_content = data['parse']['text']['*']
        page_content, table = self.fix_html(page_content)
        page_date = re.search(r'\d{4}-\d{2}-\d{2}', data['parse']['text']['*'])
        
        if(page_date):
            date = page_date.group(0)
        else:
            date = None
            
        return page_content, page_title, date
    
    def get_nav_menu(self):
        response = requests.get(self.MEDIAWIKI_BASE_URL + self.BASE_API, params={'action': 'ask', 'query': '[[Concept:MainNavigation]]', 'format': 'json', 'formatversion': '2'})
        data = response.json()
        main_navigation_elements = {}
        for page_title, page_data in data['query']['results'].items():
            title = page_data.get('fulltext', '')
            if title == 'Publications':
                title = 'publications'
            main_navigation_elements[page_title] = {'title':title}
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
            link.string = link.string.strip()
            
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
        
        # Locate the table and store it in an object
        table = soup.find('table')
        
        # Remove inline styles by deleting the 'style' attribute
        if table and 'style' in table.attrs:
            del table['style']
        
        # Add the class 'table-cont' to the table (if not already removed)
        if table:
            table['class'] = table.get('class', []) + ['table-cont']
            
        comments = soup.find_all(string=lambda text: isinstance(text, Comment))
        comment = comments[-1] if comments else None
        
        # Insert the table before the comment
        if comment and table is not None:
            comment.insert_before(table.extract())
            
        table_html = str(table) if table else None  # Store the table HTML
        
        has_content = False
        # Check if the table has meaningful rows
        if table:
            rows = table.find_all('tr')
            has_content = False  # Assume no meaningful content

            for row in rows:
                cells = row.find_all(['td', 'th'])
                # Check if any cell has non-empty text
                if any(cell.get_text(strip=True) for cell in cells):
                    has_content = True
                    break
                
        if has_content is False:
            table_html = None
            
        
        # Remove the table from the main HTML
        if table:
            table.decompose()


        # Return the modified HTML
        return soup.prettify(), table_html
    
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

app = WikiApp(__name__)

if __name__ == '__main__':
    app.run(debug=True)
