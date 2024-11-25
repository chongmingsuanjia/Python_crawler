import aiohttp
import asyncio
import os
import requests
import json
import subprocess
import re
import time
from lxml import html
import sys
#消除HTTPS安全警告
"""这个警告是urllib3库为了提醒您在进行不安全的HTTPS请求时存在潜在的风险而发出的"""
#为了消除这个警告,引入以下库中函数
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # url = 'https://www.99meiju.org/vodplay/6331-4-1.html'
async def async_download_ts(session, url, name, retry=5, timeout=30):
    for _ in range(retry):
        try:
            async with session.get(url, timeout=timeout) as resp:
                data = await resp.read()
                with open(name, 'wb') as f:
                    f.write(data)
                print(f"文件{name}下载完成")
                break
        except aiohttp.ClientPayloadError as e:
            print(f"下载文件{name}时发生错误: {e}")
            print("重试下载...")
            time.sleep(0.3)
        except aiohttp.ClientConnectionError as e:
            print(f"连接超时: {e}")
            print("重试下载...")
            time.sleep(0.3) 
        except asyncio.TimeoutError as e:
            print(f"连接超时: {e}")
            print("重试下载...")
            time.sleep(0.3) 
    else:
        print(f"文件{name}下载失败")

async def main():
    # 代码省略
    print("此程序只用于www.99meiju.org网站视频的爬取")
    url=input("请输入你要查找的影片所在的url:")

    # episode=url.rsplit('.',1)[0].rsplit('-',1)[1]
    root_url="https://"+url.split('://')[1].split('/')[0]

    async with aiohttp.ClientSession() as session:
        print(f"正在请求网站{url}...")
        resp = await session.get(url,ssl=False)

        resp_text = await resp.text()
        tree = html.fromstring(resp_text)

        # 执行XPath查询以获取指定元素的href属性
        href = tree.xpath('//*[@id="con_playlist_2"]/li/a/@href')
        title=tree.xpath('//*[@id="zanpian-score"]/h2/text()')[0]
        # 输出href属性的值
        if not href:
            print("未找到href属性")
        #视频主页信息解析完成
        #下面用户进行选择:下载第{i}集(按 "1")/下载全部(按 "2")
        while(1):
            i=input('下载第__集(输入你想下载的集数:)/下载全部(按 "0"):')
            if not i.isdigit():
                print("请输入整数!")
            elif int(i)<0 or int(i)>len(href):
                print("输入的数字超出范围!,请重试.")
            else:
                break
        episodes_url=[]
        if not int(i)==0:
            episodes_url.append(root_url+href[int(i)-1])
        else:
            episodes_url=href
        for episode_url in episodes_url:
            #在集的列表里循环请求每集的url
            print(f"正在请求{episode_url}...")
            resp = requests.get(episode_url,verify=False)
            #解析这集网页的html
            resp_text=resp.text
            url_dic_search = re.compile(r'<script type="text/javascript">var player_aaaa=(?P<dic>.*?)</script>', re.S)
            url_dic = url_dic_search.search(resp_text).group('dic')
            url_json = json.loads(url_dic)
            index_url = url_json['url']
            #请求index.m3u8
            index_rep = requests.get(index_url, verify=False)
            end_fix = index_rep.text.split('\n')[2]
            #将后缀中的
            if '_'in end_fix:
                end_fix=end_fix.replace('_', '/')
            front_fix = index_url.rsplit('/', 1)[0] + '/'
            mixed_url = front_fix + end_fix

            mixed_resp = requests.get(mixed_url)
            mixed_content = mixed_resp.text.strip()
            # 解析URL等操作
            
            ts_url_list = []
            ts_list = mixed_content.split('\n')
            tasks = []
            filesname = []

            for  li in ts_list:
                if not li.startswith('#'):
                    ts_url = mixed_url.rsplit('/', 1)[0] + '/' + li
                    ts_url_list.append(ts_url)

                    filename =ts_url.rsplit('/',1)[1]

                    if not os.path.exists(filename):
                        tasks.append(async_download_ts(session, ts_url, filename))
                    else:
                        print(f"文件{filename}已存在，跳过下载")
                    filesname.append(filename)

            await asyncio.gather(*tasks)

            output_file = f"{title}.mp4"
            ffmpeg_command = ['ffmpeg', '-i', 'concat:' + '|'.join(filesname), '-c', 'copy', output_file]
            subprocess.run(ffmpeg_command)

            for ts_file in filesname:
                os.remove(ts_file)

if __name__ == "__main__":
    
    start_time=time.time()
    asyncio.run(main())
    end_time=time.time()
    print("已全部下载完成!")
    print(f"总共用时:{end_time-start_time}s")
    
