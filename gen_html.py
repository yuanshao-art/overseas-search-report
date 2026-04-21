#!/usr/bin/env python3
"""
根据 bi-data-fetch 返回的JSON，解析数据并刷新报告HTML中的 RAW_DATA 与日期。
用法: python3 gen_html.py '<fetch_result_json>'
会同时更新: internal.html, external.html, index.html
"""
import sys, json, re, os, csv, io
from datetime import datetime, timedelta

def parse_fetch_result(raw_json: str):
    """解析 bi-data-fetch 返回的JSON，提取城市数据"""
    try:
        obj = json.loads(raw_json)
    except Exception:
        match = re.search(r'\{.*\}', raw_json, re.DOTALL)
        if match:
            obj = json.loads(match.group())
        else:
            raise ValueError("无法解析fetch结果JSON")

    # 优先尝试从 download_url 下载完整CSV
    download_url = obj.get('download_url') or (obj.get('data_ref') or {}).get('download_url')
    if download_url:
        try:
            import urllib.request
            with urllib.request.urlopen(download_url, timeout=30) as resp:
                csv_text = resp.read().decode('utf-8-sig')
            return parse_csv_text(csv_text)
        except Exception as e:
            print(f"⚠️ 下载CSV失败: {e}，回退到preview解析")

    # 回退：从preview字段解析（仅前100行）
    preview = obj.get('preview', '')
    if not preview and 'data_ref' in obj:
        preview = obj['data_ref'].get('preview', '')
    return parse_preview(preview)


def parse_csv_text(csv_text: str):
    """从完整CSV文本解析数据（推荐路径，含全量197条）"""
    reader = csv.reader(io.StringIO(csv_text))
    header = next(reader)
    # 列索引: [0]城市 [1]搜索量 [3]周环比变化率 [5]年同比变化率
    data = []
    for row in reader:
        if len(row) < 6:
            continue
        city = row[0].strip()
        if city in ('总计', '') or not city:
            continue
        try:
            vol = float(row[1])
            wow = float(row[3]) if row[3].strip() else 0.0   # 周环比_环比-变化率
            yoy = float(row[5]) if row[5].strip() else 0.0   # 年同比_环比-变化率
        except (ValueError, IndexError):
            continue
        data.append({'city': city, 'vol': vol, 'wow': wow, 'yoy': yoy})
    return data


def parse_preview(preview: str):
    """从preview文本解析（fallback，可能只有前100条）"""
    lines = [l.strip() for l in preview.strip().split('\n') if l.strip()]
    data = []
    for line in lines[1:]:  # 跳过header
        parts = [p.strip() for p in line.split(',')]
        if len(parts) < 6:
            continue
        city = parts[0]
        if city in ('总计', '') or not city:
            continue
        try:
            vol = float(parts[1])
            wow = float(parts[3]) if parts[3] else 0.0
            yoy = float(parts[5]) if parts[5] else 0.0
        except (ValueError, IndexError):
            continue
        data.append({'city': city, 'vol': vol, 'wow': wow, 'yoy': yoy})
    return data


# 区域分类
JK = {
    '首尔','济州岛','韩国','东京','大阪','釜山','京都','仁川','冲绳','福冈','神户',
    '箱根','名古屋','札幌','北海道','富士山','成田','函馆','西归浦','仙台','长崎',
    '上野','九州','别府','由布院','青森','静冈','旭川','小樽','熊本','奈良','佐贺',
    '洞爷湖','登别','白川乡','宇治','熊野古道','和歌山','千叶','泉佐野','神户',
}
SEA = {
    '曼谷','巴厘岛','普吉岛','泰国','吉隆坡','清迈','亚庇','槟城','马来西亚','富国岛',
    '越南','仙本那','胡志明','芽庄','迪拜','岘港','乌布','菲律宾','老挝','苏梅岛',
    '兰卡威','泗水','雅加达','芭堤雅','佩尼达岛','马尼拉','乔治市','柬埔寨','金边',
    '帕劳','龙目岛','文莱','科莫多岛','八打灵再也','怡宝','沙巴',
}
EU = {
    '巴黎','伦敦','维也纳','罗马','瑞士','巴塞罗那','米兰','英国','西班牙','法国',
    '德国','阿姆斯特丹','伊斯坦布尔','马德里','爱丁堡','柏林','冰岛','布达佩斯',
    '里斯本','雅典','慕尼黑','摩洛哥','土耳其','意大利','塞维利亚','荷兰','奥地利',
    '挪威','北欧','斯德哥尔摩','哥本哈根','布拉格','捷克','华沙','波兰','葡萄牙',
    '里昂','苏黎世','日内瓦','梵蒂冈','爱丁堡','南意','牛津','剑桥','马赛',
    '保加利亚','丹麦','哥本哈根','阿塞拜疆',
}


def classify(city):
    if city in JK: return 'japan_korea'
    if city in SEA: return 'sea'
    if city in EU: return 'europe'
    return 'others'


def gen_js_block(data):
    """生成完整的 RAW_DATA + UPDATE_DATE + DATA_RANGE JS块"""
    today = datetime.now().strftime('%Y-%m-%d')
    end_dt = datetime.now() - timedelta(days=1)
    start_dt = end_dt - timedelta(days=13)
    date_range = f"{start_dt.strftime('%Y-%m-%d')} ~ {end_dt.strftime('%Y-%m-%d')}（近14天）"

    lines = []
    for d in data:
        region = classify(d['city'])
        lines.append(
            f'  {{city:"{d["city"]}",vol:{round(d["vol"],2)},'
            f'wow:{round(d["wow"],4)},yoy:{round(d["yoy"],4)},region:"{region}"}},\n'
        )

    js = (
        'const RAW_DATA = [\n' + ''.join(lines) + '];\n'
        f'const UPDATE_DATE = "{today}";\n'
        f'const DATA_RANGE = "{date_range}";'
    )
    return js


def update_html(data, html_path):
    with open(html_path, 'r', encoding='utf-8') as f:
        html = f.read()

    new_block = gen_js_block(data)

    # 找到 RAW_DATA 开始位置
    start = html.find('const RAW_DATA = [')
    if start == -1:
        print(f"⚠️ {html_path}: 找不到 RAW_DATA，跳过")
        return False

    # 找到 DATA_RANGE 行末
    dr_pos = html.find('const DATA_RANGE = ', start)
    dr_end = html.find('\n', dr_pos) + 1

    new_html = html[:start] + new_block + '\n' + html[dr_end:]

    with open(html_path, 'w', encoding='utf-8') as f:
        f.write(new_html)

    city_count = new_html.count('{city:')
    print(f"✅ 已更新 {os.path.basename(html_path)}：{city_count} 条城市，{len(new_html)} 字节")
    return True


if __name__ == '__main__':
    raw_json = sys.argv[1] if len(sys.argv) > 1 else sys.stdin.read()

    try:
        data = parse_fetch_result(raw_json)
        print(f"解析到 {len(data)} 条城市数据")
        if not data:
            print("❌ 没有解析到有效数据，退出")
            sys.exit(1)
    except Exception as e:
        print(f"❌ 数据解析失败: {e}")
        sys.exit(1)

    base = os.path.dirname(os.path.abspath(__file__))
    targets = ['internal.html', 'external.html', 'index.html']
    ok = 0
    for fname in targets:
        path = os.path.join(base, fname)
        if os.path.exists(path):
            if update_html(data, path):
                ok += 1
        else:
            print(f"⚠️ {fname} 不存在，跳过")

    print(f"\n🎉 完成！共更新 {ok} 个HTML文件，{len(data)} 条城市数据")
