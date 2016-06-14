#coding: utf-8
import scrapy
from scrapy.spider import Spider
from scrapy.selector import Selector
from ted.items import TedItem
from scrapy.http import Request
#from BeautifulSoup import BeautifulSoup as BS
from datetime import timedelta
import subprocess
import re
import json
import os,sys

USERAGENT='Mozilla/5.0 (X11; Linux x86_64; rv:41.0) Gecko/20100101 Firefox/41.0'
CMDSTR = ["ffprobe","-show_format","-pretty","-loglevel","quiet",""]
CONVERT = 'ffmpeg;-i;%s;-ac;2;-ar;44100;-ab;192k;-metadata;artist=%s;-metadata;title=%s;%s'
CHKFFMPEG = os.system('which ffmpeg')

class TedSpider(scrapy.Spider):
    name = "TED"
    allowed_domains = ["ted.com"]
    sdir = None
    root_dir = os.getcwd()+"/ted_download"
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

    def extract_mp3(self,response,mp4):
        """ 这里要用到FFMPEG工具"""
        item = response.meta['item']
        rdir = "%s/%s" % (self.root_dir,item['speaker'][0]) 
        CMDSTR[-1] = mp4
        p = subprocess.Popen(CMDSTR,stdout=subprocess.PIPE,stderr = subprocess.PIPE,shell=False)
        out,err = p.communicate()
        #print " ffprobe out ---------------------------------------------"
        #print out
        #print " ffprobe err ---------------------------------------------"
        #print err
        title = ''.join(item['title'][0].splitlines())
        item['title'][0] = title
        for x in out.splitlines():
            if 'title' in x.strip():
                title = x.split(':').pop().strip()
                break


        output = "%s/%s.mp3" % (rdir,title)
        if os.path.exists(output)  and os.stat(output).st_size > 0:
            return

        ffmpegstr = CONVERT % (mp4 ,''.join(item['speaker'][0].splitlines()),title,output)
        #print ffmpegstr.split(";")
        p = subprocess.Popen(ffmpegstr.split(';'),stdout=subprocess.PIPE,stderr=subprocess.PIPE,shell=False)
        #p = subprocess.Popen(ffmpegstr.split(';'))
        #out,err = p.communicate()
        #print " ffmpeg out ---------------------------------------------"
        #print out
        #print " ffmpeg err ---------------------------------------------"
        #print err
                

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
        #print "site is",site
        url= 'http://%s%s' % (self.allowed_domains[0],site)
        #yield Request(url,callback=self.parse_transcript,meta={'item':item})
        #print "transcript url",url
        rdir = "%s/%s" % (self.root_dir,item['speaker'][0]) 
        #print "output dir",rdir
        # 下载只用wget 顺序下载，多线程怕对务器产生大压力。

        for js in response.xpath('//script'):
            txt = js.xpath('.//text()').extract()
            if len(txt):
                txt = txt[0]

            if 'q("talkPage.init",{"talks"' in txt:
                d = json.loads(txt[txt.find('{'):txt.rfind('}')+1])
                subtitleDownload = d['talks'][0]['subtitledDownloads']
                # download audio 
                #print "------------------download ",subtitleDownload
                for k,v in subtitleDownload.items():
                    #print "lang",k,'--->',v
                    # 下载中英文两种语言的视频
                    if k == 'zh-cn' or k == 'en':
                        try:
                            fp = v.get('high','low')
                            pos = fp.rfind('/')+1
                            output = "%s/%s" % (rdir,fp[pos:])
                        except KeyError:
                            print "-----------------------occur error",v
                            sys.exit(0)
                        os.system('wget --wait=3 --read-timeout=5 -t 5 --user-agent="%s" -c %s -O "%s"' % (USERAGENT,fp.encode('utf-8'),output.encode('utf-8')))
                        if CHKFFMPEG == 0:
                            if k == 'en':
                                """
                                这里如果用下载的mp3会出现与字幕不匹配的问题,因为下载的mp3前面插入十几秒的音频
                                """
                                #print "-----------------------handle lrc"
                                print "extract mp3"
                                self.extract_mp3(response,output)
                                print "write lyrics file"
                                yield Request(url,callback=self.parse_transcript,meta={'item':item})
                        else:
                            """ 没有安装FFMPEG只能下载 """
                            audioDownload = d['talks'][0]['audioDownload']
                            if audioDownload:
                                t = audioDownload.split('?')[0]
                                pos = t.rfind('/') + 1
                                #output = "%s/%s" % (rdir,t[pos:])
                                output = "%s/%s.mp3" % (rdir,item['title'][0].replace('\n',''))
                                try:
                                    pass
                                    os.system('wget  --wait=3 --read-timeout=5 -t 5 --user-agent="%s" -c %s -O "%s"' % (USERAGENT,audioDownload.encode('utf-8'),output.encode('utf-8')))
                                except UnicodeEncodeError:
                                    print "str is",audioDownload,output
                                    sys.exit(0)

        



    def parse_transcript(self,response):
        item = response.meta['item']
        lang = response.url.split('=')[1]
        if lang == 'en':
            fname = "%s/%s/%s.lrc" % (self.root_dir,item['speaker'][0],
                    item['title'][0])
        else:
            fname = "%s/%s/%s-%s.lrc" % (self.root_dir,item['speaker'][0],
                    item['title'][0],lang)

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
                    p = str(start + dtime)[2:]
                    if len(p) == 5:
                        p = p + ".000"
                    else:
                        p = p[:-3]
                    txt = '[%s]%s' % (p,mf)
                    fd.write(txt.strip().encode('utf-8'))
                    fd.write('\n')
        url = response.url.replace('=en','=zh-cn')
        #print "zh_cn links,url",url
        yield Request(url,callback=self.parse_transcript,meta={'item':item})



