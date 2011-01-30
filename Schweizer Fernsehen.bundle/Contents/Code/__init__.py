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
    Plugin.AddPrefixHandler(SF_PREFIX, GetShowOverview, 'Schweizer Fernsehen', 'icon-default.png', 'art-default.jpg')
    Plugin.AddViewGroup("Details", viewMode="InfoList", mediaType="items")
    MediaContainer.title1 = 'Schweizer Fernsehen'
    MediaContainer.art = R('art-default.jpg')
    HTTP.CacheTime = CACHE_INTERVAL

####################################################################################################
def UpdateCache():
    HTTP.Request(SF_SHOWS)
    HTTP.Request(SF_CHANNELS)

####################################################################################################
def GetShowOverview():
    dir = MediaContainer(viewGroup='Details')
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
    
    if previousEpisode or len(dir) > 0 or prev_month.year < 2000:
        dir.Append(Function(DirectoryItem(GetPreviousEpisodes, title=L("Episodes from ") + L(prev_month.strftime('%B')) + " " + str(prev_month.year), url=url), url=url, showTitle=showTitle))
    else:
        dir.Extend(GetPreviousEpisodes(sender, url, showTitle))

    return dir
