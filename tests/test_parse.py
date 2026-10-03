import sys; sys.path.insert(0,'scripts')
from bs4 import BeautifulSoup
import scrape
STD='''<div class="property_unit "><h2 class="property_unit-title"><a href="/ms/chuko/aichi/sc_nagoyashichikusa/nc_21670043/">【2沿線】</a></h2>
<dl><dt>物件名</dt><dd>オープンレジデンシア広小路今池</dd></dl><dl><dt>販売価格</dt><dd><span>2380万円</span></dd></dl>
<dl><dt>所在地</dt><dd>愛知県名古屋市千種区今池３</dd></dl><dl><dt>沿線・駅</dt><dd>地下鉄東山線「今池」徒歩5分</dd></dl>
<table><tr><td><dl><dt>専有面積</dt><dd>22.23m<sup>2</sup>（壁芯）</dd></dl></td><td><dl><dt>間取り</dt><dd>1K</dd></dl></td></tr></table>
<table><tr><td><dl><dt>築年月</dt><dd>2023年8月</dd></dl></td></tr></table></div>
<div class="property_unit"><h2><a href="/ikkodate/aichi/sc_nagoyashichikusa/nc_20607802/">x</a></h2><dl><dt>物件名</dt><dd>MOTOYAMA Hills</dd></dl><dl><dt>販売価格</dt><dd>1億8800万円</dd></dl><dl><dt>所在地</dt><dd>愛知県名古屋市千種区鹿子町４</dd></dl><dl><dt>沿線・駅</dt><dd>地下鉄東山線「本山」徒歩10分</dd></dl><dl><dt>土地面積</dt><dd>185.39m2・188.21m2</dd></dl><dl><dt>間取り</dt><dd>4LDK+3S（納戸）</dd></dl><dl><dt>建物面積</dt><dd>260.97m2・267.14m2</dd></dl></div>'''
CAS='''<div class="cassette property_unit"><h2><a href="/ms/shinchiku/aichi/sc_nagoyashichikusa/nc_67729873/">パークホームズ池下</a></h2>
<div class="cassette_basic-item"><p class="cassette_basic-title">所在地</p><p class="cassette_basic-value">名古屋市千種区春岡１</p></div>
<div class="cassette_basic-item"><p class="cassette_basic-title">交通</p><p class="cassette_basic-value">地下鉄東山線/池下 徒歩3分</p></div>
<div class="cassette_basic-item"><p class="cassette_basic-title">引渡時期</p><p class="cassette_basic-value">即引渡可</p></div>
<div class="cassette_price-value"><span class="cassette_price-accent"> 6298万円・7278万円</span> （第2期1次）</div><p class="cassette_price-description"> 3LDK / 77.42m<sup>2</sup></p></div>'''
base='https://suumo.jp/x/'
for a,f in scrape.units_standard(BeautifulSoup(STD,'html.parser')): print(scrape.to_row('中古マンション','千種区',a,f,base))
for a,f in scrape.units_cassette(BeautifulSoup(CAS,'html.parser')): print(scrape.to_row('新築マンション','千種区',a,f,base))
