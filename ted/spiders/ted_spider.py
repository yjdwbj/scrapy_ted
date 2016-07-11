#coding: utf-8
import scrapy
import urllib2
from scrapy.spider import Spider
from scrapy.selector import Selector
from ted.items import TedItem
from scrapy.http import Request
from scrapy.selector import HtmlXPathSelector
import logging
#from BeautifulSoup import BeautifulSoup as BS
from datetime import timedelta
import subprocess
import re
import json
import os,sys


USERAGENT='Mozilla/5.0 (X11; Linux x86_64; rv:41.0) Gecko/20100101 Firefox/41.0'
CMDSTR = ["ffprobe","-show_format","-pretty","-loglevel","debug",""]
#CMDSTR = ["ffprobe","-show_format","-pretty","-loglevel","quiet",""]
#CONVERT = u'ffmpeg;-i;%s;-vn;-ac;2;-ar;44100;-ab;192k;-metadata;artist=%s;-metadata;title=%s;%s'
CONVERT = u'ffmpeg;-i;%s;-vn;-ac;%d;-ar;%d;-ab;%dk;-metadata;artist=%s;-metadata;title=%s;%s'
CHKFFMPEG = os.system('which ffmpeg')

class TedSpider(scrapy.Spider):
    name = "TED"
    allowed_domains = ["www.ted.com"]
    sdir = None
    root_dir = os.getcwd()+"/download"
    if not os.path.exists(root_dir):
        os.mkdir(root_dir)
    start_urls =[
            "http://www.ted.com/playlists/171/the_most_popular_talks_of_all",
            "http://www.ted.com/playlists/260/talks_to_watch_when_your_famil",
            "http://www.ted.com/playlists/309/talks_on_how_to_make_love_last",
            "http://www.ted.com/playlists/310/talks_on_artificial_intelligen",
            "http://www.ted.com/playlists/311/time_warp",
            "http://www.ted.com/playlists/312/weird_facts_about_the_human_bo",
            "https://www.ted.com/playlists/370/top_ted_talks_of_2016",
            "https://www.ted.com/playlists/216/talks_to_restore_your_faith_in_1"
            ]

    logfile = "%s/scrapy.log" % os.getcwd()
    logging.basicConfig(filename=logfile,level=logging.DEBUG,)



    def extract_mp3(self,response,mp4):
        """ 这里要用到FFMPEG工具"""
        print "extract mp3"
        item = response.meta['item']
        #rdir = "%s/%s" % (self.root_dir,item['speaker']) 
        CMDSTR[-1] = mp4
        p = subprocess.Popen(CMDSTR,stdout=subprocess.PIPE,stderr = subprocess.PIPE,shell=False)
        out,err = p.communicate()
        #print " ffprobe out ---------------------------------------------"
        #print out
        #print " ffprobe err ---------------------------------------------"
        #print err
        title = item['title'].strip().encode('utf-8')
        #item['title'] = title
        samples = 44100
        channel = 1
        rate = 60
        for x in out.splitlines():
            if 'TAG:title' in x.strip():
                title = x.split(':').pop().strip().encode('utf-8')
                #print "title",title

            if 'TAG:description' in x.strip():
                item['info'] = x.split(':').pop().strip()
                #print "description ",item['info']

        for x in err.splitlines():
            if 'Audio:' in x:
                # examples line    Stream #0:1(und): Audio: aac (LC) (mp4a / 0x6134706D), 44100 Hz, stereo, fltp, 75 kb/s (default)
                lst = x.strip().split(' ')
                #print " list is ",lst
                samples = int(lst[10])
                if lst[12] == 'stereo':
                    channel = 2
                else:
                    channel = 1

                rate = int(lst[14])


        #nname = "%s/%s.mp4" % (self.root_dir,title)
        #os.rename(mp4,nname)
        try:
            output = u"%s/%s.mp3" % (self.root_dir,title)
        except UnicodeDecodeError:
            print "UnicodeDecodeError:",title
            print "output format error"

        if os.path.exists(output)  and os.stat(output).st_size > 0:
            return

        try:
            ffmpegstr = CONVERT % (mp4,channel,samples,rate ,item['speaker'],title,output)
        except UnicodeDecodeError:
            print "err convert str "
            print nname
            print item['speaker'],title,output
            return

        
        p = subprocess.Popen(ffmpegstr.split(';'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=False)
        out,err = p.communicate()
        #print out
        #print "  convert ---------------------------------------- err"
        #print err
                

    def parse(self,response):
        #res.meta['item'] = item
        sel = Selector(response)
        #sites = sel.xpath('/html/body/div/div[2]/div/div[2]/div[3]/div/div[1]/ul/li')
        sites = sel.xpath('//li[@class="playlist-talks__talk"]')
    
        items =[]
        for site in sites:
            item = TedItem()
            item['speaker'] = site.xpath('div/div/div[1]/span/a/text()').extract()[0].strip().encode('utf-8')
            #sdir = "%s/%s" % (self.root_dir,item['speaker']) 
            #if not os.path.exists(sdir):
            #    os.mkdir(sdir)
            #/html/body/div/div[2]/div/div[2]/div[3]/div/div[1]/ul/li[1]/div/div/a/span/span[2]
            item['duration'] = site.xpath('div/div/a/span/span[2]/text()').extract()[0].strip()
            #/html/body/div/div[2]/div/div[2]/div[3]/div/div[1]/ul/li[1]/div/div/div[1]/h9/a
            item['title'] = site.xpath('div/div/div[1]/h9/a/text()').extract()[0].strip().encode('utf-8')
            #print "the title is ",item['title']
            item['url'] = site.xpath('div/div/div[1]/h9/a/@href').extract()[0].strip()
            #/html/body/div/div[2]/div/div[2]/div[3]/div/div[1]/ul/li[1]/div/div/div[2]/div[1]
            item['info'] = site.xpath('div/div/div[2]/div[1]/text()').extract()[0]
            #print item['url']
            yield  Request('http://%s%s' % (self.allowed_domains[0],item['url']),
                    callback=self.parse_speaker,meta={'item':item})
            items.append(item)
            
            #try:
            #    info = u'%s/%s.info' % (self.root_dir,item['title'])
            #except UnicodeDecodeError:
            #    print "parse error --------- title is",item['title']
            #    continue
            #with open(info,'w') as fd:
            #    fd.writelines(json.dumps(item.__dict__,indent=4,separators=(',',':')))

        #self.parse_newest_talks(response)
        #self.parse_newest_talks(response)
        yield  Request('http://www.ted.com',callback=self.parse_newest_talks)

    def parse_newest_talks(self,response):
        #print response
        #data = urllib2.urlopen("http://www.ted.com").read()
        #hxs = HtmlXPathSelector(text = data)
        sel = Selector(response)
        #for js in hxs.xpath('//script'):
        for js in sel.xpath('//script'):
            txt = js.xpath('.//text()').extract()
            if len(txt):
                txt = txt[0]
            #print "txt is",txt
            if 'q("newHome1"' in txt:
                #print txt
                dt = txt[txt.index('['):txt.rindex(']')+1]
                #dt = dt.replace("\'","'")
                d = json.loads(dt)
                """ 这里一定是list 吧　"""
                for o in d:
                    #print "+++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++++"
                    #print o['title']
                    #print o['items']
                    for x in o['items']:
                        item = TedItem()
                        item['speaker'] = x['speaker'].encode('utf-8')
                        item['duration'] = x['duration']
                        item['title'] = x['title'].strip().encode('utf-8')
                        item['url'] = x['url'].strip()
                        item['info'] = ""
                        #sdir = "%s/%s" % (self.root_dir,item['speaker']) 
                        yield Request('http://%s%s' % (self.allowed_domains[0],x['url']),
                                callback=self.parse_speaker,meta={'item':item},dont_filter=True,
                                errback=self.parse_error)
                        #try:
                        #    info = u'%s/%s.info' % (self.root_dir,item['title'])
                        #except UnicodeDecodeError:
                        #    print "newest talks error --- title is",item['title']
                        #    continue
                        #with open(info,'w') as fd:
                        #    fd.writelines(json.dumps(item.__dict__,indent=4,separators=(',',':')))



                
    def parse_error(self,response):
        print "parse EEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEEE"
        logging.debug(response)


    def parse_speaker(self,response):
        item = response.meta['item']
        #url = response.url.split('//')[1].split('/')
        sel = Selector(response)
        #sites = sel.xpath('/html/body/div[1]/div[2]/div/div[2]/div[1]/div[1]/div[2]/div/div/div[2]')
        try:
            site = sel.xpath('//div/a[@id="hero-transcript-link"]/@href').extract()[0]
        except IndexError:
            print "error xpath --- ",sel,
            print "error url", response.url
            return
        url= 'http://%s%s' % (self.allowed_domains[0],site)
        #yield Request(url,callback=self.parse_transcript,meta={'item':item})
        #print "transcript url",url
        #try:
        #    rdir = u"%s/%s" % (self.root_dir,item['speaker']) 
        #except:
        #    logging.debug("err some %s" % item['speaker'])
        #    print "error return"
        #    return
                    
        #print "output dir",rdir
        # 下载只用wget 顺序下载，多线程怕对务器产生大压力。

        for js in response.xpath('//script'):
            txt = js.xpath('.//text()').extract()
            if len(txt):
                txt = txt[0]

            if 'q("talkPage.init",{"talks"' in txt:
                d = json.loads(txt[txt.find('{'):txt.rfind('}')+1])
                subtitleDownload = d['talks'][0]['subtitledDownloads']
                if len(subtitleDownload) == 0:
                    subtitleDownload = d['talks'][0]['nativeDownloads']
                    if len(subtitleDownload) == 0:
                        """为什么会是空的"""
                        logging.debug("%s is empty" % subtitleDownload)
                        logging.debug(d['talks'])
                        continue
                # download audio 
                #print "------------------download ",subtitleDownload
                for k,v in subtitleDownload.items():
                    #print "lang",k,'--->',v
                    # 下载中英文两种语言的视频
                    #if k == 'zh-cn' or k == 'en':
                    if k == 'en':
                        try:
                            fp = v.get('high',None)
                            if not fp:
                                fp = v.get('low',None)
                                if not fp:
                                    continue
                            pos = fp.rfind('/')+1
                            #output = u"%s/%s" % (self.root_dir,fp[pos:].encode('utf-8'))
                            output = u"%s/%s.mp4" % (self.root_dir,item['title'])
                        except KeyError:
                            print "-----------------------occur error",v
                            sys.exit(0)

                        if os.path.exists(output)  and os.stat(output).st_size > 0:
                            continue
                        os.system('wget --wait=3 --read-timeout=5 -t 5 --user-agent="%s" -c %s -O "%s"' \
                                % (USERAGENT,fp.encode('utf-8'),output.encode('utf-8')))
                        if CHKFFMPEG == 0:
                            #if k == 'en':
                            """
                            这里如果用下载的mp3会出现与字幕不匹配的问题,因为下载的mp3前面插入十几秒的音频
                            """
                            #print "-----------------------handle lrc"
                            self.extract_mp3(response,output)
                            print "handler -------------------------------------- lrc",url
                            yield Request(url,callback=self.parse_transcript,meta={'item':item},dont_filter=True,
                                    errback=self.parse_error)
                            print "yield transcript ",url
                        else:
                            """ 没有安装FFMPEG只能下载 """
                            audioDownload = d['talks'][0]['audioDownload']
                            if audioDownload:
                                t = audioDownload.split('?')[0]
                                pos = t.rfind('/') + 1
                                #output = "%s/%s" % (rdir,t[pos:])
                                output = u"%s/%s.mp3" % (self.root_dir,item['title'].replace('\n',''))
                                try:
                                    pass
                                    os.system('wget  --wait=3 --read-timeout=5 -t 5 --user-agent="%s" -c %s -O "%s"' % (USERAGENT,audioDownload.encode('utf-8'),output.encode('utf-8')))
                                except UnicodeEncodeError:
                                    print "str is",audioDownload,output
                                    sys.exit(0)

        



    def parse_transcript(self,response):
        item = response.meta['item']
        print "response status code",response.status
        lang = response.url.split('=')[1]
        if lang == 'en':
            fname = u"%s/%s.lrc" % (self.root_dir,item['title'])
        else:
            fname = u"%s/%s-%s.lrc" % (self.root_dir,item['title'],lang)

        sel = Selector(response)
        lines  = response.xpath('//p[@class="talk-transcript__para"]')
        lbody = response.xpath('//div[@class="talk-transcript__body"]')
        ftime = lbody.xpath('./p//data[1]/text()').extract()
        #lines = sel.xpath('//div')
        #print "lines",lines
        with  open(fname,'w') as fd:
            #print "item['title']",item['title']
            s= '[ti:%s]\n' % ''.join(item['title'].splitlines())
            fd.write(s.encode('utf-8'))
            s='[ar:%s]\n' % ''.join(item['speaker'].splitlines())
            fd.write(s.encode('utf-8'))
            #fd.write(u'[al:www.ted.com]\n')
            fd.write(u'%s\n' % item['url'])
            fd.write(u'[offset:1000]\n')
            ftime = lines[0].xpath('.//data[1]/text()').extract();
            
            #print "start seconds is ",ftime
            start = timedelta(seconds = int(ftime[0].splitlines()[1].split(':')[1]))
           # print "start seconds is ",start
            
            for line in lines:
                #/html/body/div[1]/div[2]/div/div[2]/div[3]/div/div/div[2]/div[2]/div/p[1]/data
                #ptime = line.xpath('.//data/text()').extract()[0] 
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
                    p = str(start + dtime)[2:]
                    if len(p) == 5:
                        p = p + ".000"
                    else:
                        p = p[:-3]
                    txt = '[%s]%s' % (p,mf)
                    fd.write(txt.strip().encode('utf-8'))
                    fd.write(u'\n')
        url = response.url.replace('=en','=zh-cn')
        #print "zh_cn links,url",url
        yield Request(url,callback=self.parse_transcript,meta={'item':item},dont_filter=True)



