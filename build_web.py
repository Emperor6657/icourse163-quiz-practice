# -*- coding: utf-8 -*-
"""
生成题库练习网页: 复习资料/题库练习.html
单文件、离线可用（数据内嵌），支持：章节练习 / 随机抽题 / 抽题组卷、
作答判分、显示/隐藏答案、打乱题目与选项顺序。
仅用 Python 标准库。
"""
import json
import os
import re

BASE = os.path.dirname(os.path.abspath(__file__))
DATA = os.path.join(BASE, "data")
# 输出到仓库根目录 index.html：GitHub Pages 的首页，网址为
# https://<user>.github.io/icourse163-quiz-practice/
OUT = os.path.join(BASE, "index.html")

CN_NUM = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
# 章节内题目顺序: 单选 → 多选 → 判断 → 填空
TYPE_RANK = {1: 0, 2: 1, 4: 2, 3: 3}
ZW = re.compile("[\u200b\u200c\u200d\u200e\u200f\u2060\ufeff\u202a-\u202e]")
TAG = re.compile(r"<[^>]+>")


def cn_to_int(s):
    if s == "十":
        return 10
    if len(s) == 1:
        return CN_NUM.get(s, 999)
    if s[0] == "十":
        return 10 + CN_NUM.get(s[1], 0)
    if s[-1] == "十":
        return CN_NUM.get(s[0], 0) * 10
    return CN_NUM.get(s[0], 0) * 10 + CN_NUM.get(s[-1], 0)


def clean_text(s):
    if not s:
        return ""
    s = ZW.sub("", s)
    s = TAG.sub("", s)
    s = re.sub(r"&#x([0-9a-fA-F]+);", lambda m: chr(int(m.group(1), 16)), s)
    s = re.sub(r"&#(\d+);", lambda m: chr(int(m.group(1))), s)
    s = s.replace("&nbsp;", " ").replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
    s = s.replace("&quot;", '"').replace("&#39;", "'").replace("&rlm;", "").replace("&lrm;", "")
    s = ZW.sub("", s)
    return re.sub(r"\s+", " ", s).strip()


def load_bank():
    quizzes = []
    for fn in sorted(os.listdir(DATA)):
        m = re.match(r"quiz_(\d+)\.json$", fn)
        if not m:
            continue
        with open(os.path.join(DATA, fn), encoding="utf-8") as f:
            d = json.load(f)
        quizzes.append(d)

    def chapno(d):
        m = re.search(r"第([一二三四五六七八九十]+)章", d.get("name", ""))
        return cn_to_int(m.group(1)) if m else 999

    quizzes.sort(key=chapno)
    bank = []
    for d in quizzes:
        qs = []
        for q in d["questions"].values():
            item = {
                "id": q["id"],
                "type": q["type"],
                "score": q.get("score") or 0,
                "title": clean_text(q.get("titleText") or q.get("title") or ""),
                "position": q.get("position"),
            }
            opts = q.get("options") or []
            item["opts"] = [{"t": clean_text(o.get("content") or ""), "a": bool(o.get("answer"))} for o in opts]
            if q["type"] == 3:
                ans = q.get("stdAnswer") or ""
                if isinstance(ans, list):
                    ans = "；".join(str(a) for a in ans)
                item["alt"] = [clean_text(a) for a in str(ans).split("##%_YZPRLFH_%##") if clean_text(a)]
            ana = q.get("analyse")
            if ana:
                if isinstance(ana, list):
                    ana = "；".join(clean_text(str(a)) for a in ana if a)
                ana = clean_text(str(ana))
                if ana:
                    item["ana"] = ana
            qs.append(item)
        m = re.search(r"第([一二三四五六七八九十]+)章", d["name"])
        # 章节内排序: 单选→多选→判断→填空，同题型按题库原始位置
        qs.sort(key=lambda x: (
            TYPE_RANK.get(x["type"], 9),
            x["position"] if isinstance(x["position"], (int, float)) else 10 ** 9,
            x["id"],
        ))
        bank.append({"quizId": d["quizId"], "name": d["name"], "no": cn_to_int(m.group(1)) if m else 99, "questions": qs})
    return bank


HTML = r"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>内燃机学 · 题库练习</title>
<style>
:root{--bd:#e3e6ee;--mut:#8a90a3;--blu:#2f6fed;--grn:#1e9e55;--red:#d64541;--bg:#f4f6fb}
*{box-sizing:border-box}
body{margin:0;font:15px/1.65 "Segoe UI","Microsoft YaHei",sans-serif;background:var(--bg);color:#262b3a}
header{position:sticky;top:0;z-index:9;background:#fff;border-bottom:1px solid var(--bd);padding:10px 18px;display:flex;align-items:center;gap:16px;flex-wrap:wrap}
header h1{font-size:18px;margin:0}
nav{display:flex;gap:6px}
nav button{border:1px solid var(--bd);background:#f8f9fd;border-radius:8px;padding:7px 16px;cursor:pointer;font-size:14px}
nav button.active{background:var(--blu);border-color:var(--blu);color:#fff}
main{max-width:960px;margin:18px auto;padding:0 14px 60px}
.panel{background:#fff;border:1px solid var(--bd);border-radius:12px;padding:14px 16px;margin-bottom:14px}
.controls{display:flex;flex-wrap:wrap;gap:10px 18px;align-items:center;margin-bottom:6px}
.controls label{display:flex;align-items:center;gap:5px;cursor:pointer;font-size:14px;color:#3c4257}
.controls select,.controls input[type=number],.controls input[type=text]{border:1px solid var(--bd);border-radius:6px;padding:5px 8px;font-size:14px;background:#fff}
.controls .num{width:64px}
button.act{border:0;border-radius:8px;padding:8px 18px;cursor:pointer;background:var(--blu);color:#fff;font-size:14px}
button.ghost{border:1px solid var(--bd);background:#fff;border-radius:8px;padding:7px 14px;cursor:pointer;font-size:13px;color:#3c4257}
button.ghost:hover{border-color:var(--blu);color:var(--blu)}
.stat{font-size:13px;color:var(--mut);margin-left:auto}
.qcard{border:1px solid var(--bd);border-radius:10px;padding:12px 14px;margin:12px 0;background:#fdfdff}
.qcard.right{border-color:#bfe4cd;background:#f7fcf9}
.qcard.wrong{border-color:#f0c9c7;background:#fdf7f6}
.qhead{display:flex;align-items:center;gap:8px;margin-bottom:6px;font-size:13px;color:var(--mut)}
.qno{font-weight:700;color:#262b3a;font-size:15px}
.badge{border-radius:5px;padding:1px 8px;font-size:12px;color:#fff}
.t1{background:#5b8def}.t2{background:#9a6ee8}.t3{background:#e0993f}.t4{background:#4cb0a5}
.verdict{margin-left:auto;font-weight:700}
.verdict.ok{color:var(--grn)}.verdict.no{color:var(--red)}
.qtitle{font-size:15.5px;margin:2px 0 8px}
.qopts{display:flex;flex-direction:column;gap:6px}
.opt{display:flex;gap:8px;align-items:flex-start;border:1px solid var(--bd);border-radius:8px;padding:7px 10px;cursor:pointer;background:#fff}
.opt::before{content:"";flex:0 0 auto;width:15px;height:15px;margin-top:4px;border:2px solid #b9c0d4;border-radius:50%;background:#fff;box-sizing:border-box}
.opt.opt-multi::before{border-radius:4px}
.opt:hover{border-color:#b9c6e8}
.opt .L{font-weight:700;color:#3c4257}
.opt.sel{border-color:var(--blu);background:#e3edff;box-shadow:inset 0 0 0 1px var(--blu)}
.opt.sel .L{color:var(--blu)}
.opt.sel::before{border-color:var(--blu);background:radial-gradient(circle at center,var(--blu) 0 3px,transparent 3.5px)}
.opt.opt-multi.sel::before{content:"✓";background:var(--blu);border-color:var(--blu);color:#fff;font-size:11px;line-height:12px;text-align:center}
.opt.ok{border-color:var(--grn);background:#ecf9f1}
.opt.ok .L{color:var(--grn)}
.opt.ok::before{border-color:var(--grn)}
.opt.ok.sel::before{background:radial-gradient(circle at center,var(--grn) 0 3px,transparent 3.5px)}
.opt.ok:not(.sel)::before{content:"✓";border-color:var(--grn);color:var(--grn);font-size:11px;line-height:12px;text-align:center}
.opt.no{border-color:#eeb9b7;background:#fdf1f0}
.opt.no .L{color:var(--red)}
.opt.no::before{border-color:var(--red)}
.opt.no.sel::before{background:radial-gradient(circle at center,var(--red) 0 3px,transparent 3.5px)}
.qans{margin-top:9px;border-left:3px solid var(--grn);background:#f2fbf5;padding:6px 12px;border-radius:0 6px 6px 0;font-size:14px}
.qans b{color:var(--grn)}
.qana{margin-top:6px;border-left:3px solid #c9cfdd;background:#f6f7fb;padding:6px 12px;border-radius:0 6px 6px 0;font-size:13.5px;color:#4a5068}
.fillrow{display:flex;gap:8px;align-items:center;margin-top:4px}
.fillrow input{flex:1;border:1px solid var(--bd);border-radius:8px;padding:8px 10px;font-size:15px}
.exambar{display:flex;gap:14px;align-items:center;background:#fff8ec;border:1px solid #f0dfc0;border-radius:10px;padding:10px 14px;margin-bottom:8px;font-size:14px;flex-wrap:wrap}
#ex-timer{font-weight:700;color:#b0650a;font-variant-numeric:tabular-nums}
.summary{border:1px solid var(--bd);border-radius:10px;padding:12px 16px;margin-top:12px;background:#fbfcff}
.summary h3{margin:2px 0 8px;font-size:16px}
.summary .row{display:flex;gap:22px;flex-wrap:wrap;font-size:14px;align-items:center}
.summary .big{font-size:30px;font-weight:800;color:var(--blu)}
.hint{font-size:12.5px;color:var(--mut)}
@media print{header nav,.controls button,.reveal-btn{display:none}}
</style>
</head>
<body>
<header>
  <h1>内燃机学 · 题库练习</h1>
  <nav>
    <button data-mode="chapter" class="active">章节练习</button>
    <button data-mode="random">随机抽题</button>
    <button data-mode="exam">抽题组卷</button>
  </nav>
</header>
<main>

<section id="panel-chapter">
  <div class="panel">
    <div class="controls">
      <label>章节 <select id="ch-chapter"></select></label>
      <label><input type="checkbox" id="ch-shuffle"> 打乱题目顺序</label>
      <label><input type="checkbox" id="ch-shuffleopts"> 打乱选项顺序</label>
      <label><input type="checkbox" id="ch-instant"> 即时判分</label>
      <button class="ghost" id="ch-showall">显示全部答案</button>
      <button class="ghost" id="ch-reset">重置作答</button>
      <span class="stat" id="ch-stat"></span>
    </div>
    <div class="hint">选择答案后点“显示答案”核对；勾选“即时判分”则作答后立即显示对错。</div>
  </div>
  <div id="ch-list"></div>
</section>

<section id="panel-random" hidden>
  <div class="panel">
    <div class="controls">
      <label>章节 <select id="rd-chapter"></select></label>
      <span>题型</span>
      <label><input type="checkbox" class="rd-type" value="1" checked>单选</label>
      <label><input type="checkbox" class="rd-type" value="2">多选</label>
      <label><input type="checkbox" class="rd-type" value="4" checked>判断</label>
      <label><input type="checkbox" class="rd-type" value="3" checked>填空</label>
      <label>数量 <input type="number" id="rd-count" class="num" value="10" min="1" max="271"></label>
      <label><input type="checkbox" id="rd-shuffleopts"> 打乱选项顺序</label>
      <label><input type="checkbox" id="rd-instant"> 即时判分</label>
      <button class="act" id="rd-go">抽 题</button>
      <button class="ghost" id="rd-showall">显示全部答案</button>
      <span class="stat" id="rd-stat"></span>
    </div>
    <div class="hint">从所选范围中随机抽题（不重复），结果按 单选 → 判断 → 填空 分块排列，适合错题重练。</div>
  </div>
  <div id="rd-list"></div>
</section>

<section id="panel-exam" hidden>
  <div class="panel">
    <div class="controls" style="margin-bottom:2px">
      <b>组卷设置</b>
      <span class="hint">勾选章节，设置每章抽题数量，交卷前不显示对错</span>
      <button class="ghost" id="ex-preset">模拟真实小测(5/5/5)</button>
      <label><input type="checkbox" id="ex-shuffle" checked> 打乱题目顺序</label>
      <label><input type="checkbox" id="ex-shuffleopts"> 打乱选项顺序</label>
      <button class="act" id="ex-go">生成试卷</button>
    </div>
    <div class="controls" id="ex-chapters" style="margin-top:4px"></div>
    <div class="controls">
      <label>每章单选 <input type="number" class="num" id="ex-n1" value="5" min="0"></label>
      <label>判断 <input type="number" class="num" id="ex-n4" value="5" min="0"></label>
      <label>填空 <input type="number" class="num" id="ex-n3" value="5" min="0"></label>
    </div>
  </div>
  <div id="ex-wrap" hidden>
    <div class="exambar">
      <b id="ex-name">试卷</b>
      <span>用时 <span id="ex-timer">00:00</span></span>
      <span id="ex-progress"></span>
      <span style="margin-left:auto"><button class="act" id="ex-submit">交卷评分</button></span>
    </div>
    <div id="ex-list"></div>
    <div id="ex-result"></div>
  </div>
</section>

</main>
<script>
const BANK = __DATA__;
const TN = {1:"单选题",2:"多选题",3:"填空题",4:"判断题"};
const LET = "ABCDEFGHIJ";

const $ = s => document.querySelector(s);
const el = (tag, cls, html) => { const e = document.createElement(tag); if (cls) e.className = cls; if (html != null) e.innerHTML = html; return e; };
function shuffle(a){ for(let i=a.length-1;i>0;i--){ const j=Math.floor(Math.random()*(i+1)); [a[i],a[j]]=[a[j],a[i]]; } return a; }
function norm(s){ return (s||"").toLowerCase().replace(/[\s，。、；：？！（）()【】\[\]"'“”‘’·,.;:?!\-—_]/g,""); }
function esc(s){ return (s||"").replace(/&/g,"&amp;").replace(/</g,"&lt;").replace(/>/g,"&gt;"); }

let seq = 0;
const state = { answers: new Map(), revealed: new Set(), optOrder: new Map(), instant: false, examJudged: false };
function deriveOrder(q, doShuffle){
  let order = q.opts.map((_, i) => i);
  if (doShuffle && q.opts.length > 2) shuffle(order);
  return order;
}
function makeInstances(qs, chName, shuffleOpts){
  return qs.map(q => {
    const key = "k" + (++seq);
    state.optOrder.set(key, deriveOrder(q, shuffleOpts));
    return { q, chName, key };
  });
}

function answerText(q){
  if (q.type === 3) {
    if (!q.alt || !q.alt.length) return "(缺失)";
    return q.alt[0] + (q.alt.length > 1 ? "（或：" + q.alt.slice(1).join("、") + "）" : "");
  }
  const idx = q.opts.map((o, i) => o.a ? i : -1).filter(i => i >= 0);
  return idx.map(i => LET[i] + "、" + q.opts[i].t).join("　");
}
function judge(inst, ans){
  const q = inst.q;
  if (q.type === 3) {
    if (ans.text == null || ans.text === "") return null;
    return q.alt.some(a => norm(a) === norm(ans.text));
  }
  if (!ans.sel || ans.sel.size === 0) return null;
  const correct = new Set(q.opts.map((o, i) => o.a ? i : -1).filter(i => i >= 0));
  if (ans.sel.size !== correct.size) return false;
  for (const i of ans.sel) if (!correct.has(i)) return false;
  return true;
}
function isShown(inst){ return state.revealed.has(inst.key) || (inst.exam && state.examJudged); }

function renderList(container, instances, opts){
  container.innerHTML = "";
  const { mode } = opts || {};
  instances.forEach((inst, i) => {
    inst.exam = mode === "exam";
    const q = inst.q;
    const card = el("div", "qcard");
    card.dataset.key = inst.key;
    const ans = state.answers.get(inst.key) || { sel: new Set(), text: "" };
    state.answers.set(inst.key, ans);
    const shown = isShown(inst);
    let head = '<span class="qno">' + (i + 1) + '.</span>' +
      '<span class="badge t' + q.type + '">' + TN[q.type] + '</span>' +
      '<span>' + q.score + '分</span><span>' + inst.chName + '</span>' +
      '<span class="verdict" data-verdict></span>';
    if (!(mode === "exam" && !state.examJudged))
      head += '<button class="ghost reveal-btn" style="margin-left:8px">' + (shown ? "隐藏答案" : "显示答案") + "</button>";
    card.appendChild(el("div", "qhead", head));
    card.appendChild(el("div", "qtitle", esc(q.title)));

    if (q.type === 3) {
      card.appendChild(el("div", "fillrow", '<input type="text" placeholder="请输入答案" value="' + esc(ans.text || "") + '">'));
    } else {
      const wrap = el("div", "qopts");
      state.optOrder.get(inst.key).forEach((oi, pos) => {
        const o = q.opts[oi];
        const opt = el("div", "opt" + (q.type === 2 ? " opt-multi" : ""), '<span class="L">' + LET[pos] + '.</span><span>' + esc(o.t) + "</span>");
        opt.dataset.oi = oi;
        if (ans.sel.has(oi)) opt.classList.add("sel");
        wrap.appendChild(opt);
      });
      card.appendChild(wrap);
    }
    const ansBox = el("div", "qans", "答案：<b>" + esc(answerText(q)) + "</b>");
    ansBox.hidden = !shown;
    card.appendChild(ansBox);
    if (shown && q.ana) card.appendChild(el("div", "qana", "解析：" + esc(q.ana)));
    container.appendChild(card);
    paint(card, inst);
  });
}

function paint(card, inst){
  const q = inst.q;
  const ans = state.answers.get(inst.key);
  const shown = isShown(inst);
  card.querySelectorAll(".opt").forEach(opt => {
    const oi = +opt.dataset.oi;
    opt.classList.remove("ok", "no");
    opt.classList.toggle("sel", ans.sel.has(oi));
    if (shown) {
      if (q.opts[oi].a) opt.classList.add("ok");
      else if (ans.sel.has(oi)) opt.classList.add("no");
    }
  });
  const v = card.querySelector("[data-verdict]");
  if (shown) {
    const j = judge(inst, ans);
    if (j === true) { v.textContent = "✓ 答对"; v.className = "verdict ok"; card.classList.add("right"); card.classList.remove("wrong"); }
    else if (j === false) { v.textContent = "✗ 答错"; v.className = "verdict no"; card.classList.add("wrong"); card.classList.remove("right"); }
    else { v.textContent = "未作答"; v.className = "verdict"; card.classList.remove("right", "wrong"); }
  } else {
    v.textContent = ""; v.className = "verdict"; card.classList.remove("right", "wrong");
  }
}

function updateStat(statEl, instances){
  let answered = 0, correct = 0, shown = 0;
  instances.forEach(inst => {
    const j = judge(inst, state.answers.get(inst.key));
    if (j !== null) answered++;
    if (j === true && isShown(inst)) correct++;
    if (isShown(inst)) shown++;
  });
  statEl.textContent = "共 " + instances.length + " 题 · 已答 " + answered + " · 答对 " + correct + (shown ? " · 已显示答案 " + shown : "");
}

function bindPanel(listEl, statEl, getInstances, mode){
  listEl.addEventListener("click", e => {
    const card = e.target.closest(".qcard"); if (!card) return;
    const key = card.dataset.key;
    const inst = getInstances().find(x => x.key === key); if (!inst) return;
    if (e.target.closest(".reveal-btn")) {
      if (state.revealed.has(key)) state.revealed.delete(key); else state.revealed.add(key);
      card.querySelector(".qans").hidden = !state.revealed.has(key);
      const ana = card.querySelector(".qana");
      if (ana) ana.hidden = !state.revealed.has(key);
      card.querySelector(".reveal-btn").textContent = state.revealed.has(key) ? "隐藏答案" : "显示答案";
      paint(card, inst); updateStat(statEl, getInstances());
      return;
    }
    const opt = e.target.closest(".opt"); if (!opt) return;
    const q = inst.q, ans = state.answers.get(key), oi = +opt.dataset.oi;
    if (q.type === 2) { ans.sel.has(oi) ? ans.sel.delete(oi) : ans.sel.add(oi); }
    else { ans.sel = new Set([oi]); }
    if (state.instant) state.revealed.add(key);
    card.querySelector(".qans").hidden = !isShown(inst);
    paint(card, inst); updateStat(statEl, getInstances());
  });
  listEl.addEventListener("input", e => {
    if (!e.target.matches(".fillrow input")) return;
    const card = e.target.closest(".qcard");
    const key = card.dataset.key;
    const inst = getInstances().find(x => x.key === key); if (!inst) return;
    state.answers.get(key).text = e.target.value;
    if (state.instant && e.target.value) state.revealed.add(key);
    card.querySelector(".qans").hidden = !isShown(inst);
    paint(card, inst); updateStat(statEl, getInstances());
  });
}

const panels = { chapter: $("#panel-chapter"), random: $("#panel-random"), exam: $("#panel-exam") };
document.querySelectorAll("nav button").forEach(b => b.addEventListener("click", () => {
  document.querySelectorAll("nav button").forEach(x => x.classList.remove("active"));
  b.classList.add("active");
  Object.entries(panels).forEach(([k, p]) => p.hidden = k !== b.dataset.mode);
}));

/* ---------- 章节练习 ---------- */
const chSel = $("#ch-chapter");
BANK.forEach(ch => { const o = el("option", null, ch.name + "（" + ch.questions.length + "题）"); o.value = ch.no; chSel.appendChild(o); });
const allOpt = el("option", null, "全部章节（" + BANK.reduce((s, c) => s + c.questions.length, 0) + "题）"); allOpt.value = 0; chSel.appendChild(allOpt);

let chBase = [], chInstances = [];
function rebuildChapters(){
  const no = +chSel.value;
  let qs = [];
  BANK.forEach(ch => { if (!no || ch.no === no) ch.questions.forEach(q => qs.push({ q, ch: ch.name })); });
  chBase = makeInstances(qs.map(x => x.q), "", $("#ch-shuffleopts").checked);
  chBase.forEach((inst, i) => inst.chName = qs[i].ch);
  state.revealed.clear();
  applyChOrder();
}
// 打乱题目顺序：仅在每种题型内部打乱，保持 单选→判断→填空 的块结构（全部章节视图下也不跨章）
function applyChOrder(){
  if ($("#ch-shuffle").checked) {
    const groups = new Map();
    chBase.forEach(inst => {
      const k = inst.chName + "|" + inst.q.type;
      if (!groups.has(k)) groups.set(k, []);
      groups.get(k).push(inst);
    });
    chInstances = [];
    groups.forEach(g => chInstances.push(...shuffle(g.slice())));
  } else {
    chInstances = chBase.slice();
  }
  renderList($("#ch-list"), chInstances, { mode: "chapter" });
  updateStat($("#ch-stat"), chInstances);
}
// 打乱选项顺序：仅重导出各题选项映射，题目顺序与作答不受影响
function applyChOpts(){
  const doShuffle = $("#ch-shuffleopts").checked;
  chBase.forEach(inst => state.optOrder.set(inst.key, deriveOrder(inst.q, doShuffle)));
  renderList($("#ch-list"), chInstances, { mode: "chapter" });
  updateStat($("#ch-stat"), chInstances);
}
$("#ch-chapter").addEventListener("change", rebuildChapters);
$("#ch-shuffle").addEventListener("change", applyChOrder);
$("#ch-shuffleopts").addEventListener("change", applyChOpts);
$("#ch-instant").addEventListener("change", e => state.instant = e.target.checked);
$("#ch-showall").addEventListener("click", () => {
  const show = chInstances.some(x => !isShown(x));
  chInstances.forEach(x => show ? state.revealed.add(x.key) : state.revealed.delete(x.key));
  renderList($("#ch-list"), chInstances, { mode: "chapter" }); updateStat($("#ch-stat"), chInstances);
});
$("#ch-reset").addEventListener("click", () => { chBase.forEach(x => { state.answers.delete(x.key); state.revealed.delete(x.key); }); rebuildChapters(); });
bindPanel($("#ch-list"), $("#ch-stat"), () => chInstances, "chapter");
rebuildChapters();

/* ---------- 随机抽题 ---------- */
const rdSel = $("#rd-chapter");
BANK.forEach(ch => { const o = el("option", null, ch.name); o.value = ch.no; rdSel.appendChild(o); });
const allOpt2 = el("option", null, "全部章节"); allOpt2.value = 0; rdSel.appendChild(allOpt2);

let rdInstances = [];
function rdDraw(){
  const no = +rdSel.value;
  const types = new Set([...document.querySelectorAll(".rd-type:checked")].map(x => +x.value));
  let pool = [];
  BANK.forEach(ch => { if (!no || ch.no === no) ch.questions.forEach(q => { if (types.has(q.type)) pool.push(q); }); });
  if (!pool.length) { alert("所选范围内没有符合条件的题目"); return; }
  const n = Math.min(+$("#rd-count").value || 10, pool.length);
  shuffle(pool);
  let picked = pool.slice(0, n);
  // 按题型分块排列: 单选→多选→判断→填空（块内保持随机抽中的顺序）
  const rank = {1: 0, 2: 1, 4: 2, 3: 3};
  picked.sort((a, b) => rank[a.type] - rank[b.type]);
  rdInstances = makeInstances(picked, no ? BANK.find(c => c.no === no).name : "混合章节", $("#rd-shuffleopts").checked);
  state.revealed.clear();
  renderList($("#rd-list"), rdInstances, { mode: "random" });
  updateStat($("#rd-stat"), rdInstances);
}
$("#rd-go").addEventListener("click", rdDraw);
// 打乱选项顺序只影响当前已抽出的题，不重新抽题
$("#rd-shuffleopts").addEventListener("change", () => {
  const doShuffle = $("#rd-shuffleopts").checked;
  rdInstances.forEach(inst => state.optOrder.set(inst.key, deriveOrder(inst.q, doShuffle)));
  renderList($("#rd-list"), rdInstances, { mode: "random" });
  updateStat($("#rd-stat"), rdInstances);
});
$("#rd-instant").addEventListener("change", e => state.instant = e.target.checked);
$("#rd-showall").addEventListener("click", () => {
  const show = rdInstances.some(x => !isShown(x));
  rdInstances.forEach(x => show ? state.revealed.add(x.key) : state.revealed.delete(x.key));
  renderList($("#rd-list"), rdInstances, { mode: "random" }); updateStat($("#rd-stat"), rdInstances);
});
bindPanel($("#rd-list"), $("#rd-stat"), () => rdInstances, "random");

/* ---------- 抽题组卷 ---------- */
const exCh = $("#ex-chapters");
BANK.forEach(ch => {
  const l = el("label", null, '<input type="checkbox" class="ex-ch" value="' + ch.no + '" checked> ' + ch.name.replace("测验", ""));
  exCh.appendChild(l);
});
$("#ex-preset").addEventListener("click", () => { $("#ex-n1").value = 5; $("#ex-n4").value = 5; $("#ex-n3").value = 5; });

let exInstances = [], exTimer = null;
function exBuild(){
  const nos = new Set([...document.querySelectorAll(".ex-ch:checked")].map(x => +x.value));
  const n1 = +$("#ex-n1").value || 0, n4 = +$("#ex-n4").value || 0, n3 = +$("#ex-n3").value || 0;
  let qs = [];
  BANK.forEach(ch => {
    if (!nos.has(ch.no)) return;
    [1, 4, 3].forEach(t => {
      const n = t === 1 ? n1 : t === 4 ? n4 : n3;
      if (!n) return;
      const pool = shuffle(ch.questions.filter(q => q.type === t).slice());
      pool.slice(0, n).forEach(q => qs.push({ q, ch: ch.name }));
    });
  });
  if (!qs.length) { alert("请选择章节并设置数量"); return; }
  // 打乱题目顺序：仅在各章各题型内部打乱，保持 单选→判断→填空 的块结构
  if ($("#ex-shuffle").checked) {
    const groups = new Map();
    qs.forEach(x => {
      const k = x.ch + "|" + x.q.type;
      if (!groups.has(k)) groups.set(k, []);
      groups.get(k).push(x);
    });
    qs = [];
    groups.forEach(g => qs.push(...shuffle(g.slice())));
  }
  exInstances = makeInstances(qs.map(x => x.q), "", $("#ex-shuffleopts").checked);
  exInstances.forEach((inst, i) => inst.chName = qs[i].ch);
  state.revealed.clear(); state.examJudged = false;
  $("#ex-wrap").hidden = false;
  $("#ex-name").textContent = "模拟卷 · " + exInstances.length + " 题 · " + exInstances.reduce((s, x) => s + x.q.score, 0) + " 分";
  $("#ex-result").innerHTML = "";
  $("#ex-submit").hidden = false;
  renderList($("#ex-list"), exInstances, { mode: "exam" });
  updateExProgress();
  clearInterval(exTimer);
  const t0 = Date.now();
  exTimer = setInterval(() => {
    const s = Math.floor((Date.now() - t0) / 1000);
    $("#ex-timer").textContent = String(Math.floor(s / 60)).padStart(2, "0") + ":" + String(s % 60).padStart(2, "0");
  }, 500);
}
function updateExProgress(){
  const done = exInstances.filter(x => judge(x, state.answers.get(x.key)) !== null).length;
  $("#ex-progress").textContent = "已答 " + done + " / " + exInstances.length;
}
$("#ex-go").addEventListener("click", exBuild);
bindPanel($("#ex-list"), $("#ex-progress"), () => exInstances, "exam");
$("#ex-list").addEventListener("click", updateExProgress);
$("#ex-list").addEventListener("input", updateExProgress);
$("#ex-submit").addEventListener("click", () => {
  clearInterval(exTimer);
  state.examJudged = true;
  exInstances.forEach(x => state.revealed.add(x.key));
  renderList($("#ex-list"), exInstances, { mode: "exam" });
  const g = { 1: [0, 0], 2: [0, 0], 3: [0, 0], 4: [0, 0] };
  let score = 0, total = 0;
  exInstances.forEach(x => {
    const j = judge(x, state.answers.get(x.key));
    g[x.q.type][1]++; if (j === true) { g[x.q.type][0]++; score += x.q.score; }
    total += x.q.score;
  });
  const rows = [1, 2, 3, 4].filter(t => g[t][1]).map(t =>
    "<span>" + TN[t] + "：<b>" + g[t][0] + "</b>/" + g[t][1] + "</span>").join("");
  const pct = total ? Math.round(score / total * 100) : 0;
  $("#ex-result").innerHTML = '<div class="summary"><h3>评分结果</h3><div class="row">' +
    '<span class="big">' + score + "</span><span>/ " + total + " 分（" + pct + "%）</span></div>" +
    '<div class="row" style="margin-top:8px">' + rows + "</div>" +
    '<div class="hint" style="margin-top:6px">用时 ' + $("#ex-timer").textContent + "。正确答案已在题中标绿。</div></div>";
  $("#ex-result").scrollIntoView({ behavior: "smooth" });
});
</script>
</body>
</html>
"""

def main():
    bank = load_bank()
    total = sum(len(c["questions"]) for c in bank)
    data = json.dumps(bank, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    html = HTML.replace("__DATA__", data)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(html)
    print("生成 %s（%d 章 %d 题，%.0f KB）" % (OUT, len(bank), total, os.path.getsize(OUT) / 1024))


if __name__ == "__main__":
    main()
