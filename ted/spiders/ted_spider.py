import scrapy
from scrapy.spider import Spider
from scrapy.selector import Selector
from ted.items import TedItem
from scrapy.http import Request
from BeautifulSoup import BeautifulSoup as BS
import re
import json
import os

class CustomRequest(Request):
    def __init__(self,*args,**kwargs):
        item = kwargs.pop('item',None)
        super(Request,self).__init__(*args,**kwargs)


class TedSpider(scrapy.Spider):
    name = "TED"
    allowed_domains = ["ted.com"]
    sdir = None
    root_dir = "/home/michael/ted_scrapy_dir"
    start_urls =[
            "http://www.ted.com/playlists/171/the_most_popular_talks_of_all"
            ]

    def parse(self,response):
        sel = Selector(response)
        sites = sel.xpath('/html/body/div/div[2]/div/div[2]/div[3]/div/div[1]/ul/li')
        items =[]
        for site in sites:
            item = TedItem()
            # speaker /html/body/div/div[2]/div/div[2]/div[3]/div/div[1]/ul/li[1]/div/div/div[1]/span
            # title /html/body/div/div[2]/div/div[2]/div[3]/div/div[1]/ul/li[1]/div/div/div[1]/h9
            #/html/body/div/div[2]/div/div[2]/div[3]/div/div[1]/ul/li[1]/div/div/div[1]/span/a
            item['speaker'] = site.xpath('div/div/div[1]/span/a/text()').extract()
            self.sdir = "%s/%s" % (self.root_dir,item['speaker'][0]) 
            if not os.path.exists(self.sdir):
                os.mkdir(self.sdir)
            #/html/body/div/div[2]/div/div[2]/div[3]/div/div[1]/ul/li[1]/div/div/a/span/span[2]
            item['duration'] = site.xpath('div/div/a/span/span[2]/text()').extract()
            #/html/body/div/div[2]/div/div[2]/div[3]/div/div[1]/ul/li[1]/div/div/div[1]/h9/a
            item['title'] = site.xpath('div/div/div[1]/h9/a/text()').extract()
            item['url'] = site.xpath('div/div/div[1]/h9/a/@href').extract()
            #print "url is:",item['url'][0]
            #/html/body/div[1]/div[2]/div/div[2]/div[1]/div[1]/div[2]/div/div/div[2]/a
            #items.extend(self.make_requests_from_url(item['url'][0]).replace(callback=self.parse))
            #/html/body/div/div[2]/div/div[2]/div[3]/div/div[1]/ul/li[1]/div/div/div[2]/div[1]
            item['info'] = site.xpath('div/div/div[2]/div[1]/text()').extract()
            items.append(item)
        #print items
        for item in items:
            #print item['url']
            yield  Request('http://%s%s' % (self.allowed_domains[0],item['url'][0]),
                    callback=self.parse_speaker,meta={'item':item})

    def parse_speaker(self,response):
        item = response.meta['item']
        #url = response.url.split('//')[1].split('/')
        sel = Selector(response)
        sites = sel.xpath('/html/body/div[1]/div[2]/div/div[2]/div[1]/div[1]/div[2]/div/div/div[2]')
        url= 'http://%s%s' % (self.allowed_domains[0],sites.xpath('a/@href').extract()[0])
        #print "transcript url",url
        yield Request(url,callback=self.parse_transcript,meta={'item':item})
        #yield Request(url+'#',callback=self.parse_download)
        #print response.xpath('//script')
        #soup = BS(response.body)
        #script = soup.findAll('script')
        #print script
        for js in response.xpath('//script'):
            txt = js.xpath('.//text()').extract()
            #print "extract ",txt
            if len(txt):
                txt = txt[0]
            if 'q("talkPage.init",{"talks"' in txt:
                d = json.loads(txt[txt.find('{'):txt.rfind('}')+1])
                subtitleDownload = d['talks'][0]['subtitledDownloads']
                for k,v in subtitleDownload.items():
                    #print "lang",k,'--->',v
                    if k == 'zh-cn' or k == 'en':
                        pos = v['high'].rfind('/')+1
                        os.system('wget -c %s -O "%s/%s"' % (v['high'],self.sdir,v['high'][pos:]))

    def parse_transcript(self,response):
        item = response.meta['item']
        fname = "%s/%s/%s.txt" % (self.root_dir,item['speaker'][0],item['title'][0].splitlines()[1])
        #print "fname ",fname

        sel = Selector(response)
        #/html/body/div[1]/div[2]/div/div[2]/div[3]/div/div/div[2]/div[2]/div/p[1]
        #/html/body/div[1]/div[2]/div/div[2]/div[3]/div/div/div[2]/div[2]/div
        lines  = sel.xpath('//div[@class="talk-transcript__para"]')
        lines  = response.xpath('//p[@class="talk-transcript__para"]')
        #lines = sel.xpath('//div')
        
        #print "response",response.url
        #print "headers",response.headers
        #/html/body/div[1]/div[2]/div/div[2]/div[3]/div/div/div[2]/div[2]/div/p[1]
        #/html/body/div[1]/div[2]/div/div[2]/div[3]/div/div/div[2]/div[2]/div/p[2]
        #html.js.loggedout.js.flexbox.flexboxlegacy.canvas.canvastext.webgl.no-touch.geolocation.postmessage.no-websqldatabase.indexeddb.hashchange.history.draganddrop.websockets.rgba.hsla.multiplebgs.backgroundsize.borderimage.borderradius.boxshadow.textshadow.opacity.cssanimations.csscolumns.cssgradients.no-cssreflections.csstransforms.csstransforms3d.csstransitions.fontface.generatedcontent.video.audio.localstorage.sessionstorage.webworkers.applicationcache.svg.inlinesvg.smil.svgclippaths.cors body.talks-body div#shoji.shoji div.shoji__door div.page.shoji__washi div.main.talks-main div.talk-transcript.talk-article div.container div.talk-article__container div.row div.col-lg-7.col-lg-offset-1 div.talk-article__body.talk-transcript__body p.talk-transcript__para span.talk-transcript__para__text span#t-0.talk-transcript__fragment
        #print "lines",lines
        fd =  open(fname,'w')
        for line in lines:
            #/html/body/div[1]/div[2]/div/div[2]/div[3]/div/div/div[2]/div[2]/div/p[1]/data
            ptime = line.xpath('.//data/text()').extract() 
            #/html/body/div[1]/div[2]/div/div[2]/div[3]/div/div/div[2]/div[2]/div/p[1]/span/span
            #/html/body/div[1]/div[2]/div/div[2]/div[3]/div/div/div[2]/div[2]/div/p[3]/span/span[1]
            #/html/body/div[1]/div[2]/div/div[2]/div[3]/div/div/div[2]/div[2]/div/p[3]/span/span[2]
            frags = line.xpath('.//span/span[@class="talk-transcript__fragment"]')
            txt = []
            for f in frags:
                txt.append(''.join(f.xpath('.//text()').extract()[0].splitlines()))
            fd.write(ptime[0].splitlines()[1]+': '+''.join(txt)+'\n')
            fd.write('\n')


       #     print ptime[0].splitlines()[1],'--->',''.join( txt )
        fd.close()

