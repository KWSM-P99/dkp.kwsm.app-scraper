from bs4 import BeautifulSoup as _bs
import time
import urllib3
import json
import os
from pathlib import Path
from datetime import datetime, date
from dotenv import load_dotenv

load_dotenv()
# Load .env file that contains the following
'''
# .env
COOKIE="your cookie"
USER_AGENT="your user_agent"
'''

COOKIE = os.getenv('COOKIE')
USER_AGENT = os.getenv('USER_AGENT')

def get_all_characters() -> list :
    #uses the 'overview' page with all filters disabled to get a list of chars, sometimes fails due to table just not getting retrieved?
    soup = _bs(get_full_overview_page(), features='lxml')
    overview_table = soup.find('h2', string='Overview').find_next('table')
    players = overview_table.find_all('a', href=True)[18:]
    
    res = set() 
    for item in players:
        for citem in item:
            res.add(citem.string)
        
    return list(res)
    
    
def get_all_users():
    
    soup = _bs(get_userlist_table(), features='lxml')

    user_pages = int(soup.find('div', class_='pagination').find('ul', attrs={'data-pages':True})['data-pages'])
    users = {}
    for page in range(user_pages):
        print(f'Page: {page+1}')
        got_users = get_users_from_page(page)
        if page != user_pages - 1:
            if len(got_users) != 100:
                raise ValueError(f'problem, didnt get 100 users from non-tail page. Expected 100. Actual {len(got_users)}')
        users.update(got_users)
        for _ in range(3):
            print('.', end='', flush=True)
            time.sleep(1)
        print()
    return users
    
def get_users_from_page(page):
    
    req = get_userlist_table(page)
    #print(req.data)
    soup = _bs(req, features='lxml')
    user_table = soup.find('h1', string='Userlist ').find_next('table')
    users = user_table.find_all('a', href=True)
    
    res = {}
    count = 0
    for user in users:
        if user.span:
            res[user.string] = {'href': user['href'], 'characters': {}, 'dkp': None, 'stated_characters': int(user.parent.parent.find_all('td')[-1].text.strip()), 'registration_date': user.parent.parent.find_all('td')[-2].text.strip()}
            count += 1
    #expected character format: 
    #{'<name>': {'type': '...',
    #            'dkp_relative': 0}
    print(count)
    return res

def get_all_user_characters_from_userlist(userlist='users-w-chars.json', start_at=0):
    users = json.load(open(userlist, 'r'))
    character_user_map = {}
    
    count = 0
    for user in users:
        if start_at > count:
            count += 1
            continue
        href = users[user]['href']
        
        print(f'idx: {count}, {user}', end='', flush=True)
        chars = get_user_characters(href)
        print(f', count: {len(chars)}')
        print(chars)
        if users[user]['stated_characters'] != len(chars):
            raise ValueError('Characters stated on user list does not match parsed user page')
        dkp = 0
        for char in chars:
            users[user]['characters'].update(char)
            name = list(char.keys())[0]
            character_user_map[name] = user
            dkp += char[name]['dkp_relative']
        users[user]['dkp'] = dkp
        for _ in range(3):
            print('.', end='', flush=True)
            time.sleep(1)
        print()
        json.dump(character_user_map, open(f'character-user-map.json', 'w'), indent=2)
        json.dump(users, open(f'users-w-chars.json', 'w'), indent=2)
        count+=1
       
        
    
#return type: [(name, type, dkp_relative)]
def get_user_characters(user_href):
    #users = json.load(open('users.json', 'r'))
    
    #with open('user-data.html', 'w') as f:
    #    f.write(get_user_data(user_href))
    #with open('user-data.html') as f:
    #    soup = _bs(f, features="lxml")
    
    soup = _bs(get_user_data(user_href), features='lxml')
    
    if soup.find('div', id='characters') is None:
        return []
    
    if soup.find('div', id='characters').find_next('table').find_all('div'):
        #has multiple characters
        res = soup.find('div', id='characters').find_next('table').find_all('div')
        char_count = len(res[0].find_all('a'))
        #print(res[0].find_all('a'))
        start_idx = 1
        chars = []
    
        races = []
        classes = []
        for idx, item in enumerate(res[0].find_all('img')):
            if idx %2:
                classes.append(item['title'])
            else:
                races.append(item['title'])
            
        if len(classes) != char_count:
            classes = []
            races = []
            for _ in range(char_count):
                classes.append('Unknown')
                races.append('Unknown')   
        if len(races) != char_count:
            classes = []
            races = []
            for _ in range(char_count):
                classes.append('Unknown')
                races.append('Unknown')   
        
        #char_count skip
        #start_idx = 1
        #names
        names = []
        for idx in range(start_idx, char_count+start_idx):
            names.append(res[idx].text.strip())
            start_idx +=1 # Note: this does not change the end loop condition
        #level skip, total, cumlative, count, blank, cumulative
        start_idx += 2 + char_count + 2
        #types
        types = []
        for idx in range(start_idx, char_count+start_idx):
            types.append(res[idx].text.strip())
            start_idx +=1 # Note: this does not change the end loop condition
        #other type skip, blank, cumlative, count, blank, cumlative
        start_idx += 2 + char_count + 2
        #dkp
        dkp_relative = []
        for idx in range(start_idx, char_count+start_idx):
            dkp_relative.append(int(res[idx].text.strip()))
        
        for idx in range(char_count):
            chars.append({names[idx]: {'type': types[idx], 'class': classes[idx], 'race': races[idx], 'dkp_relative': dkp_relative[idx]}})
    else:
        res = soup.find('div', id='characters').find_next('table').tr.next_sibling.next_sibling.find_all('td')
        chars = []
    
        race = ''
        class_ = ''
        for idx, item in enumerate(res[0].find_all('img')):
            if idx %2:
                class_ = item['title']
            else:
                race = item['title']
                
        name = res[0].text.strip()
        type = res[3].text.strip()
        dkp_relative = int(res[4].text.strip())
        
        chars.append({name: {'type': type, 'class': class_, 'race': race, 'dkp_relative': dkp_relative}})
    
    return chars
    

def send_request(url):
    headers = {
        'User-agent': USER_AGENT, 
        'Cookie': COOKIE
        }
    http = urllib3.PoolManager()
    return http.request('GET', url, headers=headers)

def get_page(url, cache_filename):
    _date = date.today().isoformat()
    cache_filename = f'daily-cache/{_date}-{cache_filename}'
    if Path(cache_filename).is_file():
        page = open(cache_filename, 'r').read()
    else:
        url = url
        page = send_request(url).data.decode('UTF-8')
        with open(cache_filename, 'w') as f:
            f.write(page)
    return page

def get_full_overview_page():
    url = "https://dkp.kwsm.app/index.php/index_points?mdkpid=0&filter=&show_inactive=1&show_hidden=1&show_twinks=1&lb_mdkpid=1&lbc=0"
    cache_filename = 'full-overview-page.html'
    return get_page(url, cache_filename)
    
def get_userlist_table(page=0):
    url = "https://dkp.kwsm.app/index.php/User.html?s=&sort="
    if page:
        url += "&start="+str(page*100)
    return send_request(url).data.decode('UTF-8')
    
def get_user_data(user_url):
    url = "https://dkp.kwsm.app"+user_url
    cache_filename = f'user-{user_url}'
    return get_page(url, cache_filename)

def get_save_page_info(data, loc='data.html'):
    with open('data.html', 'w') as f:
        f.write(data)

"Aagent-u278.html?"
"Ichibo-u265.html?"
#res = get_user_characters("/index.php/User/Madbuff-u572.html?")
#res = get_users_from_page(0)
#res = get_all_users()

res = get_full_overview_page()

#json.dump(res, open(f'users.json', 'w'), indent=2)
#json.dump(res, open('overview-chars.json', 'w'), indent = 2)
print("main result:")
#print(res)
print(len(res))