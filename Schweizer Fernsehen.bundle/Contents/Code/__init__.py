import re
import datetime
import urlparse

SF_PREFIX   = '/video/schweizerfernsehen'
SF_ROOT     = 'http://www.videoportal.sf.tv'
SF_SHOWS    = SF_ROOT + '/sendungen'
SF_CHANNELS = SF_ROOT + '/channels'
SF_SEARCH   = SF_ROOT + '/suche'

CACHE_INTERVAL = 3600

####################################################################################################
def Start():
    Plugin.AddPrefixHandler(SF_PREFIX, MainMenu, 'Schweizer Fernsehen', 'icon-default.jpg', 'art-default.jpg')
    Plugin.AddViewGroup("Details", viewMode="InfoList", mediaType="items")
    MediaContainer.title1 = 'Schweizer Fernsehen'
    MediaContainer.art = R('art-default.jpg')
    HTTP.CacheTime = CACHE_INTERVAL

####################################################################################################
def UpdateCache():
    HTTP.Request(SF_SHOWS)
    HTTP.Request(SF_CHANNELS)

####################################################################################################
def MainMenu():
    dir = MediaContainer()
    dir.Append(Function(DirectoryItem(GetShowOverview,   title=L("Shows"), thumb=R('icon-default.jpg'))))
    dir.Append(Function(SearchDirectoryItem(Search,       title=L("Search"), prompt=L("Search for Episodes"), thumb=R('search.png'))))
    return dir

####################################################################################################
def GetChannelsMenu(sender):
    dir = MediaContainer(viewGroup='Details', title2=sender.itemTitle)
    xml = HTML.ElementFromURL(SF_CHANNELS)
    for show in xml.xpath('//div[@class="channel"]'):
        url = SF_ROOT + show.xpath('div[@class="keyvisual"]/a')[0].get('href')
        title = show.xpath('div[@class="keyvisual"]/a/img')[0].get('alt')
        description = show.xpath('div[@class="channel_info"]/p')[0].text
        try: thumb = SF_ROOT + show.xpath('div[@class="keyvisual"]/a/img')[0].get('src')
        except: thumb = None
        dir.Append(WebVideoItem(url, title=title, thumb=thumb, summary=description))
    return dir

####################################################################################################
def GetShowOverview(sender):
    dir = MediaContainer(viewGroup='Details', title2=sender.itemTitle)
    xml = HTML.ElementFromURL(SF_SHOWS)
    for show in xml.xpath('//div[@class="az_row"]'):
        key = SF_ROOT + show.find('a').get('href')
        title = show.xpath('a[@class="sendung_name"]')[0].text
        description = show.xpath('p[@class="az_description"]')[0].text
        try:
            thumb = re.sub("width=\d+", "width=200", show.xpath('a/img')[0].get('src'))
        except: thumb = None
        dir.Append(Function(DirectoryItem(GetEpisodeMenu, title=title, thumb=thumb, summary=description, url=key), url=key))
    return dir

####################################################################################################
def GetEpisodeMenu(sender, url):
    dir = MediaContainer(viewGroup='Details', title2=sender.itemTitle)
    xml = HTML.ElementFromURL(url)
    try:
        show = xml.xpath('//div[@class="act_sendung_info"]')[0]
        video_url = show.find('a').get('href').split(';')[0]

        title = show.xpath('div/h2/a')[0].text
        summary = ""
        for info_item in show.xpath('//ul[@class="sendung_beitraege"]/li/a'):
            summary = summary + info_item.text + "\n"
        try:
            thumb = re.sub("width=\d+", "width=200", show.xpath('a/img')[0].get('src'))
        except: thumb = None
        dir.Append(WebVideoItem(SF_ROOT + video_url, title=title, thumb=thumb, summary=summary))
    except:
        pass

    dir.Extend(GetPreviousEpisodes(sender, url, sender.itemTitle, previousEpisode=(len(dir) > 0)))

    if (len(dir) == 0):
        dir.Append(DirectoryItem("none", L("No Episodes")))

    return dir

####################################################################################################
def GetPreviousEpisodes(sender, url, showTitle, previousEpisode=False):
    dir = MediaContainer(viewGroup='Details', title2=showTitle)
    xml = HTML.ElementFromURL(url)

    previous = xml.xpath('//div[@class="prev_sendungen"]')[0]
    for show in previous.xpath('//div[@class="comment_row"]'):
        try:
            video_url = SF_ROOT + show.xpath('div[@class="left_innner_column"]/a')[0].get('href').split(';')[0]

            title = show.xpath('div[@class="sendung_content"]/a/strong')[0].text
            summary = ""
            for info_item in show.xpath('div[@class="sendung_content"]/ul/li/a'):
                summary = summary + info_item.text + "\n"
            try:
                thumb = re.sub("width=\d+", "width=200", show.xpath('div/a/img[@class="thumbnail"]')[0].get('src'))
            except: thumb = None
            dir.Append(WebVideoItem(video_url, title=title, thumb=thumb, summary=summary))
        except:
            pass

    base_url = url.split('&page=', 1)[0]
    try:
        current_page = int(xml.xpath('//p[@class="pagination"]/a[@class="act"]')[0].text)
        max_page = 1
        try:
            for page in xml.xpath('//p[@class="pagination"]/a'):
                if (page.get('href')):
                    page_nr = int(page.get('href').rsplit('=',1)[1])
                    if (page_nr > max_page):
                        max_page = page_nr
        except:
            pass

        if (current_page < max_page):
            next_url = base_url + "&page=" + str(current_page + 1)
            dir.Append(Function(DirectoryItem(GetPreviousEpisodes, title=L("Previous Episodes"), url=next_url), url=next_url, showTitle=showTitle))
            return dir
    except:
        #no additional pages
        pass

    if base_url.find("&period=") != -1:
        (url, a, date) = base_url.rpartition("&period=")
        (year, a, month) = date.partition("-")
        year = int(year)
        month = int(month)
    else:
        year = datetime.date.today().year
        month = datetime.date.today().month
    
    prev_month = datetime.date(year=year if month != 1 else (year - 1), month=(month - 1) if month > 1 else 12, day=1)
    url = url + "&period=" + str(prev_month.year) + "-" + "%02d" % prev_month.month
    
    if previousEpisode or len(dir) > 0 or prev_month.year < datetime.date.today().year - 3:
        dir.Append(Function(DirectoryItem(GetPreviousEpisodes, title=L("Episodes from ") + L(prev_month.strftime('%B')) + " " + str(prev_month.year), url=url), url=url, showTitle=showTitle))
    else:
        dir.Extend(GetPreviousEpisodes(sender, url, showTitle))

    return dir

####################################################################################################
def Search(sender, query, page=None, start_video=0):
    dir = MediaContainer(viewGroup='Details', title2=query)

    search_url = SF_SEARCH + '?query=' + query
    if (page):
        search_url += "&page=" + str(page)

    xml = HTML.ElementFromURL(search_url)
    #shows
    if start_video == 0:
        try:
            shows = xml.xpath('//div[@id="search_result_sendungen"]')[0]
            for sendung in shows.xpath('div/div[@class="reiter_item"]'):
                url = SF_ROOT + sendung.xpath('h3/a[@class="title"]')[0].get('href')
                title = sendung.xpath('h3/a[@class="title"]/strong')[0].text
                try: thumb = sendung.xpath('h3/a[@class="sendung_img_wrapper"]/img')[0].get('src')
                except: thumb = None
                dir.Append(Function(DirectoryItem(GetEpisodeMenu, title=title, thumb=thumb, url=url), url=url))
        except:
            pass

    #Videos
    number_shows = 0;
    try:
        shows = xml.xpath('//div[@id="search_result_videos"]')[0]
        for show in shows.xpath('div[@class="result_video_row"]')[start_video:]:
            video_url = SF_ROOT + show.xpath('div/h3/a[@class="video_title"]')[0].get('href').split(';')[0]

            try: thumb = show.xpath('a[@class="sendung_img_wrapper"]/img')[0].get('src')
            except: thumb = None
            try: title = show.xpath('div/h3/a[@class="video_title"]')[0].text
            except: title = None
            try: summary = show.xpath('div/p[@class="video_description"]')[0].text
            except: summary = None
            dir.Append(WebVideoItem(video_url, title=title, thumb=thumb, summary=summary))

            number_shows += 1
            if number_shows == 9:
                dir.Append(Function(DirectoryItem(Search, title=L("More Results"), url=SF_SEARCH), query=query, page=page, start_video=(start_video + number_shows)))
                return dir
    except:
        pass
    try:
        current_page = int(xml.xpath('//div[@id="skim_results"]/a[@class="act_site"]')[0].text)
        max_page = 1
        try:
            for page in xml.xpath('//div[@id="skim_results"]/a'):
                if (page.get('href')):
                    page_nr = int(page.get('href').rsplit('=',1)[1])
                    if (page_nr > max_page):
                        max_page = page_nr
        except:
            pass

        if (current_page < max_page):
            dir.Append(Function(DirectoryItem(Search, title=L("More Results"), url=SF_SEARCH), query=query, page=(current_page + 1)))
            return dir
    except:
        #no additional pages
        pass

    return dir

