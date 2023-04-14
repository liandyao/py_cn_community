# -*- coding: utf-8 -*
'''

湖南长沙社区
数据来源 http://www.cncn.org.cn/map/areas.php?pid=18&cid=284&sid=2223
pid表示省份id 例如18 表示湖南
cid表示城市id 例如284 表示长沙
sid表示区县id 例如2223 表示天心区

通过分析网页发现是ajax请求得到数据
http://cms.cncn.org.cn/api/map_province_index.php?pid=省份id
http://cms.cncn.org.cn/api/map_city_index.php?cid=城市id
http://cms.cncn.org.cn/api/map_district_index.php?limit=500&sid=区县id


'''
import re
import sqlite3

from lxml import html
import json
import time

import requests

import pandas as pd

headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.87 Safari/537.36 SE 2.X MetaSr 1.0',
    'Referer': 'http://www.cncn.org.cn/map/areas.php?cid=284&sid=2222'
}


conn = sqlite3.connect('my_community_db.db', timeout=10, check_same_thread=False)

# 初始化数据库
def initDb():
    create_tb_cmd = '''
                CREATE TABLE IF NOT EXISTS tb_community_info
                (
                id integer primary key autoincrement, --'主键'
                provinceId varchar(64) ,  -- '省份直辖市id'
                provinceName varchar(64), --'省份直辖市'
                cityId varchar(64), --'城市id'
                cityName varchar(64), --'城市'
                districtId varchar(64), --'区县id'
                districtName varchar(64), --'区县' 
                communityId varchar(64), --'社区id'
                communityName varchar(64), --'社区' 
                communityWebUrl varchar(64), --'社区网站' 
                create_time TIMESTAMP default (datetime('now', 'localtime'))  -- '加入时间' 
                ); -- '社区信息表'
                '''
    c = conn.execute(create_tb_cmd)
    print('create_tb_cmd sql is: %s', c.description)
    # 创建唯一索引
    create_index = 'CREATE UNIQUE  INDEX IF NOT EXISTS communityId_UNIQUE on tb_community_info (communityId);'
    c = conn.execute(create_index)
    print('create_tb_index_cmd sql is: %s', c.description)



# 将数据保存到sqlite数据库
def saveSqliteDb(it):
    try:
        if it:
            insert_sql = '''
            INSERT INTO tb_community_info (provinceId,provinceName,cityId,cityName,districtId,
             districtName,communityId,communityName,communityWebUrl )
                VALUES (?,?,?,?,?,?,?,?,?) ;
            '''
            conn.execute(insert_sql, (
            it['provinceId'], it['provinceName'], it['cityId'], it['cityName'], it['districtId'],
            it['districtName'], it['communityId'], it['communityName'], it['communityWebUrl']))
            conn.commit()
            print('insert sql is: %s', insert_sql)
            return True
    except sqlite3.IntegrityError as e:
        print('sqlite3主键重复!')
        return False

# 主方法
def main():
    # 初始化数据库
    initDb()
    # 网站经常挂,不能一次性读取所有的省份 --- 悠着点
    provinces = getProvince()
    # 三层循环获取数据 所有的省份
    for pid in provinces:
        cites = getCityByPid(pid)  # 得到城市列表
        for cid in cites:
            districts = getDistrictByCityId(cid['cityId'])  # 得到区县列表
            for did in districts:
                communites = getCommunityByDistrictId(did['districtId'])  # 得到社区列表
                for com in communites:
                    item = {
                        "provinceId": cid["provinceId"],
                        "provinceName": cid["provinceName"],
                        "cityId": cid["cityId"],
                        "cityName": cid["cityName"],
                        "districtId": did["districtId"],
                        "districtName": did["districtName"],
                        "communityId": com["communityId"],
                        "communityName": com["communityName"],
                        "communityWebUrl": com["communityWebUrl"]
                    }
                    # 保存到数据库
                    saveSqliteDb(item)
                # 稍微间隔100毫秒,防止速度过快
                time.sleep(0.5)

    # writeExcel(datas)


# 导出到excel
def writeExcel(datas):
    # 封装DataFrame
    columns = ['省(直辖市)id', '省(直辖市)', '城市id', '城市', '区县id', '区县', '社区id', '社区名称', '社区网址']
    myDataFrame = pd.DataFrame.from_dict(data=datas)
    writer = pd.ExcelWriter('./全国社区信息导出.xlsx')  # 初始化一个writer
    myDataFrame.to_excel(writer)  # table输出为excel, 传入writer
    writer._save()  # 保存


'''
得到所有的省份id,需要使用html解析工具
'''
def getProvince():
    provinces = []
    url = 'http://cncn.org.cn/'
    res = requests.get(url, headers=headers)
    indexHtml = res.text
    detailHtml = html.etree.HTML(indexHtml)
    # /html/body/div[6]/div/div[2]/div/div
    lis = detailHtml.xpath('//div[@class="maps"]/div/ul/li')
    for li in lis:
        ahref = li.xpath('./a/@href')[0]
        # 提取字符串中的数字
        number = re.findall("\d+", ahref)[0]
        print(number)
        provinces.append(number)
    return provinces

'''
 根据省份得到城市
'''


def getCityByPid(pid):
    # 拼接网址,分析网页之后得到的ajax地址
    url = f'http://cms.cncn.org.cn/api/map_province_index.php?pid={pid}'
    # 开始获取网站数据
    res = requests.get(url=url, headers=headers, timeout=10)
    # 将响应的文本转换为json
    cityJson = res.json()
    print(cityJson)
    # 开始取出响应的数据,转换为json
    if cityJson['error_code'] == 0:
        province = cityJson['map_list'][0]
        print(f'{province["province_id"]}-{province["province_name"]}')
        for k in province['province_items']:
            city = {
                "provinceId": province["province_id"],
                "provinceName": province["province_name"],
                "cityId": k,
                "cityName": province['province_items'][k]['city_name']
            }
            yield city


# 根据城市得到区县
def getDistrictByCityId(cid):
    # 拼接网址,分析网页之后得到的ajax地址
    url = f'http://cms.cncn.org.cn/api/map_city_index.php?cid={cid}'
    # 开始获取网站数据
    res = requests.get(url=url, headers=headers, timeout=10)
    # 将响应的文本转换为json
    jsonStr = res.json()
    print(jsonStr)
    # 区县数组
    # 开始取出响应的数据,转换为json
    if jsonStr['error_code'] == 0:
        map_list = jsonStr['map_list'][0]
        print(f'{map_list["city_id"]}-{map_list["city_name"]}')
        for k in map_list['city_items']:
            item = {
                "districtId": k,  # 区县id
                "districtName": map_list['city_items'][k]['district_name']  # 区县名称
            }
            yield item


# 根据区县id得到所有的社区
def getCommunityByDistrictId(did):
    # 拼接网址,分析网页之后得到的ajax地址
    url = f'http://cms.cncn.org.cn/api/map_district_index.php?limit=500&sid={did}'
    # 开始获取网站数据
    res = requests.get(url=url, headers=headers, timeout=10)
    # 将响应的文本转换为json
    jsonStr = res.json()
    print(jsonStr)
    # 社区数组
    # 开始取出响应的数据,转换为json
    if jsonStr['error_code'] == 0:
        map_list = jsonStr['map_list'][0]
        print(f'{map_list["district_id"]}-{map_list["district_name"]}')
        # 这里的map_list['district_items']变成了数组格式,有些区县没有社区,就不要取了
        if map_list.__contains__('district_items'):
            for it in map_list['district_items']:
                print(it['community_name'])
                item = {
                    "communityId": it['community_id'],  # 社区id
                    "communityName": it['community_name'],  # 社区名称
                    "communityWebUrl": it['community_weburl']  # 社区网站
                }
                yield item


# unicode编码转为中文
# def getCnZh(str):
#     cn_zh = str.encode('utf-8').decode('unicode_escape')
#     return cn_zh


if __name__ == '__main__':
    main()
    # getProvince()
    # getCityByPid(18)
    # item = {
    #     "provinceId": 1,
    #     "provinceName": '湖南省',
    #     "cityId": 2,
    #     "cityName": '长沙市',
    #     "districtId": 2222,
    #     "districtName": '芙蓉区',
    #     "communityId": '22222',
    #     "communityName": '文艺新村社区',
    #     "communityWebUrl": 'http://hn.cncn.org.cn/changsha/wenyixincun/intro.html'
    # }
    # datas=[]
    # datas.append(item)
    # writeExcel(datas)
