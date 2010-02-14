import re, string
import datetime
import urlparse
from PMS import *
from PMS.Objects import *
from PMS.Shortcuts import *

SF_PREFIX   = '/video/schweizerfernsehen'
SF_ROOT     = 'http://videoportal.sf.tv'
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
    HTTP.SetCacheTime(CACHE_INTERVAL)

####################################################################################################
def UpdateCache():
    HTTP.Request(SF_SHOWS)
    HTTP.Request(SF_CHANNELS)

####################################################################################################
def MainMenu():
    dir = MediaContainer()
    dir.Append(Function(DirectoryItem(GetShowOverview,   title=L("Shows"), thumb=R('icon-default.jpg'))))
    #dir.Append(Function(DirectoryItem(GetChannelsMenu,    title=L("Channels"))))
    dir.Append(Function(SearchDirectoryItem(Search,       title=L("Search"), prompt=L("Search for Episodes"), thumb=R('search.png'))))
    #dir.Append(PrefsItem(                                 title=L("Preferences"), thumb=R('icon-prefs.png')))
    return dir

####################################################################################################
def GetChannelsMenu(sender):
    dir = MediaContainer(viewGroup='Details', title2=sender.itemTitle)
    xml = XML.ElementFromURL(SF_CHANNELS, True)
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
    xml = XML.ElementFromURL(SF_SHOWS, True)
    for show in xml.xpath('//div[@class="az_row"]'):
        key = SF_ROOT + show.find('a').get('href')
        title = show.xpath('a[@class="sendung_name"]')[0].text
        description = show.xpath('p[@class="az_description"]')[0].text
        try: thumb = show.xpath('a/img')[0].get('src')
        except: thumb = None
        dir.Append(Function(DirectoryItem(GetEpisodeMenu, title=title, thumb=thumb, summary=description, url=key), url=key))
    return dir

####################################################################################################
def SelectVideoMethod(json_result, title=None, subtitle=None, thumb=None, art=None, summary=None):
    best_bitrate = 0
    quality_str = Prefs.Get("quality")
    if (quality_str.startswith("High")):
        quality = 1500
    elif(quality_str.startswith("Medium")):
        quality = 1200
    elif(quality_str.startswith("Low")):
        quality = 500
    elif(quality_str.startswith("Very")):
        quality = 110

    for stream in json_result['streaming_urls']:
        bitrate = int(stream['bitrate'])
        if (bitrate > best_bitrate and bitrate <= quality):
            best_bitrate = bitrate
            best_stream = stream

    if best_stream:
        if title == None:
            title = json_result['video']['description_title']
        duration = ((int(json_result['mark_out']) - int(json_result['mark_in'])) * 1000)
        video_url = best_stream['url']
        width = int(best_stream['frame_width'])
        height = int(best_stream['frame_height'])

        if (best_stream['codec_video'] == "wmv3"):
            return VideoItem(video_url, width=width, height=height, title=title, summary=summary, duration=duration, thumb=thumb, art=art, subtitle=subtitle)

        elif (best_stream['codec_video'] == "vp6f"):
            video_parts = video_url.split("ondemand/");
            video = video_parts[0] + "ondemand/"
            clip = "".join(video_parts[1:]).strip(".flv")
            return RTMPVideoItem(video, clip=clip, width=width, height=height, title=title, summary=summary, duration=duration, thumb=thumb, art=art, subtitle=subtitle)

####################################################################################################
def GetJSON(video_url):
    video_url_parsed = urlparse.urlsplit(video_url)
    video = SF_ROOT + '/cvis/segment/' + video_url_parsed.query.split('=',2)[1].split(';',2)[0] + '/.json?nohttperr=1;omit_video_segments_validity=1;omit_related_segments=1'

    video_http = HTTP.Request(video)
    video_http = video_http[10:-2]
    return JSON.ObjectFromString(video_http)

####################################################################################################
def GetEpisodeMenu(sender, url):
    dir = MediaContainer(viewGroup='Details', title2=sender.itemTitle)
    xml = XML.ElementFromURL(url, True)
    try:
        show = xml.xpath('//div[@class="act_sendung_info"]')[0]
        video_url = show.find('a').get('href')
        video_json = GetJSON(video_url)

        title = show.xpath('div/h2/a')[0].text
        summary = ""
        for info_item in show.xpath('//ul[@class="sendung_beitraege"]/li/a'):
            summary = summary + info_item.text + "\n"
        try: thumb = show.xpath('a/img')[0].get('src')
        except: thumb = None
        dir.Append(WebVideoItem(SF_ROOT + video_url, title=title, thumb=thumb, summary=summary))
        #dir.Append(SelectVideoMethod(video_json, thumb=thumb, summary=summary))
    except:
        pass

    dir.Extend(GetPreviousEpisodes(sender, url))

    if (len(dir) == 0):
        dir.Append(DirectoryItem("none", L("No Episodes")))

    return dir

####################################################################################################
def GetPreviousEpisodes(sender, url):
    dir = MediaContainer(viewGroup='Details', title2=sender.itemTitle)
    xml = XML.ElementFromURL(url, True)

    previous = xml.xpath('//div[@class="prev_sendungen"]')[0]
    for show in previous.xpath('//div[@class="comment_row"]'):
        try:
            video_url = SF_ROOT + show.xpath('div[@class="left_innner_column"]/a')[0].get('href')
            video_json = GetJSON(video_url)

            title = show.xpath('div[@class="sendung_content"]/a/strong')[0].text
            summary = ""
            for info_item in show.xpath('div[@class="sendung_content"]/ul/li/a'):
                summary = summary + info_item.text + "\n"
            try: thumb = show.xpath('div/a/img[@class="thumbnail"]')[0].get('src')
            except: thumb = None
            dir.Append(WebVideoItem(video_url, title=title, thumb=thumb, summary=summary))
            #dir.Append(SelectVideoMethod(video_json, thumb=thumb, summary=summary))
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
            dir.Append(Function(DirectoryItem(GetPreviousEpisodes, title=L("Previous Episodes"), url=next_url), url=next_url))
            return dir
    except:
        #no additional pages
        pass

    if base_url.find("&period=") != -1:
        (url, a, date) = base_url.rpartition("&period=")
        (year, a, month) = date.partition("-")
        current = datetime.date(year=int(year), month=int(month), day=1)
        prev_month = current - datetime.timedelta(days=29)
    else:
        prev_month = datetime.date.today() - datetime.timedelta(days=29)
    url = url + "&period=" + str(prev_month.year) + "-" + "%02d" % prev_month.month
    dir.Append(Function(DirectoryItem(GetPreviousEpisodes, title=L("Episodes from ") + L(prev_month.strftime('%B')), url=url), url=url))

    return dir

####################################################################################################
def Search(sender, query, page=None, start_video=0):
    dir = MediaContainer(viewGroup='Details', title2=query)

    search_url = SF_SEARCH + '?query=' + query
    if (page):
        search_url += "&page=" + str(page)

    xml = XML.ElementFromURL(search_url, True)
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
            video_url = SF_ROOT + show.xpath('div/h3/a[@class="video_title"]')[0].get('href')
            video_json = GetJSON(video_url)

            try: thumb = show.xpath('div/h3/a[@class="sendung_img_wrapper"]/img')[0].get('src')
            except: thumb = None
            try: title = video_json['description_title']
            except: title = None
            try: summary = video_json['description_lead']
            except: summary = None
            dir.Append(SelectVideoMethod(video_json, title=title, summary=summary, thumb=thumb))

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

