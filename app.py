# -*- coding: utf-8 -*-
"""
将軍様シミュレーター (The Glorious General) - Prime Number Hell Edition (Safe ver.)
"""
import os
import csv
import sys
from urllib.parse import quote
from flask import Flask, session, redirect, url_for, render_template, request
from flask_session import Session 

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dictator-secret-key-production")

# ====== セッション設定 ======
SESSION_DIR = "./flask_session_data"
if not os.path.exists(SESSION_DIR):
    os.makedirs(SESSION_DIR)

app.config["SESSION_TYPE"] = "filesystem" 
app.config["SESSION_FILE_DIR"] = SESSION_DIR
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_USE_SIGNER"] = True
Session(app)

# ====== ゲーム定数 ======
INIT_HAPPINESS = 30
LIMIT_HAPPINESS = 100
MAX_YEAR = 2035
SCENARIO_FILE = "dictator_scenario.csv"

# ====== ユーティリティ ======
def load_scenario():
    scenarios = {}
    if not os.path.exists(SCENARIO_FILE):
        return {}
    try:
        with open(SCENARIO_FILE, encoding='utf-8-sig') as f:
            reader = csv.DictReader(f)
            if reader.fieldnames:
                reader.fieldnames = [name.strip().replace('\ufeff', '') for name in reader.fieldnames]
            for row in reader:
                if "year" in row and row["year"]:
                    val = row["year"].strip()
                    if val.isdigit():
                        scenarios[int(val)] = row
                        scenarios[str(val)] = row
    except Exception:
        try:
            with open(SCENARIO_FILE, encoding='cp932') as f:
                reader = csv.DictReader(f)
                if reader.fieldnames:
                    reader.fieldnames = [name.strip() for name in reader.fieldnames]
                for row in reader:
                    if "year" in row and row["year"] and row["year"].strip().isdigit():
                        scenarios[int(row["year"].strip())] = row
        except:
            pass
    return scenarios

# ====== ルート定義 ======

@app.route('/')
def index():
    session.clear()
    session["year"] = 2026
    session["national_happiness"] = INIT_HAPPINESS
    session["log"] = []
    session["turn_complete"] = False 
    return render_template('title.html')

@app.route('/tutorial')
def tutorial():
    if "year" not in session:
        return redirect(url_for('index'))
    return render_template('tutorial.html')

@app.route('/terminal')
def terminal():
    if "year" not in session:
        return redirect(url_for('index'))
    
    year = session["year"]
    happiness = session.get("national_happiness", INIT_HAPPINESS)
    
    if happiness > LIMIT_HAPPINESS:
        return redirect(url_for('game_over', reason="overflow"))
    
    if year > MAX_YEAR:
        return redirect(url_for('ending'))

    scenarios = load_scenario()
    current_scene = scenarios.get(year) or scenarios.get(str(year)) or scenarios.get(int(year))
    
    if not current_scene:
        return redirect(url_for('ending'))
    
    log_text = "\n".join(session.get("log", []))

    return render_template('terminal_ui.html', 
                           year=year,
                           happiness=happiness,
                           scenario=current_scene,
                           log=log_text)

@app.route('/decision', methods=['POST'])
def decision():
    if session.get("turn_complete"):
        return redirect(url_for('generating'))

    selected_idx = request.form.get('selected_idx')
    year = session.get("year", 2026)
    scenarios = load_scenario()
    current_scene = scenarios.get(year) or scenarios.get(int(year))
    
    if not current_scene or not selected_idx:
        return redirect(url_for('terminal'))

    tag = current_scene.get(f"opt{selected_idx}_tag", "reform")
    choice_title = current_scene.get(f"opt{selected_idx}_title", "決断")

    delta = 0
    if tag == "delusion": delta = 13
    elif tag == "purge": delta = 11
    elif tag == "corruption": delta = 7
    elif tag == "reform": delta = -5

    current_val = session.get("national_happiness", INIT_HAPPINESS)
    session["national_happiness"] = max(0, current_val + delta)
    session["log"].append(f"[{year}] {choice_title}")
    
    session["turn_complete"] = True
    
    return redirect(url_for('generating'))

@app.route('/generating')
def generating():
    return render_template('generating.html')

@app.route('/process_next')
def process_next():
    if session.get("turn_complete"):
        session["year"] = session.get("year", 2026) + 1
        session["turn_complete"] = False
        
    return redirect(url_for('terminal'))

@app.route('/game_over')
def game_over():
    summary_title = "REGIME COLLAPSED"
    summary_text = "【幸福度の限界突破】\nプロパガンダの強度が限界を超えました。国民は「地上の楽園」という嘘に気づき、発狂した暴徒となって官邸になだれ込みました。計算が甘かったようです。"
    
    rank = "E"
    
    site_url = "https://shogun-simulator.onrender.com/" 
    
    share_text = f"【急募：亡命先】幸福度計算をミスって革命されました。探さないでください。 #将軍様シミュレーター\n{site_url}"
    share_url = "https://twitter.com/intent/tweet?text=" + quote(share_text)
    
    return render_template('summary.html', 
                           summary_title=summary_title, 
                           summary_text=summary_text, 
                           share_url=share_url, 
                           rank=rank)

@app.route('/ending')
def ending():
    happiness = session.get("national_happiness", 0)
    
    if happiness >= 96:
        rank = "A"
        title = "現人神"
        desc = "【96-100】奇跡的なバランス感覚です。あなたの嘘は真実になりました。国民は心からあなたを崇拝し、後世の歴史書はあなたを神として記録するでしょう。"
    elif happiness >= 91:
        rank = "B"
        title = "カリスマ指導者"
        desc = "【91-95】あと一歩で神になれました。熱狂的な支持を集めましたが、あなたは最後に少しだけ躊躇してしまいました。"
    elif happiness >= 86:
        rank = "C"
        title = "平凡な独裁者"
        desc = "【86-90】そこそこの支持と、そこそこの不満。あなたは可もなく不可もない統治者として過ごしました。"
    elif happiness >= 81:
        rank = "D"
        title = "小物"
        desc = "【81-85】かろうじて椅子に座っていましたが、誰もあなたの命令を真剣に聞いていませんでした。クーデターが起きなかったのが不思議です。"
    else:
        rank = "E"
        title = "臆病者"
        desc = "【0-80】あなたは暴動を恐れるあまり、媚びへつらうような政治を行いました。命は助かりましたが、歴史には「退屈な行政官」として記録されます。"

    site_url = "https://shogun-simulator.onrender.com/"
    share_text = f"【将軍様シミュレーター】ランク『{rank}: {title}』\n最終幸福度: {happiness}/100\n#将軍様シミュレーター\n{site_url}"
    share_url = "https://twitter.com/intent/tweet?text=" + quote(share_text)

    return render_template('summary.html', 
                           summary_title=f"ARCHIVE: {title}", 
                           summary_text=desc, 
                           share_url=share_url, 
                           rank=rank)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)