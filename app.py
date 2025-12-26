# -*- coding: utf-8 -*-
"""
将軍様シミュレーター (The Glorious General)
Xブラウザ対応・Cookieセッション・リダイレクト回避版
"""
import os
import csv
import sys
from urllib.parse import quote
from flask import Flask, session, redirect, url_for, render_template, request

app = Flask(__name__)
# セキュリティキーの設定
app.secret_key = os.environ.get("SECRET_KEY", "dictator-secret-key-production")

# ====== セッション設定 ======
# Xのブラウザ（WebView）対策：外部サイトからの遷移でもセッションを維持しやすくする
# ファイルシステム保存(Flask-Session)は廃止し、標準のCookieセッションを使用
app.config["SESSION_COOKIE_SAMESITE"] = 'Lax'
app.config["SESSION_COOKIE_SECURE"] = True 

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
    # 連打対策等で既にターン完了している場合
    if session.get("turn_complete"):
        # 安全策として直接レンダリング
        return render_template('generating.html')

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
    
    # ログ更新（Cookieセッション用にリストを再代入）
    current_log = session.get("log", [])
    current_log.append(f"[{year}] {choice_title}")
    session["log"] = current_log
    
    session["turn_complete"] = True
    
    # 【重要変更】リダイレクトせず、直接HTMLを表示してブラウザの負担を減らす
    # これでX内ブラウザで「真っ暗になる」現象を防ぎます
    return render_template('generating.html')

@app.route('/generating')
def generating():
    return render_template('generating.html')

@app.route('/process_next')
def process_next():
    if session.get("turn_complete"):
        session["year"] = session.get("year", 2026) + 1
        session["turn_complete"] = False
        session.modified = True
        
    return redirect(url_for('terminal'))

@app.route('/game_over')
def game_over():
    summary_title = "REGIME COLLAPSED"
    summary_text = "【幸福度の限界突破】\nプロパガンダの強度が限界を超えました。国民は「地上の楽園」という嘘に気づき、発狂した暴徒となって官邸になだれ込みました。計算が甘かったようです。皮肉なことに、あなたが作り上げた「完璧な虚構」の中に、あなた自身の逃げ場だけが用意されていませんでした。"
    
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
        desc = "奇跡的なバランス感覚です。あなたのついた嘘は、もはや真実を超えました。国民はあなたの肖像画を見るだけで感涙し、物理法則さえもあなたの言葉に従うと信じられています。後世の歴史書は、あなたを人間ではなく「神話上の存在」として記録するでしょう。"
    elif happiness >= 91:
        rank = "B"
        title = "カリスマ指導者"
        desc = "あと一歩で神になれました。あなたは熱狂的な支持と雷鳴のような拍手に包まれ、偉大な指導者として君臨しました。しかし、最後にわずかな「人間味」を見せてしまったようです。歴史はあなたを、類まれなる独裁者として、敬意と少しの恐怖をもって語り継ぐでしょう。"
    elif happiness >= 86:
        rank = "C"
        title = "平凡な独裁者"
        desc = "そこそこの支持と、そこそこの不満。あなたは粛清も改革も中途半端にこなし、定年まで勤め上げた公務員のように統治を終えました。教科書のあなたのページは、学生たちが居眠りをするのに最適な睡眠導入剤となるでしょう。"
    elif happiness >= 81:
        rank = "D"
        title = "小物"
        desc = "かろうじて椅子に座っていましたが、側近たちはあなたの背後で舌を出していました。クーデターが起きなかったのは、あなたが無害すぎて、弾薬を使う価値もないと判断されたからです。銅像が建つことはなく、あなたの名前はクイズ番組の難問としてのみ残ります。"
    else:
        rank = "E"
        title = "臆病者"
        desc = "あなたは暴動を恐れるあまり、八方美人の如く媚びへつらう政治を行いました。その結果、命だけは助かりましたが、独裁者としての威厳は皆無です。歴史家はあなたを「将軍」ではなく、ただの「退屈な事務次官」として分類しました。"

    site_url = "https://shogun-simulator.onrender.com/"
    share_text = f"【将軍様シミュレーター】ランク『{rank}: {title}』\n最終幸福度: {happiness}/100\n#将軍様シミュレーター\n{site_url}"
    share_url = "https://twitter.com/intent/tweet?text=" + quote(share_text)

    return render_template('summary.html', 
                           summary_title=f"ARCHIVE: {title}", 
                           summary_text=desc, 
                           share_url=share_url, 
                           rank=rank)

if __name__ == '__main__':
    app.run(debug=False, host='0.0.0.0', port=5000)