"""
山东城投公司名单（2023-2025年数据）
覆盖山东省16个地级市 + 主要国家级开发区
数据来源：向钱看188、知乎、大公国际研报
"""

def get_shandong_companies():
    """
    返回山东城投公司列表（按债券余额优先级排序）
    返回字段：name(公司名), city(城市/开发区), priority(优先级1=最高)
    """
    return [
        # ===== 青岛（67家，城投债余额4,902亿，山东省第一）=====
        {"name": "青岛城市建设投资(集团)有限责任公司", "city": "青岛", "priority": 1},
        {"name": "青岛国信发展(集团)有限责任公司", "city": "青岛", "priority": 1},
        {"name": "青岛地铁集团有限公司", "city": "青岛", "priority": 1},
        {"name": "青岛海发国有资本投资运营集团有限公司", "city": "青岛", "priority": 1},
        {"name": "青岛华通国有资本投资运营集团有限公司", "city": "青岛", "priority": 1},
        {"name": "青岛海洋科技投资发展集团有限公司", "city": "青岛", "priority": 2},
        {"name": "青岛水务集团有限公司", "city": "青岛", "priority": 2},
        {"name": "青岛旅游集团有限公司", "city": "青岛", "priority": 2},
        {"name": "青岛城市发展集团有限公司", "city": "青岛", "priority": 2},
        {"name": "中德联合集团有限公司", "city": "青岛", "priority": 2},
        {"name": "青岛西海岸新区海洋控股集团有限公司", "city": "青岛西海岸新区", "priority": 1},
        {"name": "青岛西海岸新区融合控股集团有限公司", "city": "青岛西海岸新区", "priority": 1},
        {"name": "城发投资集团有限公司", "city": "青岛西海岸新区", "priority": 2},
        {"name": "青岛黄岛发展(集团)有限公司", "city": "青岛西海岸新区", "priority": 2},
        {"name": "青岛军民融合发展集团有限公司", "city": "青岛西海岸新区", "priority": 2},
        {"name": "青岛海洋投资集团有限公司", "city": "青岛西海岸新区", "priority": 2},
        {"name": "青岛经济技术开发区投资控股集团有限公司", "city": "青岛西海岸新区", "priority": 2},
        {"name": "青岛西海岸旅游投资集团有限公司", "city": "青岛西海岸新区", "priority": 3},
        {"name": "青岛开发区投资建设集团有限公司", "city": "青岛西海岸新区", "priority": 3},
        {"name": "青岛西海岸公用事业集团有限公司", "city": "青岛西海岸新区", "priority": 3},
        {"name": "青岛董家口发展集团有限公司", "city": "青岛西海岸新区", "priority": 3},
        {"name": "青科控股集团有限公司", "city": "青岛西海岸新区", "priority": 3},

        # ===== 济南（30家，城投债余额2,249亿，排第二）=====
        {"name": "济南城市投资集团有限公司", "city": "济南", "priority": 1},
        {"name": "济南城市建设集团有限公司", "city": "济南", "priority": 1},
        {"name": "济南轨道交通集团有限公司", "city": "济南", "priority": 1},
        {"name": "济南西城投资开发集团有限公司", "city": "济南", "priority": 2},
        {"name": "齐鲁财金(山东)经济发展有限公司", "city": "济南", "priority": 2},
        {"name": "济南能源集团有限公司", "city": "济南", "priority": 2},
        {"name": "莱芜城市发展集团有限公司", "city": "济南", "priority": 3},
        {"name": "济南高新控股集团有限公司", "city": "济南高新区", "priority": 1},

        # ===== 潍坊（56家，城投债余额1,167亿，排第三）=====
        {"name": "潍坊市城市建设发展投资集团有限公司", "city": "潍坊", "priority": 1},
        {"name": "潍坊滨海投资发展有限公司", "city": "潍坊", "priority": 1},
        {"name": "潍坊滨城投资开发有限公司", "city": "潍坊", "priority": 2},
        {"name": "潍坊市投资集团有限公司", "city": "潍坊", "priority": 2},
        {"name": "潍坊水务投资集团有限公司", "city": "潍坊", "priority": 2},
        {"name": "潍坊经济区城市建设投资发展集团有限公司", "city": "潍坊", "priority": 3},
        {"name": "潍坊滨海旅游集团有限公司", "city": "潍坊", "priority": 3},
        {"name": "潍坊东兴建设发展有限公司", "city": "潍坊", "priority": 3},
        {"name": "潍坊三农创新发展集团有限公司", "city": "潍坊", "priority": 3},
        {"name": "潍坊凤凰山国有资本投资运营管理有限公司", "city": "潍坊", "priority": 3},
        {"name": "山东高创建设投资集团有限公司", "city": "潍坊", "priority": 2},
        {"name": "潍坊高新区国有资本运营管理有限公司", "city": "潍坊", "priority": 3},
        {"name": "潍坊滨城建设集团有限公司", "city": "潍坊", "priority": 3},

        # ===== 烟台 =====
        {"name": "烟台蓝天投资开发集团有限公司", "city": "烟台", "priority": 1},
        {"name": "烟台市城市建设投资有限责任公司", "city": "烟台", "priority": 1},
        {"name": "烟台市财金发展投资集团有限公司", "city": "烟台", "priority": 2},
        {"name": "烟台业达城市发展集团有限公司", "city": "烟台经开区", "priority": 2},
        {"name": "烟台业达经济发展集团有限公司", "city": "烟台经开区", "priority": 3},

        # ===== 淄博 =====
        {"name": "淄博市城市资产运营集团有限公司", "city": "淄博", "priority": 1},
        {"name": "淄博高新国有资本投资有限公司", "city": "淄博", "priority": 2},
        {"name": "淄博高新城市投资运营集团有限公司", "city": "淄博", "priority": 2},
        {"name": "淄博文昌湖公有资产经营有限公司", "city": "淄博", "priority": 3},

        # ===== 临沂 =====
        {"name": "临沂城市建设投资集团有限公司", "city": "临沂", "priority": 1},
        {"name": "临沂城市发展集团有限公司", "city": "临沂", "priority": 1},
        {"name": "临沂投资发展集团有限公司", "city": "临沂", "priority": 2},
        {"name": "临沂振东建设投资有限公司", "city": "临沂", "priority": 3},
        {"name": "临沂商城控股集团有限公司", "city": "临沂", "priority": 3},
        {"name": "临沂经济开发区城市建设投资有限公司", "city": "临沂经开区", "priority": 3},

        # ===== 威海 =====
        {"name": "威海城市投资集团有限公司", "city": "威海", "priority": 1},
        {"name": "威海产业投资集团有限公司", "city": "威海", "priority": 2},
        {"name": "威海高新城市建设发展有限公司", "city": "威海高新区", "priority": 2},
        {"name": "威海经济技术开发区国有资产经营集团有限公司", "city": "威海经开区", "priority": 3},
        {"name": "威海市临港国有资产经营管理有限公司", "city": "威海临港区", "priority": 3},

        # ===== 济宁 =====
        {"name": "济宁城投控股集团有限公司", "city": "济宁", "priority": 1},
        {"name": "山东公用控股有限公司", "city": "济宁", "priority": 2},
        {"name": "济宁市新城发展投资有限责任公司", "city": "济宁", "priority": 3},
        {"name": "济宁高新城建投资有限公司", "city": "济宁高新区", "priority": 3},
        {"name": "济宁高新控股集团有限公司", "city": "济宁高新区", "priority": 3},

        # ===== 日照 =====
        {"name": "日照市城市建设投资集团有限公司", "city": "日照", "priority": 1},
        {"name": "日照城投集团有限公司", "city": "日照", "priority": 2},
        {"name": "日照交通能源发展集团有限公司", "city": "日照", "priority": 2},
        {"name": "日照水务集团有限公司", "city": "日照", "priority": 3},
        {"name": "日照市土地发展集团有限公司", "city": "日照", "priority": 3},
        {"name": "山东海洋文化旅游发展集团有限公司", "city": "日照", "priority": 3},
        {"name": "日照经济技术开发区城市发展投资集团有限公司", "city": "日照经开区", "priority": 3},

        # ===== 泰安 =====
        {"name": "泰安市泰山投资有限公司", "city": "泰安", "priority": 1},
        {"name": "泰安市泰山财金投资集团有限公司", "city": "泰安", "priority": 2},
        {"name": "泰安市城市发展投资有限公司", "city": "泰安", "priority": 2},
        {"name": "泰安泰山城乡建设发展有限公司", "city": "泰安", "priority": 3},
        {"name": "泰安泰山控股有限公司", "city": "泰安", "priority": 3},

        # ===== 聊城 =====
        {"name": "聊城市财信投资控股集团有限公司", "city": "聊城", "priority": 1},
        {"name": "聊城市兴业控股集团有限公司", "city": "聊城经开区", "priority": 2},

        # ===== 德州 =====
        {"name": "德州财金投资控股集团有限公司", "city": "德州", "priority": 1},
        {"name": "德州德达城市建设投资运营有限公司", "city": "德州", "priority": 2},
        {"name": "德州市城市建设投资发展集团有限公司", "city": "德州", "priority": 3},
        {"name": "宁津惠宁投资控股集团有限公司", "city": "德州", "priority": 3},

        # ===== 滨州 =====
        {"name": "滨州城建投资集团有限公司", "city": "滨州", "priority": 1},
        {"name": "滨州沾化区宏达财金投资集团有限公司", "city": "滨州", "priority": 3},
        {"name": "滨州市惠众置业有限公司", "city": "滨州", "priority": 3},
        {"name": "滨州市中海创业投资集团有限公司", "city": "滨州经开区", "priority": 3},

        # ===== 东营 =====
        {"name": "东营市财金投资集团有限公司", "city": "东营", "priority": 1},
        {"name": "东营市城市资产经营有限公司", "city": "东营", "priority": 2},

        # ===== 枣庄 =====
        {"name": "枣庄市基础设施投资发展集团有限公司", "city": "枣庄", "priority": 1},
        {"name": "鲁南(枣庄)经济开发投资有限公司", "city": "枣庄", "priority": 3},
        {"name": "枣庄高新投资集团有限公司", "city": "枣庄", "priority": 3},

        # ===== 菏泽 =====
        {"name": "菏泽城投控股集团有限公司", "city": "菏泽", "priority": 1},
        {"name": "山东菏建国有资本投资有限公司", "city": "菏泽", "priority": 2},
        {"name": "菏泽投资发展集团有限公司", "city": "菏泽", "priority": 2},
        {"name": "菏泽市城市开发投资有限公司", "city": "菏泽", "priority": 3},
        {"name": "菏泽市金地土地开发投资有限公司", "city": "菏泽", "priority": 3},
    ]


def get_summary():
    """返回城市分布摘要"""
    companies = get_shandong_companies()
    by_city = {}
    for c in companies:
        city = c["city"]
        if city not in by_city:
            by_city[city] = []
        by_city[city].append(c)

    summary = []
    for city, comps in sorted(by_city.items(), key=lambda x: -len(x[1])):
        p1 = sum(1 for c in comps if c["priority"] == 1)
        summary.append(f"{city}: {len(comps)}家 (优先{p1}家)")
    return summary
