import re, string
from PMS import *
from PMS.Objects import *
from PMS.Shortcuts import *

SF_PREFIX = '/video/schweizerfernsehen'
SF_ROOT   = 'http://videoportal.sf.tv'
SF_SENDUNGEN = SF_ROOT + '/sendungen'
SF_CHANNELS  = SF_ROOT + '/channels'
SF_SEARCH    = SF_ROOT + '/suche'

CACHE_INTERVAL = 3600

####################################################################################################
def Start():
  Plugin.AddPrefixHandler(SF_PREFIX, MainMenu, 'Schweizer Fernsehen', 'icon-default.jpg', 'art-default.jpg')
  Plugin.AddViewGroup("Details", viewMode="InfoList", mediaType="items")
  MediaContainer.title1 = 'Schweizer Fernsehen'
  MediaContainer.content = 'Items'
  MediaContainer.art = R('art-default.jpg')
  HTTP.SetCacheTime(CACHE_INTERVAL)

####################################################################################################
def UpdateCache():
  HTTP.Request(SF_SENDUNGEN)
  HTTP.Request(SF_CHANNELS)
  
####################################################################################################
def MainMenu():
  dir = MediaContainer()
  dir.Append(Function(DirectoryItem(GetSendungenMenu,   title="Sendungen")))
  dir.Append(Function(DirectoryItem(GetChannelsMenu,    title="Channels")))
  dir.Append(Function(SearchDirectoryItem(Search,       title=L("Suche..."), prompt=L("Search for Interviews"), thumb=R('search.png'))))
  return dir

####################################################################################################
def GetChannelsMenu(sender):
  dir = MediaContainer(viewGroup='Details', title2=sender.itemTitle)
  xml = XML.ElementFromURL(SF_CHANNELS, True)
  for sendung in xml.xpath('//div[@class="channel"]'):
    url = SF_ROOT + sendung.xpath('div[@class="keyvisual"]/a')[0].get('href')
    title = sendung.xpath('div[@class="keyvisual"]/a/img')[0].get('alt')
    description = sendung.xpath('div[@class="channel_info"]/p')[0].text
    try: thumb = SF_ROOT + sendung.xpath('div[@class="keyvisual"]/a/img')[0].get('src')
    except: thumb = None
    dir.Append(WebVideoItem(url, title=title, thumb=thumb, summary=description))
  return dir

####################################################################################################
def GetSendungenMenu(sender):
  dir = MediaContainer(viewGroup='Details', title2=sender.itemTitle)
  xml = XML.ElementFromURL(SF_SENDUNGEN, True)
  for sendung in xml.xpath('//div[@class="az_row"]'):
    key = SF_ROOT + sendung.find('a').get('href')
    title = sendung.xpath('a[@class="sendung_name"]')[0].text
    description = sendung.xpath('p[@class="az_description"]')[0].text
    try: thumb = sendung.xpath('a/img')[0].get('src')
    except: thumb = None
    dir.Append(Function(DirectoryItem(GetSendungMenu, title=title, thumb=thumb, summary=description, url=key), url=key))
  return dir

####################################################################################################
def GetSendungMenu(sender, url):
	dir = MediaContainer(viewGroup='Details', title2=sender.itemTitle)
	xml = XML.ElementFromURL(url, True)
	sendung = xml.xpath('//div[@class="act_sendung_info"]')[0]
	video = SF_ROOT + sendung.find('a').get('href')
	title = sendung.xpath('div/h2/a')[0].text
	summary = ""
	for info_item in sendung.xpath('//ul[@class="sendung_beitraege"]/li/a'):
		summary = summary + info_item.text + "\n"
	try: thumb = sendung.xpath('a/img')[0].get('src')
	except: thumb = None
	dir.Append(WebVideoItem(video, title=title, thumb=thumb, summary=summary))
	
	previous = xml.xpath('//div[@class="prev_sendungen"]')[0]
	for sendung in previous.xpath('//div[@class="comment_row"]'):
		try:
			video = SF_ROOT + sendung.xpath('div[@class="left_innner_column"]/a')[0].get('href')
			title = sendung.xpath('div[@class="sendung_content"]/a/strong')[0].text
			summary = ""
			for info_item in sendung.xpath('div[@class="sendung_content"]/ul/li/a'):
				summary = summary + info_item.text + "\n"
			try: thumb = sendung.xpath('div/a/img[@class="thumbnail"]')[0].get('src')
			except: thumb = None
			dir.Append(WebVideoItem(video, title=title, thumb=thumb, summary=summary))
		except:
			pass
		
	return dir

####################################################################################################
def Search(sender, query):
	dir = MediaContainer(viewGroup='Details', title2=query)
	
	xml = XML.ElementFromURL(SF_SEARCH + '?query=' + query, True)
	#sendungen
	try:
		sendungen = xml.xpath('//div[@id="search_result_sendungen"]')[0]
		for sendung in sendungen.xpath('div/div[@class="reiter_item"]'):
			url = SF_ROOT + sendung.xpath('h3/a[@class="title"]')[0].get('href')
			title = sendung.xpath('h3/a[@class="title"]/strong')[0].text
			try: thumb = sendung.xpath('h3/a[@class="sendung_img_wrapper"]/img')[0].get('src')
			except: thumb = None
			dir.Append(Function(DirectoryItem(GetSendungMenu, title=title, thumb=thumb, url=url), url=url))
	except:
		pass
	
	#Videos
	try:
		sendungen = xml.xpath('//div[@id="search_result_videos"]')[0]
		for sendung in sendungen.xpath('div[@class="result_video_row"]'):
			url = SF_ROOT + sendung.xpath('div/h3/a[@class="video_title"]')[0].get('href')
			title = sendung.xpath('div/h3/a[@class="video_title"]')[0].text
			description = sendung.xpath('div/p[@class="video_description"]')[0].text + ' (' + sendung.xpath('div/div[@class="fill_from_bottom"]/p')[0].text + ')'
			try: thumb = sendung.xpath('div/h3/a[@class="sendung_img_wrapper"]/img')[0].get('src')
			except: thumb = None
			dir.Append(WebVideoItem(url, title=title, thumb=thumb, summary=description))
	except:
		pass
		
	return dir

