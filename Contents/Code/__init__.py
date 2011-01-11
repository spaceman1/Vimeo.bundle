import re, string

VIMEO_PREFIX      = "/video/vimeo"
CACHE_INTERVAL    = 1800
VIMEO_NAMESPACE   = {'v':'http://www.w3.org/2005/Atom', 'm':'http://search.yahoo.com/mrss/'}
VIMEO_URL         = 'http://www.vimeo.com/'
VIMEO_LOAD_CLIP   = 'http://www.vimeo.com/moogaloop/load/clip:%s/local?param_md5=0&param_context_id=&param_force_embed=0&param_clip_id=3715286&param_show_portrait=0&param_multimoog=&param_server=vimeo.com&param_show_title=0&param_color=00ADEF&param_autoplay=0&param_show_byline=0&param_fullscreen=1&param_context=subscriptions|newest&param_force_info=undefined&context=subscriptions'
VIMEO_PLAY_CLIP   = 'http://www.vimeo.com/moogaloop/play/clip:%s/%s/%s/?q=%s&type=local'
VIMEO_DIRECTORY   = 'http://vimeo.com/%s/%s/page:%d'
VIMEO_SEARCH      = 'http://vimeo.com/search/videos/search:%s/%s/page:%d/sort:plays/format:detail'
CLIENT_CAP_HEADER = 'X-Plex-Client-Capabilities'

####################################################################################################
def Start():
  Plugin.AddPrefixHandler(VIMEO_PREFIX, MainMenu, 'Vimeo', 'icon-default.jpg', 'art-default.png')
  Plugin.AddViewGroup("Details", viewMode="InfoList", mediaType="items")
  MediaContainer.title1 = 'Vimeo'
  MediaContainer.content = 'Items'
  MediaContainer.art = R('art-default.png')
  DirectoryItem.thumb = R('icon-default.jpg')
  HTTP.CacheTime = CACHE_INTERVAL

####################################################################################################
def UpdateCache():
  HTTP.Request(VIMEO_URL+'channels').content
  HTTP.Request(VIMEO_URL+'channels/hd/videos/rss').content
  HTTP.Request(VIMEO_URL+'channels/staffpicks/videos/rss').content

####################################################################################################
def MainMenu():
  dir = MediaContainer()
  dir.Append(Function(DirectoryItem(GetMyStuff,       title=L("My Stuff"))))
  dir.Append(Function(DirectoryItem(GetVideosRSS,     title="Staff Picks", thumb=R('staffpicks.png')), name='channels/staffpicks/videos', title2='Staff Picks'))
  dir.Append(Function(DirectoryItem(FeaturedChannels, title="Featured Channels", thumb=R('featured.png'))))
  dir.Append(Function(DirectoryItem(GetVideosRSS,     title="High Def", thumb=R('hd.png')), name='channels/hd/videos', title2="High Def"))
  dir.Append(Function(DirectoryItem(Categories,       title="Channels", thumb=R('channels.png')), noun='channels', url='all'))
  dir.Append(Function(DirectoryItem(Categories,       title=L("Groups"), thumb=R('groups.png')), noun='groups', url='all', sort='members'))
  dir.Append(Function(SearchDirectoryItem(Search,     title=L("Search"), prompt=L("Search for Videos"), thumb=R('search.png'))))
  dir.Append(PrefsItem(L("Preferences..."), thumb=R('prefs.png')))
  
  return dir

####################################################################################################
def GetMyStuff(sender):
  dir = MediaContainer()

  # See if we need to log in.
  xml = HTML.ElementFromURL(VIMEO_URL + 'subscriptions/channels/sort:name', cacheTime=0)
  if xml.xpath('//title')[0].text != 'Your subscriptions on Vimeo':
    # See if we have any creds stored.
    if not Prefs['email'] and not Prefs['password']:
      return MessageContainer(header='Logging in', message='Please enter your email and password in the preferences.')
    # Try to log in
    Login()
    Log(xml.xpath('//title')[0].text)
    # Now check to see if we're logged in.
    xml = HTML.ElementFromURL(VIMEO_URL + 'subscriptions/channels/sort:name', cacheTime=0)
    if xml.xpath('//title')[0].text != 'Your subscriptions on Vimeo':
      return MessageContainer(header='Error logging in', message='Check your email and password in the preferences.')

  userUrl = None
  for item in xml.xpath('//li[@class="firstborn"]/ul/li/a'):
    if item.find('span') is not None:
      url = item.get('href')
      Log(url)
      junk, noun, link = url.split('/')
      title = item.text# + item.find('span').text
      if item.text.strip() == 'My Likes':
        userUrl = name=item.get('href')[1:]
        dir.Append(Function(DirectoryItem(GetVideosRSS, title), name=userUrl, title2="My Likes"))
      elif item.text.strip() == 'My Groups':
        dir.Append(Function(DirectoryItem(GetDirectory, title), noun=noun, url=link, sort='name', narrow='joined'))
      elif item.text.strip() == 'My Channels':
        dir.Append(Function(DirectoryItem(GetDirectory, title), noun=noun, url=link, sort='name', narrow='subscribe'))
      elif item.text.strip() == 'My Videos':
        dir.Append(Function(DirectoryItem(GetVideosRSS, title), name=item.get('href')[1:], title2='My Videos'))
        dir.Append(Function(DirectoryItem(GetContacts, "My Contacts"), url=item.get('href').replace('videos', 'contacts')))
    
  dir.Append(Function(DirectoryItem(GetVideosRSS, 'My Subscriptions'), name=userUrl.replace('likes','subscriptions/videos'), title2='My Subscriptions'))

  return dir

####################################################################################################
def GetContacts(sender, url):
  dir = MediaContainer(viewGroup='Details', title2=sender.itemTitle)

  url += '/sort:name'
  for contact in HTML.ElementFromURL(VIMEO_URL + url).xpath('//div[@class="contact"]'):
    thumb = contact.find('img').get('src')
    title = contact.xpath('div[@class="deleter"]')[0].xpath('span[@class="greyd"]')[0].text

    info = contact.xpath('div/div[@class="info"]')[0]
    try:
      subtitle = info.xpath('div[@class="location"]')[0].text + "\n"
    except:
      subtitle = ""
    subtitle += info.xpath('div[@class="date"]')[0].text

    summary = '\n'
    try:
        summary += info.xpath('a[@class="contacts"]')[0].text + ", "
    except:
        pass

    try:
        summary += info.xpath('a[@class="videos"]')[0].text
        url = info.xpath('a[@class="videos"]')[0].get('href')
        dir.Append(Function(DirectoryItem(GetVideosRSS, title=title, subtitle=subtitle, thumb=thumb, summary=summary), name=url, title2=title))
    except:
        # doesn't have any videos for some reason.. skip
        pass

  return dir

####################################################################################################
def FeaturedChannels(sender):
  dir = MediaContainer(title2='Featured Channels')
  for c in HTML.ElementFromURL(VIMEO_URL + 'channels').xpath("//div[@class='badge']"):
    title = c.find('a').get('title')
    thumb = re.findall("'(.*)'", c.get('style'))[0]
    url = c.find('a').get('href')
    url = url[url.rfind('/')+1:]
    dir.Append(Function(DirectoryItem(GetVideosRSS, title, thumb=thumb), name='channels/' + url + '/videos', title2=title))
  return dir

####################################################################################################
def Categories(sender, noun, url, sort='subscribed'):
  dir = MediaContainer(viewGroup='Details', title2='Channels')
  for category in HTML.ElementFromURL(VIMEO_URL + 'channels').xpath('//div[@id="cloud"]/ul/li'):
    title = string.capwords(category.find('a').text)
    subtitle = category.find('span').text + ' ' + noun
    cat = category.find('a').get('href')
    cat = cat[cat.find(':')+1:]
    dir.Append(Function(DirectoryItem(GetDirectory, title, subtitle=subtitle), category=cat, noun=noun, url=url, sort=sort))
  return dir

####################################################################################################
def GetDirectory(sender, category=None, noun=None, url=None, page=1, sort='subscribed', narrow=None):
  dir = MediaContainer(viewGroup='Details', title2=sender.itemTitle, replaceParent=(page>1))

  the_url = VIMEO_DIRECTORY % (noun, url, page)
  if category is not None:
    the_url += '/category:%s' % category
  if sort is not None:
    the_url += '/sort:%s' % sort
  if narrow is not None:
    the_url += '/narrow:%s' % narrow

  if url == 'channels' and narrow is not None:
    xpath = '//ul[@id="channel_listing"]/li'
    xp_title = 'div[@class="digest"]/div[@class="channel_title"]/a'
    xp_subtitle = 'div[@class="digest"]/div[@class="counts"]'
    xp_desc = 'div[@class="digest"]/div[@class="descrip"]'
    full_subtitle = True
    noun = 'channels'
    sort = 'newest'
  elif url == 'groups' and narrow is not None:
    xpath = '//ul[@id="group_listing"]/li'
    xp_title = 'div[@class="digest"]/div[@class="group_title"]/a'
    xp_subtitle = 'div[@class="digest"]/div[@class="counts"]'
    xp_desc = 'div[@class="digest"]/div[@class="descrip"]'
    full_subtitle = True
    noun = 'groups'
  else:
    xpath = '//div[@class="item last"]'
    xp_title= 'div/div[@class="title"]/a'
    xp_subtitle = 'div/div[@class="date"]'
    xp_desc = 'div/div[@class="description"]'
    full_subtitle = False

  for channel in HTML.ElementFromURL(the_url).xpath(xpath):
    title = channel.xpath(xp_title)[0].text
    subtitle_items = [e for e in channel.xpath(xp_subtitle)[0].itertext()]
    subtitle = "".join(subtitle_items[0:1]).strip()
    if len(subtitle) == 0 or full_subtitle == True:
      subtitle = "".join(subtitle_items).strip()
    try: desc = channel.xpath(xp_desc)[0].text
    except: desc =''
    link = channel.xpath('div[@class="channel_thumb"]/a')[0]
    thumb = link.find('img').get('src')
    channel = link.get('href')
    channel = channel[channel.rfind('/')+1:]
    dir.Append(Function(DirectoryItem(GetVideosRSS, title=title, summary=desc, subtitle=subtitle, thumb=thumb), name=noun+'/'+channel+'/videos', title2=title))

  dir.Append(Function(DirectoryItem(GetDirectory, title="More..."), category=category, noun=noun, url=url, sort=sort, narrow=narrow, page=page+1))
  return dir

####################################################################################################
def Search(sender, query, page=1):
  dir = MediaContainer(viewGroup='Details', title2='Search Results', replaceParent=(page>1))
  query = query.replace(' ', '+')
  
  # Need to get the security token.
  vimeo_page = HTML.ElementFromURL(VIMEO_URL)
  security_token = vimeo_page.xpath('//input[@id="xsrft"]')[0].get('value')[0:8]
  
  for result in HTML.ElementFromURL(VIMEO_SEARCH % (query, security_token, page), headers={"Cookie" : "searchtoken="+security_token}).xpath('//div[@class="item last"]'):
    title = result.xpath('div/div[@class="title"]/a')[0].text
    subtitle_items = [e.strip() for e in result.xpath('div/div[@class="date"]')[0].itertext()]
    subtitle = "%s (%s plays)" % (subtitle_items[0], subtitle_items[2])
    try: desc = result.xpath('div/div[@class="description"]')[0].text
    except: desc =''
    try:
        link = result.xpath('div[@class="thumbnail_box"]/a[@class="thumbnail"]')[0]
        thumb = link.find('img').get('src')
        key = link.get('href')[1:]
    except:
        PMS.Log(XML.StringFromElement(result))
        continue
    
    dir.Append(
      VideoItem(
        title = title,
        subtitle = subtitle,
        summary = desc,
        thumb = thumb,
        items = URLService.MediaItemsForURL('http://www.vimeo.com/' + key)
      ))
    
  dir.Append(Function(DirectoryItem(Search, title="More..."), query=query, page=page+1))
  return dir

####################################################################################################
def GetVideosRSS(sender, name, title2):
  cookies = HTTP.GetCookiesForURL(VIMEO_URL)

  dir = MediaContainer(viewGroup='Details', title2=title2, httpCookies=cookies)
  for video in XML.ElementFromURL(VIMEO_URL + name + '/rss', errors="ignore").xpath('//item', namespaces=VIMEO_NAMESPACE):
    title = video.find('title').text
    date = Datetime.ParseDate(video.find('pubDate').text).strftime('%a %b %d, %Y')
    
    try:
      thumb = video.xpath('m:content/m:thumbnail', namespaces=VIMEO_NAMESPACE)[0].get('url')
      key = video.xpath('m:content/m:player', namespaces=VIMEO_NAMESPACE)[0].get('url')
      key = key[key.rfind('=')+1:]
      summary = String.StripTags(video.find('description').text)
      
      dir.Append(
        VideoItem(
          title = title,
          subtitle = date,
          summary = summary,
          thumb = thumb,
          items = URLService.MediaItemsForURL('http://www.vimeo.com/' + key)
        ))
  
    except:
      Log.Exception("Error appending video")
  return dir

####################################################################################################
def Login():
  xsrft = HTML.ElementFromURL('http://www.vimeo.com/log_in', cacheTime=0).xpath('//input[@id="xsrft"]')[0].get('value')

  values = {
     'sign_in[email]' : Prefs['email'],
     'sign_in[password]' : Prefs['password'],
     'token' : xsrft
  }

  headers = {
     'Cookie' : 'xsrft=' + xsrft
  }

  x = HTTP.Request('http://www.vimeo.com/log_in', values, headers).content
