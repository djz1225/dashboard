#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""beautify.py —— 每半个月（15 天）自动切换一次的「美化增强包」

机制
----
看板由 GitHub Actions 每天构建 3 次，本模块在【构建期】按当天日期算出所属的
15 天周期序号，选出该周期的增强包（CSS + JS）注入全站。因此：

  · 不需要额外定时任务，任何一次构建都会自动带上当期美化；
  · 每满 15 天自动换一套，结构/数据/主色完全不动，只轮换视觉增强细节；
  · 全部增强都是"增量 + 防御式"写法，元素不存在时不报错、不改变布局。

周期计算
--------
周期序号 = (date.toordinal() // 15) % len(PACKS)
即每 15 天推进一格，四包循环，一年轮 24 次。

用法
----
    python beautify.py            # 打印当前周期与生效包
    python beautify.py --all      # 打印全部包清单
"""
import datetime
import sys

PERIOD_DAYS = 15

# ---------------------------------------------------------------- 增强包定义
# 每个包：(key, 名称, 说明, css, js)
# css 里只允许新增选择器或覆盖"装饰性"属性；js 必须自带存在性判断。

_P1_CSS = """
/* ==== 包1 入场动效：卡片渐入 + 图表条生长 + 数字滚动 ==== */
.reveal{opacity:0;transform:translateY(10px);
  transition:opacity .55s cubic-bezier(.22,.8,.3,1),transform .55s cubic-bezier(.22,.8,.3,1)}
.reveal.in{opacity:1;transform:none}
.bt i{transform-origin:left center;transition:transform .75s cubic-bezier(.22,.8,.3,1)}
.bt.pre i{transform:scaleX(0)}
.pill .ar{display:inline-block;transition:transform .2s ease}
.icard:hover .pill .ar{transform:translateY(-1px)}
@media(prefers-reduced-motion:reduce){
  .reveal,.bt i,.pill .ar{transition:none!important;opacity:1!important;transform:none!important}
}
@media print{.reveal{opacity:1!important;transform:none!important}.bt.pre i{transform:none!important}}
"""

_P1_JS = r"""
/* 包1：滚动入场 + 图表条生长 */
(function(){
  var els=[].slice.call(document.querySelectorAll('.icard,.scard,.chart,.tbl'));
  if(!els.length)return;
  var reduce=window.matchMedia&&window.matchMedia('(prefers-reduced-motion:reduce)').matches;
  if(reduce)return;
  els.forEach(function(e){e.classList.add('reveal');});
  var bars=[].slice.call(document.querySelectorAll('.bt i'));
  bars.forEach(function(b){b.parentNode.classList.add('pre');});
  function grow(){
    bars.forEach(function(b){
      var p=b.parentNode;
      if(p.classList.contains('pre')){
        var r=p.getBoundingClientRect();
        if(r.top<window.innerHeight-40&&r.bottom>0)p.classList.remove('pre');
      }
    });
  }
  if('IntersectionObserver' in window){
    var io=new IntersectionObserver(function(es){
      es.forEach(function(en){
        if(en.isIntersecting){en.target.classList.add('in');io.unobserve(en.target);}
      });
    },{rootMargin:'0px 0px -8% 0px',threshold:0.06});
    els.forEach(function(e){io.observe(e);});
  }else{
    els.forEach(function(e){e.classList.add('in');});
  }
  window.addEventListener('scroll',grow,{passive:true});
  window.addEventListener('resize',grow);
  setTimeout(grow,120);setTimeout(grow,900);
})();
"""

_P2_CSS = """
/* ==== 包2 阅读进度：顶部进度条 + 表格行位置标记 ==== */
#uxprog{position:fixed;left:0;top:0;height:3px;width:0;z-index:120;
  background:linear-gradient(90deg,#8fbf7a,#54895f 55%,#3f6b4f);
  box-shadow:0 0 8px rgba(63,107,79,.55);border-radius:0 3px 3px 0;
  pointer-events:none;transition:width .12s linear,opacity .3s ease}
#uxprog.idle{opacity:0}
table tbody td:first-child{position:relative}
table tbody tr:hover td:first-child::before{content:"";position:absolute;left:0;top:15%;bottom:15%;
  width:3px;border-radius:0 3px 3px 0;background:#6aa077}
.snav a.on::after{content:"";display:block;height:2px;margin:3px auto 0;width:60%;
  border-radius:2px;background:rgba(255,255,255,.65)}
@media print{#uxprog{display:none!important}}
@media(max-width:560px){#uxprog{height:2px}}
"""

_P2_JS = r"""
/* 包2：阅读进度条 */
(function(){
  if(document.getElementById('uxprog'))return;
  var bar=document.createElement('div');
  bar.id='uxprog';bar.className='idle';
  document.body.appendChild(bar);
  var raf=false;
  function upd(){
    var h=document.documentElement.scrollHeight-window.innerHeight;
    var y=window.pageYOffset||document.documentElement.scrollTop||0;
    var p=h>0?Math.min(100,Math.max(0,y/h*100)):0;
    bar.style.width=p+'%';
    bar.classList[(y<40||p>=99.6)?'add':'remove']('idle');
  }
  window.addEventListener('scroll',function(){
    if(raf)return;raf=true;requestAnimationFrame(function(){raf=false;upd();});
  },{passive:true});
  window.addEventListener('resize',upd);upd();
})();
"""

_P3_CSS = """
/* ==== 包3 氛围光影：卡片光斑跟随 + 图表标签联动高亮 ==== */
.icard,.chart,.tbl,.scard{position:relative;overflow:hidden}
.icard::after,.chart::after,.tbl::after,.scard::after{content:"";position:absolute;inset:0;
  pointer-events:none;opacity:0;transition:opacity .28s ease;
  background:radial-gradient(220px circle at var(--mx,50%) var(--my,0%),rgba(143,191,122,.20),transparent 65%)}
.icard:hover::after,.chart:hover::after,.tbl:hover::after,.scard:hover::after{opacity:1}
.chart .brow{transition:background .18s ease,transform .18s ease;border-radius:7px}
.chart .brow:hover{background:#f2f8ea;transform:translateX(2px)}
.chart .brow:hover .bl{color:#2f6b46;font-weight:700}
.chart .brow:hover .bv{color:#3f6b4f}
h1{background:linear-gradient(92deg,#3f6b4f 0,#54895f 45%,#3f6b4f 100%);
  -webkit-background-clip:text;background-clip:text;-webkit-text-fill-color:transparent}
@media print{
  .icard::after,.chart::after,.tbl::after,.scard::after{display:none}
  h1{-webkit-text-fill-color:#3f6b4f;background:none}
}
"""

_P3_JS = r"""
/* 包3：光斑跟随鼠标 */
(function(){
  if(!window.matchMedia||!window.matchMedia('(hover:hover)').matches)return;
  var sel='.icard,.chart,.tbl,.scard';
  function move(e){
    var el=e.currentTarget,r=el.getBoundingClientRect();
    el.style.setProperty('--mx',(e.clientX-r.left)+'px');
    el.style.setProperty('--my',(e.clientY-r.top)+'px');
  }
  function bind(){
    [].forEach.call(document.querySelectorAll(sel),function(el){
      if(el.__uxglow)return;el.__uxglow=1;
      el.addEventListener('mousemove',move,{passive:true});
    });
  }
  bind();
  new MutationObserver(bind).observe(document.body,{childList:true,subtree:true});
})();
"""

_P4_CSS = """
/* ==== 包4 精致细节：等宽数字 / 徽章微光 / 按压回弹 / 导航吸附收窄 ==== */
.icard,.pill,.iprice,td.pc,.bv,.histrow .hd,.nav-meta .ndate{font-variant-numeric:tabular-nums;
  font-feature-settings:"tnum" 1}
.iprice{letter-spacing:-.4px}
.pill{transition:box-shadow .22s ease,transform .22s ease}
.icard:hover .pill{box-shadow:0 4px 12px -8px rgba(192,57,43,.55)}
.icard:hover .pill.up{box-shadow:0 4px 12px -8px rgba(192,57,43,.6)}
.icard:hover .pill.down{box-shadow:0 4px 12px -8px rgba(30,132,73,.6)}
.toolnav a,.go,.hb,.nb{transition:transform .14s ease,box-shadow .18s ease,background .18s ease}
.toolnav a:active,.go:active,.nb:active{transform:scale(.97)}
.snav{padding-top:8px;padding-bottom:8px;transition:padding .22s ease,box-shadow .22s ease}
.snav.scrolled{padding-top:5px;padding-bottom:5px}
.snav.scrolled a{font-size:13px}
.tag,.lv{letter-spacing:.2px}
footer{letter-spacing:.1px}
@media print{.pill{box-shadow:none!important}}
"""

_P4_JS = r"""
/* 包4：无脚本行为，纯视觉细节（占位以保持接口一致） */
(function(){})();
"""

PACKS = [
    ("p1", "入场动效", "卡片滚动渐入、图表条生长、箭头微动", _P1_CSS, _P1_JS),
    ("p2", "阅读进度", "顶部阅读进度条、表格行位置标记、导航下划线", _P2_CSS, _P2_JS),
    ("p3", "氛围光影", "卡片光斑跟随鼠标、图表标签联动、标题渐变", _P3_CSS, _P3_JS),
    ("p4", "精致细节", "等宽数字、徽章微光、按压回弹、导航吸附收窄", _P4_CSS, _P4_JS),
]


def period_index(d=None):
    """当前 15 天周期序号（每 15 天 +1）"""
    d = d or datetime.date.today()
    return d.toordinal() // PERIOD_DAYS


def current_pack(d=None):
    """返回当期包 (key, name, desc, css, js)"""
    d = d or datetime.date.today()
    return PACKS[period_index(d) % len(PACKS)]


def period_range(d=None):
    """当期起止日期"""
    d = d or datetime.date.today()
    start = datetime.date.fromordinal(period_index(d) * PERIOD_DAYS)
    return start, start + datetime.timedelta(days=PERIOD_DAYS - 1)


def current_extras(d=None):
    """供热注入使用：返回 (css, js)"""
    _, _, _, css, js = current_pack(d)
    return css, js


def next_switch(d=None):
    d = d or datetime.date.today()
    _, end = period_range(d)
    return end + datetime.timedelta(days=1)


if __name__ == "__main__":
    if "--all" in sys.argv:
        for i, (k, n, desc, _c, _j) in enumerate(PACKS):
            print(f"{i}. [{k}] {n} —— {desc}")
        print(f"\n每 {PERIOD_DAYS} 天轮换一格，共 {len(PACKS)} 包")
    else:
        k, n, desc, css, js = current_pack()
        s, e = period_range()
        print(f"当前周期：{s} ~ {e}（第 {period_index()} 期）")
        print(f"生效包：[{k}] {n} —— {desc}")
        print(f"下次切换：{next_switch()}（自动，构建时生效）")
        print(f"注入体积：CSS {len(css)} 字符 / JS {len(js)} 字符")
