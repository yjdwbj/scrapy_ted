#coding: utf-8
import scrapy
from scrapy.spider import Spider
from scrapy.selector import Selector
from ted.items import TedItem
from scrapy.http import Request
from BeautifulSoup import BeautifulSoup as BS
from datetime import timedelta
import re
import json
import os,sys

USERAGENT='Mozilla/5.0 (X11; Linux x86_64; rv:41.0) Gecko/20100101 Firefox/41.0'

class TedSpider(scrapy.Spider):
    name = "TED"
    allowed_domains = ["ted.com"]
    sdir = None
    root_dir = os.getcwd()+"/ted_download"
    if not os.path.exists(root_dir):
        os.mkdir(root_dir)
    start_urls =[
            "http://www.ted.com/playlists/171/the_most_popular_talks_of_all",
           # "http://www.ted.com/playlists/260/talks_to_watch_when_your_famil",
           # "http://www.ted.com/playlists/309/talks_on_how_to_make_love_last",
           # "http://www.ted.com/playlists/310/talks_on_artificial_intelligen",
           # "http://www.ted.com/playlists/311/time_warp",
           # "http://www.ted.com/playlists/312/weird_facts_about_the_human_bo"
            ]

    def parse(self,response):
        sel = Selector(response)
        #sites = sel.xpath('/html/body/div/div[2]/div/div[2]/div[3]/div/div[1]/ul/li')
        sites = sel.xpath('//li[@class="playlist-talks__talk"]')
        #print "sites",sites,len(sites)
        items =[]
        for site in sites:
            item = TedItem()
            item['speaker'] = site.xpath('div/div/div[1]/span/a/text()').extract()
            sdir = "%s/%s" % (self.root_dir,item['speaker'][0]) 
            if not os.path.exists(sdir):
                os.mkdir(sdir)
            #/html/body/div/div[2]/div/div[2]/div[3]/div/div[1]/ul/li[1]/div/div/a/span/span[2]
            item['duration'] = site.xpath('div/div/a/span/span[2]/text()').extract()
            #/html/body/div/div[2]/div/div[2]/div[3]/div/div[1]/ul/li[1]/div/div/div[1]/h9/a
            item['title'] = site.xpath('div/div/div[1]/h9/a/text()').extract()
            item['url'] = site.xpath('div/div/div[1]/h9/a/@href').extract()
            #/html/body/div/div[2]/div/div[2]/div[3]/div/div[1]/ul/li[1]/div/div/div[2]/div[1]
            item['info'] = site.xpath('div/div/div[2]/div[1]/text()').extract()
            #print item['url']
            yield  Request('http://%s%s' % (self.allowed_domains[0],item['url'][0]),
                    callback=self.parse_speaker,meta={'item':item})
            items.append(item)
            
            with open('%s/talk.info' % sdir,'w') as fd:
                fd.writelines(json.dumps(item.__dict__,indent=4,separators=(',',':')))

    def parse_speaker(self,response):
        item = response.meta['item']
        #url = response.url.split('//')[1].split('/')
        sel = Selector(response)
        #sites = sel.xpath('/html/body/div[1]/div[2]/div/div[2]/div[1]/div[1]/div[2]/div/div/div[2]')
        site = sel.xpath('//div/a[@id="hero-transcript-link"]/@href').extract()[0]
        #print "site is",site.extract()
        url= 'http://%s%s' % (self.allowed_domains[0],site)
        #print "transcript url",url
        yield Request(url,callback=self.parse_transcript,meta={'item':item})
        rdir = "%s/%s" % (self.root_dir,item['speaker'][0]) 
        #print "output dir",rdir
        # 下载只用wget 顺序下载，多线程怕对务器产生大压力。
        return

        for js in response.xpath('//script'):
            txt = js.xpath('.//text()').extract()
            #print "extract ",txt
            if len(txt):
                txt = txt[0]
            if 'q("talkPage.init",{"talks"' in txt:
                d = json.loads(txt[txt.find('{'):txt.rfind('}')+1])
                subtitleDownload = d['talks'][0]['subtitledDownloads']
                # download audio 
                audioDownload = d['talks'][0]['audioDownload']
                if audioDownload:
                    t = audioDownload.split('?')[0]
                    pos = t.rfind('/') + 1
                    #output = "%s/%s" % (rdir,t[pos:])
                    output = "%s/%s.mp3" % (rdir,item['title'][0].replace('\n',''))
                    try:
                        pass
                        os.system('wget  --wait=3 --read-timeout=5 -t 5 --user-agent="%s" -c %s -O "%s"' % (USERAGENT,audioDownload,output))
                    except UnicodeEncodeError:
                        print "str is",audioDownload,output
                        sys.exit(0)

                for k,v in subtitleDownload.items():
                    #print "lang",k,'--->',v
                    # 下载中英文两种语言的视频
                    if k == 'zh-cn' or k == 'en':
                        try:
                            pos = v['high'].rfind('/')+1
                            output = "%s/%s" % (rdir,v['high'][pos:])
                        except KeyError:
                            print "occur error",v
                            sys.exit(0)
                        #os.system('wget --wait=3 --read-timeout=5 -t 5 --user-agent="%s" -c %s -O "%s"' % (USERAGENT,v['high'],output))
                        #break

    def parse_transcript(self,response):
        item = response.meta['item']
        lang = response.url.split('=')[1]
        if lang == 'en':
            fname = "%s/%s/%s.lrc" % (self.root_dir,item['speaker'][0],
                    item['title'][0].splitlines()[1])
        else:
            fname = "%s/%s/%s-%s.lrc" % (self.root_dir,item['speaker'][0],
                    item['title'][0].splitlines()[1],lang)

        sel = Selector(response)
        lines  = response.xpath('//p[@class="talk-transcript__para"]')
        lbody = response.xpath('//div[@class="talk-transcript__body"]')
        ftime = lbody.xpath('./p//data[1]/text()').extract()
        #lines = sel.xpath('//div')
        #print "lines",lines
        with  open(fname,'w') as fd:
            #print "item['title']",item['title']
            s= '[ti:%s]\n' % ''.join(item['title'][0].splitlines())
            fd.write(s.encode('utf-8'))
            s='[ar:%s]\n' % ''.join(item['speaker'][0].splitlines())
            fd.write(s.encode('utf-8'))
            fd.write(u'[al:www.ted.com]\n')
            fd.write(u'[offset:1000]\n')
            ftime = lines[0].xpath('.//data[1]/text()').extract();
            
            #print "start seconds is ",ftime
            start = timedelta(seconds = int(ftime[0].splitlines()[1].split(':')[1]))
           # print "start seconds is ",start
            
            for line in lines:
                #/html/body/div[1]/div[2]/div/div[2]/div[3]/div/div/div[2]/div[2]/div/p[1]/data
                ptime = line.xpath('.//data/text()').extract() 
                #/html/body/div[1]/div[2]/div/div[2]/div[3]/div/div/div[2]/div[2]/div/p[1]/span/span
                #/html/body/div[1]/div[2]/div/div[2]/div[3]/div/div/div[2]/div[2]/div/p[3]/span/span[1]
                #/html/body/div[1]/div[2]/div/div[2]/div[3]/div/div/div[2]/div[2]/div/p[3]/span/span[2]
                frags = line.xpath('.//span/span[@class="talk-transcript__fragment"]')
                txt = []
                for f in frags:
                    ms = f.xpath('./@data-time').extract()
                    #print "data-time is -------------------------",ms
                    dtime = timedelta(milliseconds = int(ms[0]))
                    mf = ' '.join(f.xpath('./text()').extract()[0].splitlines())
                    txt = '[%s]%s' % (str(start + dtime),mf)
                    fd.write(txt.strip().encode('utf-8'))
                    fd.write('\n')
        url = response.url.replace('=en','=zh-cn')
        #print "zh_cn links,url",url
        yield Request(url,callback=self.parse_transcript,meta={'item':item})



