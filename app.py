import datetime
from zoneinfo import ZoneInfo
import os
import re
import pytz
import streamlit as st
import urllib.parse
from horoscope_calc import validate_and_get_coords, get_chart_data, EPHE_PATH, get_cities_for_prefecture

# get_synastry_data が horoscope_calc に無い場合の安全対策
try:
    from horoscope_calc import get_synastry_data
except ImportError:
    get_synastry_data = None

icon_url = "https://github.com/marrongrace/horoscope-app/blob/main/Horo_logo.png"

st.set_page_config(
    page_title="HoroNote - Horoscope Information Export System",
    page_icon="Horo_logo.png",
    layout="centered",
)

# スマホのホーム画面用アイコン設定をHTMLインジェクションで追加
st.markdown(f"""
    <link rel="apple-touch-icon" href="{icon_url}">
""", unsafe_allow_html=True)

# グローバル国・州・地域マスターリスト（提供いただいたデータ[cite: 1]）
GLOBAL_COUNTRIES = [
    "Afghanistan", "Alabama", "Alaska", "Albania", "Algeria", "American Samoa", "Andorra", "Angola", "Anguilla", "Antigua & Barbuda", "Argentina",
    "Arizona", "Arkansas", "Armenia", "Australia", "Austria", "Azerbaijan",
    "Bahamas", "Bahrain", "Bangladesh", "Barbados", "Belarus", "Belgium", "Belize", "Benin", "Bermuda", "Bhutan",
    "Bolivia", "Bosnia and Herzegovina", "Botswana", "Brazil", "Brunei", "Bulgaria", "Burkina Faso", "Burundi", "California", "Cambodia",
    "Cameroon", "Canada", "Cape Verde", "Cayman Islands", "Central African Republic", "Chad","Chile", "China", "Colombia", "Colorado",
    "Comoros", "Congo", "Connecticut","Cook Islands", "Costa Rica", "Croatia", "Cuba", "Cyprus", "Czech Republic",
    "Delaware","Denmark", "District of Columbia", "Djibouti", "Dominica", "Dominican Republic","Democratic Republic of the Congo", "East Timor","Ecuador", "Egypt",
    "El Salvador", "Equatorial Guinea", "Eritrea", "Estonia", "Eswatini", "Ethiopia", "Faeroe Islands", "Falkland Islands", "Fiji", "Finland", "Florida",
    "France", "French Guiana", "French Polynesia", "Gabon", "Gambia", "Georgia", "Germany", "Ghana", "Gibraltar", "Greece",
    "Greenland", "Grenada", "Guadeloupe", "Guam", "Guatemala", "Guernsey", "Guinea", "Guinea-Bissau", "Guyana", "Haiti",
    "Hawaii", "Honduras", "Hungary", "Iceland", "Idaho", "Illinois", "India", "Indiana", "Indonesia", "Iowa",
    "Iran", "Iraq", "Ireland", "Isle of Man", "Israel", "Italy", "Ivory Coast", "Jamaica", "Japan", "Jersey",
    "Jordan", "Kansas", "Kazakhstan", "Kentucky", "Kenya", "Kiribati", "Kuwait", "Kyrgyzstan", "Laos", "Latvia",
    "Lebanon", "Lesotho", "Liberia", "Libya", "Liechtenstein", "Lithuania", "Louisiana", "Luxembourg", "Madagascar",
    "Maine", "Malawi", "Malaysia", "Maldives", "Mali", "Malta", "Marshall Islands", "Martinique", "Maryland", "Massachusetts",
    "Mauritania", "Mauritius", "Mayotte", "Mexico", "Michigan", "Micronesia", "Midway Islands", "Minnesota", "Mississippi", "Missouri",
    "Moldova", "Monaco", "Mongolia", "Montana", "Montserrat", "Morocco", "Mozambique", "Myanmar", "Namibia", "Nauru",
    "Nebraska", "Nepal", "Netherlands", "Netherlands Antilles", "Nevada", "New Caledonia", "New Hampshire", "New Jersey", "New Mexico", "New York",
    "New Zealand", "Nicaragua", "Niger", "Nigeria", "Niue", "Norfolk Islands", "North Carolina", "North Dakota", "North Macedonia", "Northern Mariana Islands",
    "Norway", "Ohio", "Oklahoma", "Oman", "Oregon", "Pakistan", "Palau", "Palestine", "Panama", "Papua New Guinea",
    "Paraguay", "Pennsylvania", "Peru", "Philippines", "Pitcairn", "Poland", "Portugal", "Puerto Rico", "Qatar", "Reunion",
    "Rhode Island", "Romania", "Russia", "Rwanda", "Saint Helena", "Saint Kitts-Nevis", "Saint Lucia", "Saint Pierre and Miquelon", "Saint Vincent and Grenadines", "Samoa",
    "San Marino", "Sao Tome and Principe", "Saudi Arabia", "Senegal", "Seychelles", "Sierra Leone", "Singapore", "Slovakia", "Slovenia", "Solomon Islands",
    "Somalia", "South Africa", "South Carolina", "South Dakota", "South Georgia", "Spain", "Sri Lanka", "Sudan", "Suriname",
    "Sweden", "Switzerland", "Syria", "Taiwan", "Tajikistan", "Tanzania", "Tennessee", "Texas", "Thailand", "Togo",
    "Tokelau Islands", "Tonga", "Trinidad and Tobago", "Tunisia", "Turkey", "Turkmenistan", "Turks and Caicos", "Tuvalu", "Uganda", "Ukraine",
    "United Arab Emirates", "United Kingdom", "Uruguay", "Utah", "Uzbekistan", "Vanuatu", "Vatican City State", "Venezuela", "Vermont", "Vietnam", "Virgin Islands",
    "Virginia", "Wake Island", "Wallis and Futuna", "Washington", "West Virginia", "Western Sahara", "Wisconsin", "Wyoming", "Yemen", "Yugoslavia", "Zambia",
    "Zimbabwe"
]

country_default = "Please select a country/region"
COUNTRY_OPTIONS = [country_default] + GLOBAL_COUNTRIES

# ==========================================
# 英語UIテキスト定義
# ==========================================
t = {
    "app_name": "HoroNote Earth",
    "app_subtitle": "- Horoscope Information Export System -",
    "page_title": "HoroNote Earth",
    "page_subtitle": "- Horoscope Information Export System -",
    "disclaimer": "※ Minor discrepancies in house degrees may occur due to calculation libraries or coordinate settings.",
    "sidebar_header": "📝 Birth Data Input",
    "mode_select": "🔮 Reading Mode",
    "mode_options": ["Single Horoscope", "Synastry (Compatibility)", "Composite", "Transit"],
    "transit_header": "🌌 Transit Settings",
    "p1_header": "Person 1",
    "p2_header": "Person 2",
    "name_input": "Name / Label",
    "birth_date": "Birth Date",
    "birth_time": "Birth Time",
    "pref_select": "Prefecture / Region",
    "pref_default": "Please select a region",
    "city_input": "City / Location Name (e.g. London)",
    "lat_input": "Latitude",
    "lng_input": "Longitude",
    "lat_caption": "💡 Auto-fetched or from Google Maps",
    "settings_header": "⚙️ Display Settings",
    "aspect_view_label": "Aspect View:",
    "aspect_view_options": ["By Pair", "By Aspect"],
    "unknown_time_checkbox": "Unknown Birth Time (Assumed 12:00 / Exclude Houses)",
    "submit_btn": "✨ Create Horoscope",
    "loading": "Calculating planetary positions... 🌌✨",
    "bodies_tab": "🌟 Celestial Bodies",
    "houses_tab": "🏠 12 Houses",
    "aspects_tab": "🔗 Aspects",
    "patterns_tab": "💎 Complex Patterns",
    "invalid_pref_error": "Please select a prefecture/region.",
    "invalid_loc_error": "Please enter a valid location within the prefecture.",
    "welcome_desc": "Please input your birth data and select a reading mode from the sidebar, then click '✨ Create Horoscope'.",
    "mobile_tip": "If you are using a smartphone, tap the `>>` at the top left to open the sidebar.",
    "chart_intro_heading": "📊 Chart Overview",
    "natal_card_title": "🔮 Natal Chart",
    "natal_card_desc": "Explores your core essence, talents, and life themes based on the planetary positions at birth.",
    "syn_card_title": "💕 Synastry (Compatibility)",
    "syn_card_desc": "Compares two charts to analyze relationship compatibility and the energy exchange between two people.",
    "comp_card_title": "☯️ Composite",
    "comp_card_desc": "Merges two birth charts to analyze the shared dynamic, bonds, and partnership theme.",
    "tra_card_title": "🌌 Transit Reading",
    "tra_card_desc": "Examines how current planetary movements interact with your natal chart to reveal present influences.",
    "guide_link_text": "For detailed instructions on how to use this app, [click here](https://note.com/marroscorps/n/ncfc7216cd870)",
    "guide_link_text": "For detailed instructions on how to use this app, [click here](https://note.com/marroscorps/n/ncfc7216cd870)  \n<span style='font-size: 0.85rem; color: #888888;'>(Note: The linked article is in Japanese. Please use your browser's translation feature to read it.)</span>"
}

# ==========================================
# メイン画面のタイトルと注釈を表示
# ==========================================
col1, col2 = st.columns([0.7, 7]) 

with col1:
    st.image("Horo_logo.png", width=50) 

with col2:
    st.markdown(f"""
        <link href="https://fonts.googleapis.com/css2?family=Montserrat:wght@600;700&display=swap" rel="stylesheet">
        
        <style>
            .title-container {{
                display: flex;
                align-items: baseline;
                flex-wrap: wrap;
                margin-bottom: 0.5rem;
                margin-left: -12px;
            }}
            .sub-title {{
                font-size: 1.1rem;
                color: #888888;
                font-weight: 600;
                margin-left: 6px;
            }}

            @media (max-width: 768px) {{
                .title-container {{
                    display: block;
                    margin-left: 0px;
                }}
                .sub-title {{
                    display: block;
                    margin-left: 0px;
                    margin-top: 4px;
                    margin-bottom: 1.2rem; 
                }}
            }}
        </style>

        <div class="title-container">
            <span style="font-size: 2.2rem; font-weight: 700; color: #d8c292; font-family: 'Montserrat', sans-serif;">
                {t['page_title']}
            </span>
            <span class="sub-title">
                {t['page_subtitle']}
            </span>
        </div>
    """, unsafe_allow_html=True)

st.caption(t["disclaimer"])

# ==========================================
# 4. まだ結果が計算されていない初期状態の画面
# ==========================================
if "chart_data" not in st.session_state:
    st.markdown("---")
    st.write(t["welcome_desc"])  # 初期画面の案内文
    st.markdown("") # 少し余白を開ける
    
    # スマホ向けのヒントを分かりやすく表示
    st.info(t["mobile_tip"])
    st.markdown("")
    st.markdown("")

    # 稍微余白を開けて「チャート紹介」の見出しを入れる
    st.markdown("")
    st.markdown(f"### {t['chart_intro_heading']}")
    st.markdown("")
    st.markdown("")

    
    # 縦に4つのモードを順番に配置する
    st.markdown(f"#### {t['natal_card_title']}")
    st.write(t["natal_card_desc"])
    st.markdown("")
    
    st.markdown(f"#### {t['syn_card_title']}")
    st.write(t["syn_card_desc"])
    st.markdown("")
    
    st.markdown(f"#### {t['comp_card_title']}")
    st.write(t["comp_card_desc"])
    st.markdown("")
    
    st.markdown(f"#### {t['tra_card_title']}")
    st.write(t["tra_card_desc"])
    st.markdown("")
    st.markdown("")
    st.markdown("")
    st.markdown("")
    
    st.markdown(t["guide_link_text"], unsafe_allow_html=True)

# 先頭に初期選択肢を追加
PREFECTURES = COUNTRY_OPTIONS

def convert_to_dms(text):
    """
    (16.30°) のような10進数の度数表記を (16°18') の60進数表記に変換する関数
    """
    if not isinstance(text, str):
        text = str(text)

    def replace_deg(match):
        val = float(match.group(1))
        deg = int(val)
        min_val = round((val - deg) * 60)
        if min_val == 60:
            deg += 1
            min_val = 0
        return f"({deg}°{min_val:02d}')"
    
    return re.sub(r'\((\d+\.\d+)°\)', replace_deg, text)

def localize_text(text, lang):
    """
    英語モードの際に、占星術用語（星座、天体、ハウス、アスペクト等）を英語に翻訳する関数
    """
    if lang == "日本語" or not isinstance(text, str):
        return text
    
    translations = {
        # Zodiac Signs
        "牡羊座": "Aries", "牡牛座": "Taurus", "双子座": "Gemini", "蟹座": "Cancer",
        "獅子座": "Leo", "乙女座": "Virgo", "天秤座": "Libra", "蠍座": "Scorpio",
        "射手座": "Sagittarius", "山羊座": "Capricorn", "水瓶座": "Aquarius", "魚座": "Pisces",
        
        # Planets & Points
        "太陽": "Sun", "月": "Moon", "水星": "Mercury", "金星": "Venus",
        "火星": "Mars", "木星": "Jupiter", "土星": "Saturn", "天王星": "Uranus",
        "海王星": "Neptune", "冥王星": "Pluto", "ドラゴンヘッド": "North Node",
        "ドラゴンテイル": "South Node", "キロン": "Chiron",
        
        # Aspects
        "コンジャンクション": "Conjunction", "オポジション": "Opposition",
        "トライン": "Trine", "スクエア": "Square", "セクスタイル": "Sextile",
        "クインカンクス": "Quincunx",
        
        # Dignities
        "ドミサイル": "Domicile", "エグザルテーション": "Exaltation",
        "デトリメント": "Detriment", "フォール": "Fall",
        
        # Misc
        "5度前ルール適用": "5-degree rule applied",
        "出生時間不明のためハウス除外": "Houses excluded due to unknown birth time",
    }
    
    for i in range(12, 0, -1):
        suffix = "st" if i == 1 else "nd" if i == 2 else "rd" if i == 3 else "th"
        translations[f"第{i}ハウス"] = f"{i}{suffix} House"
        
    for jp, en in translations.items():
        text = text.replace(jp, en)
        
    return text

# 💡 1人分の入力フォームを関数化
def render_user_input_form(prefix, default_name, show_header=True):
    if show_header:
        header_text = t["p1_header"] if prefix == "p1" else t["p2_header"]
        st.subheader(header_text)
    
    user_name = st.text_input(t["name_input"], value=default_name, key=f"{prefix}_user_name_input")
    
    default_birth_time = datetime.time(12, 0)
    birth_date = st.date_input(t["birth_date"], value=datetime.date(2000, 1, 1), min_value=datetime.date(1900, 1, 1), max_value=datetime.date(2100, 12, 31), key=f"{prefix}_birth_date_input")
    birth_time = st.time_input(t["birth_time"], value=default_birth_time, key=f"{prefix}_birth_time_input")

    # 🌍 国・州・地域のセレクトボックスに変更

# 2. st.selectbox に placeholder と index=None を指定する
    selected_country = st.selectbox(
        "Country / Region",
        options=GLOBAL_COUNTRIES,
        index=None,  # 最初は何も選択されていない状態にする
        placeholder="Please select a country/region",  # ← これがうっすらとプレースホルダー表示されます！
        key=f"{prefix}_country_select_input"
    )
    
    # 🏙️ 都市名を入力するテキストボックス（例: Tokyo, London など）
    input_city_name = st.text_input(
        t["city_input"], 
        value="London" if prefix == "p1" else "New York", 
        placeholder="e.g., London, Paris, Tokyo", 
        key=f"{prefix}_city_input_global"
    )

    # バリデーションや座標取得の判定
    is_valid = selected_country != country_default and bool(input_city_name.strip())

    if selected_country == country_default:
        st.markdown(f"<p style='color: #ff4b4b; font-size: 0.82em; margin-top: -8px; margin-bottom: 8px;'>⚠️ Please select a country/region.</p>", unsafe_allow_html=True)
    elif not input_city_name.strip():
        st.markdown(f"<p style='color: #ff4b4b; font-size: 0.82em; margin-top: -8px; margin-bottom: 8px;'>⚠️ Please enter a city name.</p>", unsafe_allow_html=True)

    lat_key = f"{prefix}_lat_number_input"
    lng_key = f"{prefix}_lng_number_input"

    # セッションステートの初期値設定
    if f"{prefix}_input_lat_val" not in st.session_state: st.session_state[f"{prefix}_input_lat_val"] = 51.5074
    if f"{prefix}_input_lng_val" not in st.session_state: st.session_state[f"{prefix}_input_lng_val"] = -0.1278

    input_lat = st.number_input(t["lat_input"], value=st.session_state[f"{prefix}_input_lat_val"], format="%.4f", key=lat_key)
    input_lng = st.number_input(t["lng_input"], value=st.session_state[f"{prefix}_input_lng_val"], format="%.4f", key=lng_key)

    st.caption("* Please enter coordinates in decimal degrees")

    return {
        "user_name": user_name,
        "birth_date": birth_date,
        "birth_time": birth_time,
        "selected_country": selected_country,
        "input_city_name": input_city_name,
        "input_lat": input_lat,
        "input_lng": input_lng,
        "is_valid": is_valid
    }

with st.sidebar:
    st.header(t["sidebar_header"])
    
    # 鑑定モードの選択
    chart_mode_raw = st.selectbox(t["mode_select"], t["mode_options"], key="chart_mode_select")
    is_synastry = chart_mode_raw in ["Synastry (Compatibility)"]
    is_composite = chart_mode_raw in ["Composite", "Composite Chart"]
    is_transit = chart_mode_raw in ["Transit"]
    st.markdown("---")

    # 1人目の入力
    p1_data = render_user_input_form("p1", "TestUser1", show_header=is_synastry)

    # 🌟 トランジットモードが選ばれた場合
    if is_transit:
        st.markdown("---")
        st.subheader("🌌 Transit Settings")
        
        import datetime
        from zoneinfo import ZoneInfo
        
        # 💡 日本時間（JST）の現在日時を取得
        jst_now = datetime.datetime.now(ZoneInfo("Asia/Tokyo"))
        
        # フォームの初期値として JST の現在の日付・時間をセット
        transit_date = st.date_input(
            "Transit Date",
            value=jst_now.date(),
            key="transit_date_input"
        )
        
        transit_time = st.time_input(
            "Transit Time",
            value=jst_now.time().replace(second=0, microsecond=0), # 秒・ミリ秒は切り捨てる
            key="transit_time_input"
        )
            
        # 計算用にセッションステートへ保存
        st.session_state["transit_info"] = {
            "year": transit_date.year,
            "month": transit_date.month,
            "day": transit_date.day,
            "hour": transit_time.hour,
            "minute": transit_time.minute,
            "lat": p1_data["input_lat"],
            "lng": p1_data["input_lng"]
        }
        
    # 2人目の入力（シナストリー選択時のみ表示）
    p2_data = None
    if is_synastry or is_composite:
        p2_data = render_user_input_form("p2", "TestUser2", show_header=True)

    # 🌟 ネイタル（単独）のときだけ「表示設定」を表示する
    if not is_synastry and not is_composite and not is_transit:
        st.markdown("---")
        st.header(t["settings_header"])
        toggle_view_raw = st.radio(t["aspect_view_label"], t["aspect_view_options"], key="aspect_view_radio")
        toggle_view = "ペア別" if toggle_view_raw in ["By Pair"] else "アスペクト別"
        unknown_checkbox = st.checkbox(t["unknown_time_checkbox"], key="unknown_time_chk")
    else:
        # ネイタル以外の場合は非表示にしつつ、エラー防止用のデフォルト値を設定
        toggle_view = "ペア別"
        unknown_checkbox = False

    submit_button = st.button(label=t["submit_btn"], type="primary", key="submit_btn_main")
    
    # --- SNSシェアボタンの生成 ---
    share_text = urllib.parse.quote("「HoroNote」- Horoscope Information Export System - #HoroNote")
    app_url = urllib.parse.quote("https://horonote.streamlit.app/#horo-note") # ←公開用URL

    # 各SNS・サービスのシェア用URL
    x_share_url = f"https://twitter.com/intent/tweet?text={share_text}&url={app_url}"
    line_share_url = f"https://social-plugins.line.me/lineit/share?url={app_url}"
    fb_share_url = f"https://www.facebook.com/sharer/sharer.php?u={app_url}"
    bsky_share_url = f"https://bsky.app/intent/compose?text={share_text}%20{app_url}"
    threads_share_url = f"https://threads.net/intent/post?text={share_text}%20{app_url}"
    pinterest_share_url = f"https://pinterest.com/pin/create/button/?url={app_url}&description={share_text}"

    st.markdown(f"""
        <style>
            .share-buttons-grid {{
                display: grid;
                grid-template-columns: repeat(3, 1fr); /* 均等な幅で3列に配置 */
                gap: 6px; /* ボタン同士の隙間 */
                margin-top: 1.2rem;
                margin-bottom: 0.8rem;
            }}
            .share-btn {{
                display: flex;
                align-items: center;
                justify-content: center;
                padding: 6px 2px;
                border-radius: 4px;
                font-size: 0.65rem; /* 長い名称も綺麗に収まるよう文字サイズを調整 */
                font-weight: 600;
                color: #ffffff !important;
                text-decoration: none !important;
                transition: opacity 0.2s;
                text-align: center;
                white-space: nowrap; /* 文字が勝手に改行されないようにする */
            }}
            .share-btn:hover {{
                opacity: 0.85;
            }}
            .btn-x {{ background-color: #000000; border: 1px solid #333; }}
            .btn-line {{ background-color: #06c755; }}
            .btn-fb {{ background-color: #1877f2; }}
            .btn-bsky {{ background-color: #0585ee; }}
            .btn-threads {{ background-color: #101010; border: 1px solid #444; }}
            .btn-pinterest {{ background-color: #e60023; }}
        </style>

        <div style="font-size: 0.8em; color: gray; margin-top: 25px;">↓↓↓ Share Output ↓↓↓</div>
        <div class="share-buttons-grid">
            <a href="{x_share_url}" target="_blank" class="share-btn btn-x">𝕏 Share</a>
            <a href="{line_share_url}" target="_blank" class="share-btn btn-line">LINE</a>
            <a href="{fb_share_url}" target="_blank" class="share-btn btn-fb">Facebook</a>
            <a href="{bsky_share_url}" target="_blank" class="share-btn btn-bsky">Bluesky</a>
            <a href="{threads_share_url}" target="_blank" class="share-btn btn-threads">Threads</a>
            <a href="{pinterest_share_url}" target="_blank" class="share-btn btn-pinterest">Pinterest</a>
        </div>
    """, unsafe_allow_html=True)
    # -----------------------------
    
    # 自分の名義
    st.sidebar.markdown(
        """
        <div style="font-size: 0.85em; color: gray; margin-top: 40px; text-align: left;">
        Producted by marronglace
        """,
        unsafe_allow_html=True
    )
    
if submit_button:
    # バリデーションチェック
    p1_error = False
    if p1_data["selected_pref"] == t["pref_default"]:
        st.error(f"1人目: {t['invalid_pref_error']}")
        p1_error = True
    elif not p1_data["is_valid"] and p1_data["selected_pref"] != "海外・その他":
        st.error(f"1人目: {t['invalid_loc_error']}")
        p1_error = True

    p2_error = False
    if (is_synastry or is_composite) and p2_data:
        if p2_data["selected_pref"] == t["pref_default"]:
            st.error(f"2人目: {t['invalid_pref_error']}")
            p2_error = True
        elif not p2_data["is_valid"] and p2_data["selected_pref"] != "海外・その他":
            st.error(f"2人目: {t['invalid_loc_error']}")
            p2_error = True

    if not p1_error and not p2_error:
        with st.spinner(t["loading"]):
            
            # ── 1. トランジットモードの場合 ──
            if is_transit:
                from horoscope_calc import get_transit_chart_data
                transit_info = st.session_state.get("transit_info", {
                    "year": 2026, "month": 1, "day": 1, "hour": 12, "minute": 0,
                    "lat": p1_data["input_lat"], "lng": p1_data["input_lng"]
                })
                
                data = get_chart_data(
                    p1_data["user_name"],
                    p1_data["birth_date"].year, p1_data["birth_date"].month, p1_data["birth_date"].day,
                    p1_data["birth_time"].hour, p1_data["birth_time"].minute,
                    p1_data["input_lat"], p1_data["input_lng"],
                    p1_data["input_city_name"], lang, toggle_view, unknown_checkbox,
                    transit_info=transit_info
                )
                
                st.session_state.chart_data = data
                st.session_state.user_name = p1_data["user_name"]
                st.session_state.is_synastry = False
                st.session_state.is_composite = False
                st.session_state.is_transit = True
                st.rerun()

            # ── 2. コンポジット（合成図）モードの場合 ──
            elif is_composite:
                data1 = get_chart_data(
                    p1_data["user_name"],
                    p1_data["birth_date"].year, p1_data["birth_date"].month, p1_data["birth_date"].day,
                    p1_data["birth_time"].hour, p1_data["birth_time"].minute,
                    p1_data["input_lat"], p1_data["input_lng"],
                    p1_data["input_city_name"], lang, toggle_view, unknown_checkbox
                )
                
                data2 = get_chart_data(
                    p2_data["user_name"],
                    p2_data["birth_date"].year, p2_data["birth_date"].month, p2_data["birth_date"].day,
                    p2_data["birth_time"].hour, p2_data["birth_time"].minute,
                    p2_data["input_lat"], p2_data["input_lng"],
                    p2_data["input_city_name"], lang, toggle_view, unknown_checkbox
                )
                
                from horoscope_calc import calculate_composite_bodies, calculate_aspects

                # 2つの変数で個別に受け取る
                comp_bodies, comp_aspects = calculate_composite_bodies(data1["bodies_raw"], data2["bodies_raw"])
                
                st.write("📊 計算されたコンポジット天体の詳細データ:", comp_bodies)
                
                st.session_state.chart_data = {
                    "type": "composite", 
                    "bodies": comp_bodies,
                    "aspects": comp_aspects # ここに計算済みの美しいアスペクト文字列が入る
                }
                
                st.session_state.user_name = p1_data["user_name"]
                st.session_state.p2_name = p2_data["user_name"]
                st.session_state.is_composite = True
                st.session_state.is_synastry = False
                st.session_state.is_transit = False
                
                st.rerun()

            # ── 3. シナストリー（相性）モードの場合 ──
            elif is_synastry:
                if get_synastry_data is not None:
                    p1_info = {
                        "name": p1_data["user_name"],
                        "year": p1_data["birth_date"].year, "month": p1_data["birth_date"].month, "day": p1_data["birth_date"].day,
                        "hour": p1_data["birth_time"].hour, "minute": p1_data["birth_time"].minute,
                        "lat": p1_data["input_lat"], "lng": p1_data["input_lng"],
                        "city": p1_data["input_city_name"], "is_unknown_time": unknown_checkbox
                    }
                    p2_info = {
                        "name": p2_data["user_name"],
                        "year": p2_data["birth_date"].year, "month": p2_data["birth_date"].month, "day": p2_data["birth_date"].day,
                        "hour": p2_data["birth_time"].hour, "minute": p2_data["birth_time"].minute,
                        "lat": p2_data["input_lat"], "lng": p2_data["input_lng"],
                        "city": p2_data["input_city_name"], "is_unknown_time": unknown_checkbox
                    }
                    data = get_synastry_data(p1_info, p2_info, mode=lang, display_mode=toggle_view)
                else:
                    data = get_chart_data(
                        f"{p1_data['user_name']} & {p2_data['user_name']}", 
                        p1_data["birth_date"].year, p1_data["birth_date"].month, p1_data["birth_date"].day,
                        p1_data["birth_time"].hour, p1_data["birth_time"].minute, p1_data["input_lat"], p1_data["input_lng"],
                        p1_data["input_city_name"], lang, toggle_view, unknown_checkbox
                    )
                st.session_state.chart_data = data
                st.session_state.user_name = p1_data["user_name"]
                st.session_state.p2_name = p2_data["user_name"]
                st.session_state.is_synastry = True
                st.session_state.is_composite = False
                st.session_state.is_transit = False
                st.rerun()

            # ── 4. シングル（ネイタル）モードの場合 ──
            else:
                data = get_chart_data(
                    p1_data["user_name"],
                    p1_data["birth_date"].year, p1_data["birth_date"].month, p1_data["birth_date"].day,
                    p1_data["birth_time"].hour, p1_data["birth_time"].minute,
                    p1_data["input_lat"], p1_data["input_lng"],
                    p1_data["input_city_name"], lang, toggle_view, unknown_checkbox
                )
                st.session_state.chart_data = data
                st.session_state.user_name = p1_data["user_name"]
                st.session_state.is_synastry = False
                st.session_state.is_composite = False
                st.session_state.is_transit = False
                st.rerun()

# セッションにデータが存在する場合に表示
if "chart_data" in st.session_state:
    data = st.session_state.chart_data
    u_name = st.session_state.get("user_name", "TestUser")
    current_is_synastry = st.session_state.get("is_synastry", False)
    current_is_transit = st.session_state.get("is_transit", False)
    p2_name = st.session_state.get("p2_name", "TestUser2")
    current_is_composite = st.session_state.get("is_composite", False) or (data.get("type") == "composite")

    # ==========================================
    # 🌌 トランジットモードの場合の画面描画
    # ==========================================
    if current_is_transit and "transit" in data:
        st.divider()
        st.subheader("🌌 トランジット分析結果" if lang == "日本語" else "🌌 Transit Reading")
        st.write(f"📅 対象日時: {data['transit'].get('transit_date', '')}")
        st.caption("※ アスペクトはオーブ（誤差）が狭い順（影響が強い順）に並んでいます。")
        
        t_col1, t_col2 = st.columns(2)
        with t_col1:
            st.markdown("### 👤 ネイタル天体配置" if lang == "日本語" else "👤 Natal Bodies")
            for body in data.get("bodies", []):
                st.markdown(f"- {body}", unsafe_allow_html=True)
        with t_col2:
            st.markdown("### 🔗 トランジット・アスペクト" if lang == "日本語" else "🔗 Transit Aspects")
            transit_aspects = data["transit"].get("transit_aspects", [])
            if transit_aspects:
                for asp in transit_aspects:
                    clean_asp = re.sub(r'^[-\s◦○]+', '', str(asp)).strip()
                    st.markdown(f"- {clean_asp}")
            else:
                st.info("現在、顕著なトランジット・アスペクトはありません。" if lang == "日本語" else "No significant transit aspects found.")
        
        st.divider()

        # 📋 ④ 一括コピー欄（トランジット用）
        with st.expander("📋 結果をテキストで一括コピー / Copy All Results"):
            def clean_html(text):
                if not isinstance(text, str):
                    return str(text)
                text = re.sub(r'<[^>]+>', '', text)
                text = text.replace('&nbsp;', '').replace('**', '').replace('`', '')
                return text

            copy_lines = []
            if lang == "日本語":
                copy_lines.append(f"【トランジット鑑定データ: {u_name}】")
                copy_lines.append(f"ネイタル日時: {data.get('date_str', '')}")
                copy_lines.append(f"トランジット日時: {data['transit'].get('transit_date', '')}\n")
                copy_lines.append("[ネイタル天体配置]")
                for b in data.get("bodies", []):
                    copy_lines.append(f"- {clean_html(b)}")
                copy_lines.append("\n[トランジット・アスペクト]")
                if transit_aspects:
                    for asp in transit_aspects:
                        clean_asp = re.sub(r'^[-\s◦○]+', '', clean_html(asp)).strip()
                        copy_lines.append(f"- {clean_asp}")
                else:
                    copy_lines.append("- (特になし)")
            else:
                copy_lines.append(f"[Transit Reading Data: {u_name}]")
                copy_lines.append(f"Natal Date: {data.get('date_str', '')}")
                copy_lines.append(f"Transit Date: {data['transit'].get('transit_date', '')}\n")
                copy_lines.append("[Natal Bodies]")
                for b in data.get("bodies", []):
                    copy_lines.append(f"- {clean_html(b)}")
                copy_lines.append("\n[Transit Aspects]")
                if transit_aspects:
                    for asp in transit_aspects:
                        copy_lines.append(f"- {clean_html(asp)}")
                else:
                    copy_lines.append("- (None)")

            full_text = "\n".join(copy_lines)
            st.code(full_text, language="text")
            
            st.download_button(
                label="💾 テキストファイルとしてダウンロード / Download as text",
                data="\ufeff" + full_text,
                file_name=f"transit_{u_name}.txt",
                mime="text/plain;charset=utf-8"
            )

        # 一番下に追加する note & 質問箱リンク
        st.divider()
        st.markdown(f"""
        <div style="background-color: var(--secondary-background-color); padding: 20px; border-radius: 10px; text-align: center; border: 1px solid var(--border-color);">
        <h3 style="margin-top: 0; color: var(--text-color);">❕ 何かお気づきの点がありましたら</h3>
        <p style="color: var(--text-color);">今回のホロスコープのより詳しい解説は、noteの方で発信しています。</p>
        <a href="https://note.com/marroscorps" target="_blank" style="text-decoration: none; display: inline-block; margin-top: 15px;">
        <button style="background-color: #41d1a7; color: white; border: none; padding: 10px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; width: 290px;">
        noteをチェックする / Visit Note
        </button>
        </a>
        <br><br>
        <p style="color: var(--text-color); margin-bottom: 10px;">匿名での質問も可能です。詳しくは以下からどうぞ</p>
        <a href="https://note.com/qa/marroscorps" target="_blank" style="text-decoration: none; display: inline-block;">
        <button style="background-color: #41d1a7; color: white; border: none; padding: 10px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; width: 290px;">
        匿名で質問する / Ask anonymously
        </button>
        </a>
        </div>
        """, unsafe_allow_html=True)
        st.write("")
        
        st.stop() # トランジットのときはここで通常の描画をストップする

    # ==========================================
    # ☯️ コンポジットモードの場合の画面描画
    # ==========================================
    elif current_is_composite or data.get("type") == "composite":
        st.markdown(f"""
        <div style="padding: 20px; border: 2px solid #D4AF37; border-radius: 12px; background: linear-gradient(135deg, rgba(212,175,55,0.05), rgba(75,0,130,0.05)); text-align: center; margin-bottom: 25px;">
            <h2 style="margin: 0; color: #B8860B;">☯️ {u_name} & {p2_name} のコンポジットチャート</h2>
            <p style="margin: 10px 0 0 0; font-size: 1.1em; color: #555;">2人の出生図を合成したパートナーシップの象徴</p>
        </div>
        """, unsafe_allow_html=True)
        
        # データの取り出し
        bodies = data.get("bodies", [])
        aspects = data.get("aspects", [])
        
        sign_map = {
            "Aries": "牡羊座", "Taurus": "牡牛座", "Gemini": "双子座", "Cancer": "蟹座",
            "Leo": "獅子座", "Virgo": "乙女座", "Libra": "天秤座", "Scorpio": "蠍座",
            "Sagittarius": "射手座", "Capricorn": "山羊座", "Aquarius": "水瓶座", "Pisces": "魚座"
        }
        body_map = {
            "Sun": "太陽", "Moon": "月", "Mercury": "水星", "Venus": "金星",
            "Mars": "火星", "Jupiter": "木星", "Saturn": "土星", "Uranus": "天王星",
            "Neptune": "海王星", "Pluto": "冥王星", "North Node": "ドラゴンヘッド",
            "South Node": "ドラゴンテイル", "Chiron": "キロン"
        }

        # アスペクトを綺麗に整形するヘルパー関数
        def format_aspect_item(asp):
            if isinstance(asp, dict):
                b1 = body_map.get(asp.get("b1", ""), asp.get("b1", "")) if lang == "日本語" else asp.get("b1", "")
                b2 = body_map.get(asp.get("b2", ""), asp.get("b2", "")) if lang == "日本語" else asp.get("b2", "")
                lbl = asp.get("label", "")
                orb = asp.get("orb", 0.0)
                return f"{b1} & {b2} : {lbl} (オーブ: {orb:.1f}°)"
            return str(asp)

        # 左右2カラムで天体位置とアスペクトを並べる
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("#### ■ コンポジット天体位置" if lang == "日本語" else "#### ■ Composite Bodies")
            if bodies and isinstance(bodies, list):
                for body in bodies:
                    if isinstance(body, dict):
                        raw_name = body.get('key', '')
                        raw_sign = body.get('sign', '')
                        deg_val = body.get('degree', 0)
                        
                        d = int(deg_val)
                        m = round((deg_val - d) * 60)
                        if m == 60:
                            d += 1
                            m = 0
                        deg_str = f"{d}°{m:02d}'"
                        
                        disp_name = body_map.get(raw_name, raw_name) if lang == "日本語" else raw_name
                        disp_sign = sign_map.get(raw_sign, raw_sign) if lang == "日本語" else raw_sign
                        
                        st.markdown(f"- **{disp_name}** : {disp_sign} `{deg_str}`")
            else:
                st.info("表示する天体データがありません。" if lang == "日本語" else "No bodies data.")

        with col2:
            st.markdown("#### ■ コンポジット・アスペクト" if lang == "日本語" else "#### ■ Composite Aspects")
            if aspects:
                if isinstance(aspects, str):
                    # **■ を消して、きれいなMarkdownの見出し（####）に変換する
                    formatted_str = aspects.replace("**■ ", "\n#### ").replace("**", "")
                    st.markdown(localize_text(convert_to_dms(formatted_str), lang))
                elif isinstance(aspects, list):
                    for asp in aspects:
                        formatted_asp = format_aspect_item(asp)
                        st.markdown(f"- {localize_text(convert_to_dms(formatted_asp), lang)}")
            else:
                st.info("該当するアスペクトはありません。" if lang == "日本語" else "No aspects found.")

        st.divider()

        # 📋 一括コピー（結果画面の下側）
        with st.expander("📋 結果をテキストで一括コピー / Copy All Results"):
            copy_lines = [f"【コンポジットチャート: {u_name} & {p2_name}】\n", "[コンポジット天体位置]"]
            if bodies and isinstance(bodies, list):
                for body in bodies:
                    if isinstance(body, dict):
                        raw_name = body.get('key', '')
                        raw_sign = body.get('sign', '')
                        deg_val = body.get('degree', 0)
                        d = int(deg_val)
                        m = round((deg_val - d) * 60)
                        if m == 60:
                            d += 1
                            m = 0
                        deg_str = f"{d}°{m:02d}'"
                        
                        disp_name = body_map.get(raw_name, raw_name) if lang == "日本語" else raw_name
                        disp_sign = sign_map.get(raw_sign, raw_sign) if lang == "日本語" else raw_sign
                        copy_lines.append(f"- {disp_name} : {disp_sign} ({deg_str})")
            
            if aspects:
                copy_lines.append("\n[コンポジット・アスペクト]")
                if isinstance(aspects, str):
                    # コピー用テキストからは ** や ■ を完全に削除してスッキリさせる
                    clean_copy_str = aspects.replace("**■ ", "").replace("**", "")
                    copy_lines.append(clean_copy_str)
                elif isinstance(aspects, list):
                    for asp in aspects:
                        formatted_asp = format_aspect_item(asp)
                        copy_lines.append(f"- {formatted_asp}")
            
            full_text = "\n".join(copy_lines)
            st.code(full_text, language="text")
            st.download_button(
                label="💾 テキストファイルとしてダウンロード / Download as text",
                data="\ufeff" + full_text,
                file_name=f"composite_{u_name}_{p2_name}.txt",
                mime="text/plain;charset=utf-8"
            )

        # ==========================================
        # 🌟 ここから下が「一番下に追加する note & 質問箱リンク」です！
        # ==========================================
        st.divider()
        st.markdown(f"""
        <div style="background-color: var(--secondary-background-color); padding: 20px; border-radius: 10px; text-align: center; border: 1px solid var(--border-color);">
        <h3 style="margin-top: 0; color: var(--text-color);">❕ 何かお気づきの点がありましたら</h3>
        <p style="color: var(--text-color);">今回のホロスコープのより詳しい解説は、noteの方で発信しています。</p>
        <a href="https://note.com/marroscorps" target="_blank" style="text-decoration: none; display: inline-block; margin-top: 15px;">
        <button style="background-color: #41d1a7; color: white; border: none; padding: 10px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; width: 290px;">
        noteをチェックする / Visit Note
        </button>
        </a>
        <br><br>
        <p style="color: var(--text-color); margin-bottom: 10px;">匿名での質問も可能です。詳しくは以下からどうぞ</p>
        <a href="https://note.com/qa/marroscorps" target="_blank" style="text-decoration: none; display: inline-block;">
        <button style="background-color: #41d1a7; color: white; border: none; padding: 10px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; width: 290px;">
        匿名で質問する / Ask anonymously
        </button>
        </a>
        </div>
        """, unsafe_allow_html=True)
        st.write("")
        
        st.stop()

    if not current_is_synastry:
        display_loc_str = data['loc_str']
        if lang != "日本語":
            display_loc_str = (
                display_loc_str
                .replace("北緯", "N")
                .replace("東経", "E")
                .replace("十進:", "Decimal:")
            )

        st.markdown(f"""
        <div style="padding: 20px; border: 2px solid #D4AF37; border-radius: 12px; background: linear-gradient(135deg, rgba(212,175,55,0.05), rgba(75,0,130,0.05)); text-align: center; margin-bottom: 25px;">
            <h2 style="margin: 0; color: #B8860B;">✨ {u_name} {"さんのホロスコープ" if lang=="日本語" else "'s Horoscope Reading"} ✨</h2>
            <p style="margin: 10px 0 0 0; font-size: 1.1em; color: #555;">📅 {data['date_str']}<br>📍 {display_loc_str}</p>
        </div>
        """, unsafe_allow_html=True)

        if data["angles"]:
            col_a1, col_a2 = st.columns(2)
            col_a1.info(localize_text(convert_to_dms(data["angles"][0]), lang))
            col_a2.info(localize_text(convert_to_dms(data["angles"][1]), lang))
            st.write("")

        # タブの作成（全6タブ）
        ruler_tab_label = "ハウスルーラー" if lang == "日本語" else "House Rulers"
        midpoint_tab_label = "ミッドポイント" if lang == "日本語" else "Midpoints"
        tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
            t["bodies_tab"], t["houses_tab"], t["aspects_tab"], 
            t["patterns_tab"], ruler_tab_label, midpoint_tab_label
        ])

        with tab1:
            for p in data["bodies"]:
                st.markdown(f"- {localize_text(convert_to_dms(p), lang)}", unsafe_allow_html=True)

        with tab2:
            for h in data["houses"]:
                st.markdown(f"- {localize_text(convert_to_dms(h), lang)}")

        with tab3:
            converted_aspects = localize_text(convert_to_dms(data["aspects"]), lang)
            aspect_lines = [l.strip() for l in converted_aspects.strip().split("\n") if l.strip()]
            
            current_view_raw = st.session_state.get("aspect_view_radio", "ペア別")
            is_by_aspect = current_view_raw in ["アスペクト別", "By Aspect"]

            if is_by_aspect:
                # 🔗【アスペクト別】の場合
                for i, line in enumerate(aspect_lines):
                    if line.startswith("■"):
                        clean_heading = line.replace("■", "").strip()
                        # 2つ目以降の見出しの前に、余白（空行）を挟む
                        if i > 0:
                            st.markdown("") 
                        st.markdown(f"#### 🔗 {clean_heading}")
                    else:
                        st.markdown(line)
            else:
                # 🌟【ペア別】の場合
                current_planet = None
                for line in aspect_lines:
                    if " & " in line:
                        raw_target = line.lstrip("-* ").strip()
                        planet = raw_target.split(" & ")[0].strip()
                        if planet != current_planet:
                            current_planet = planet
                            heading_prefix = "Aspects of" if lang != "日本語" else "のアスペクト"
                            st.markdown(f"\n#### 🌟 {current_planet} {heading_prefix}")
                    st.markdown(line)

        with tab4:
            if data["patterns"]:
                for pat in data["patterns"]:
                    st.success(localize_text(convert_to_dms(pat), lang))
            else:
                st.info("*(該当する複合アスペクトはありません)*" if lang=="日本語" else "*(No complex aspects found)*")

        with tab5:
            if data.get("house_rulers"):
                ruler_mode_options = (
                    ["5度前ルール適用なし", "5度前ルール適用あり"] 
                    if lang == "日本語" 
                    else ["Without 5-degree rule", "With 5-degree rule"]
                )
                ruler_mode_label = "表示モードを選択" if lang == "日本語" else "Select Display Mode"
                
                ruler_mode = st.radio(
                    ruler_mode_label,
                    ruler_mode_options,
                    key="ruler_mode_radio"
                )
                st.write("")

                is_without_5deg = ruler_mode in ["5度前ルール適用なし", "Without 5-degree rule"]

                if is_without_5deg:
                    target_rulers = data.get("house_rulers", [])
                else:
                    target_rulers = data.get(
                        "house_rulers_with_5deg", data.get("house_rulers", [])
                    )

                for r_line in target_rulers:
                    # 計算側で作成された文字列をそのまま活かす
                    formatted_line = r_line.replace("->", "→").replace("➡️", "→").strip()
                    
                    # 2ハウス間のミューチュアル・レセプションの判定と表示用の置換
                    mutual_match = re.search(r'(第\d+ハウス) → (第\d+ハウス) → \1', formatted_line)
                    
                    if mutual_match:
                        h1 = mutual_match.group(1)
                        h2 = mutual_match.group(2)
                        match_end = mutual_match.end()
                        loop_part = formatted_line[:match_end]
                        
                        n1 = int(re.search(r'\d+', h1).group())
                        n2 = int(re.search(r'\d+', h2).group())
                        min_n, max_n = min(n1, n2), max(n1, n2)
                        
                        if lang == "日本語":
                            formatted_line = f"{loop_part} (第{min_n}ハウス・第{max_n}ハウスのミューチュアル・レセプション)"
                        else:
                            formatted_line = f"{loop_part} (Mutual Reception between {min_n}th and {max_n}th Houses)"

                    formatted_line = localize_text(formatted_line, lang)
                    st.markdown(f"- {formatted_line}")
            else:
                st.info("*(出生時間不明のためハウスルーラー除外)*" if lang == "日本語" else "*(House rulers excluded due to unknown birth time)*")
                
        with tab6:
            st.caption("※1 主要な感受点・軸に対するミッドポイント・ヒット（オーブ1.5°以内）を表示します。" if lang=="日本語" else "*1 Displays midpoint hits to major points/axes (orb within 1.5°).")
            st.caption("※2 出生時間不明の場合、月・Asc・Mcを含む組み合わせは除外してあります。" if lang == "日本語" else "*2 Combinations including Moon, Asc, and MC are excluded if birth time is unknown.")
            midpoints_data = data.get("midpoints", [])
            if midpoints_data:
                for m_line in midpoints_data:
                    clean_m = m_line.lstrip("- ").strip()
                    st.markdown(f"- {localize_text(clean_m, lang)}")
            else:
                st.info("*(該当するミッドポイントデータはありません)*" if lang=="日本語" else "*(No midpoint data)*")

        st.divider()

        with st.expander("📋 結果をテキストで一括コピー / Copy All Results"):
            u_name = st.session_state.get("user_name", "TestUser")
            
            hide_dt_loc = st.checkbox(
                "日時と場所を非表示にする（除外する）" if lang == "日本語" else "Exclude Date, Time & Location",
                value=False,
                key="copy_hide_dt_loc"
            )
            
            def clean_html(text):
                if not isinstance(text, str):
                    return str(text)
                text = re.sub(r'<[^>]+>', '', text)
                text = text.replace('&nbsp;', '')
                text = text.replace('**', '').replace('`', '')
                text = localize_text(text, lang)
                return text

            # --- ★ ハウスルーラーを綺麗に整形する共通関数 ---
            def clean_and_format_ruler(r_line, current_lang):
                cleaned = clean_html(r_line).replace("->", "→").replace("➡️", "→").strip()
                cleaned = cleaned.lstrip("-").strip()
                
                # 先頭の「第〇ハウス」を確実に抽出
                prefix_match = re.search(r'(第\d+ハウス)', cleaned)
                prefix = prefix_match.group(1) if prefix_match else "第1ハウス"
                
                separator = "：" if current_lang == "日本語" else ": "

                # ミューチュアル・レセプションの判定（コピー用）
                mutual_match = re.search(r'(第\d+ハウス) → (第\d+ハウス) → \1', cleaned)
                
                if mutual_match:
                    h1 = mutual_match.group(1)
                    h2 = mutual_match.group(2)
                    match_end = mutual_match.end()
                    loop_part = cleaned[:match_end]
                    
                    n1 = int(re.search(r'\d+', h1).group())
                    n2 = int(re.search(r'\d+', h2).group())
                    min_n, max_n = min(n1, n2), max(n1, n2)
                    
                    if current_lang == "日本語":
                        cleaned = f"{loop_part} (第{min_n}ハウス・第{max_n}ハウスのミューチュアル・レセプション)"
                    else:
                        # 英語化が必要な場合の調整
                        cleaned = f"{loop_part} (Mutual Reception between {min_n}th and {max_n}th Houses)"
                else:
                    # すでにコロンが含まれている場合（第9ハウスのドミサイルなど）
                    if "：" in cleaned or ":" in cleaned:
                        parts = re.split(r'[：:]', cleaned, 1)
                        if len(parts) == 2:
                            b_part = parts[1].strip()
                            formatted_line = f"{prefix}{separator}{b_part}"
                        else:
                            formatted_line = f"{prefix}{separator}{cleaned}"
                    else:
                        # コロンがない通常ラインの場合
                        formatted_line = f"{prefix}{separator}{cleaned}"

                return localize_text(cleaned, current_lang)

            copy_lines = []
            if lang == "日本語":
                copy_lines.append(f"【ホロスコープ鑑定データ: {u_name}】")
                
                if not hide_dt_loc:
                    copy_lines.append(f"日時: {data['date_str']}")
                    copy_lines.append(f"場所: {data['loc_str']}\n")
                else:
                    copy_lines.append("")

                if data["angles"]:
                    copy_lines.append("[アングル]")
                    for a in data["angles"]:
                        copy_lines.append(f"- {clean_html(a)}")
                    copy_lines.append("")
                
                copy_lines.append("[天体配置]")
                for b in data["bodies"]:
                    clean_b = clean_html(b)
                    clean_b = clean_b.replace("↳", " ↳ ")
                    copy_lines.append(f"- {clean_b}")
                    
                copy_lines.append("\n[12ハウス]")
                for h in data["houses"]:
                    copy_lines.append(f"- {clean_html(h)}")

                if data.get("house_rulers"):
                    ruler_mode = st.session_state.get("ruler_mode_radio", "5度前ルール適用なし")
                    copy_lines.append(f"\n[ハウスルーラー（{ruler_mode}）]")
                    
                    is_without = ruler_mode in ["5度前ルール適用なし", "Without 5-degree rule"]
                    target_rulers_for_copy = (
                        data.get("house_rulers", []) 
                        if is_without 
                        else data.get("house_rulers_with_5deg", data.get("house_rulers", []))
                    )
                    
                    for r_line in target_rulers_for_copy:
                        # ★ ここで共通関数を使って綺麗に整形する
                        formatted_r = clean_and_format_ruler(r_line, "日本語")
                        copy_lines.append(f"- {formatted_r}")

                copy_lines.append("\n[主要アスペクト]")
                clean_aspects = clean_html(data["aspects"]).replace("■ ", "")
                copy_lines.append(clean_aspects)

                if data["patterns"]:
                    copy_lines.append("\n[複合アスペクト]")
                    for pat in data["patterns"]:
                        copy_lines.append(f"- {clean_html(pat)}")

                midpoints_data = data.get("midpoints", [])
                if midpoints_data:
                    copy_lines.append("\n[ミッドポイント]")
                    for m_line in midpoints_data:
                        clean_m = clean_html(m_line).lstrip("- ").strip()
                        copy_lines.append(f"- {clean_m}")
            else:
                # 英語モードの処理
                copy_lines.append(f"[Horoscope Reading Data: {u_name}]")
                
                if not hide_dt_loc:
                    copy_lines.append(f"Date & Time: {data['date_str']}")
                    copy_lines.append(f"Location: {display_loc_str}\n")
                else:
                    copy_lines.append("")

                if data["angles"]:
                    copy_lines.append("[Angles]")
                    for a in data["angles"]:
                        copy_lines.append(f"- {clean_html(a)}")
                    copy_lines.append("")
                
                copy_lines.append("[Celestial Bodies]")
                for b in data["bodies"]:
                    clean_b = clean_html(b)
                    clean_b = clean_b.replace("↳", " ↳ ")
                    copy_lines.append(f"- {clean_b}")
                    
                copy_lines.append("\n[12 Houses]")
                for h in data["houses"]:
                    copy_lines.append(f"- {clean_html(h)}")

                if data.get("house_rulers"):
                    ruler_mode_raw = st.session_state.get("ruler_mode_radio", "Without 5-degree rule")
                    ruler_mode_en = "Without 5-degree rule" if ruler_mode_raw in ["5度前ルール適用なし", "Without 5-degree rule"] else "With 5-degree rule"
                    
                    copy_lines.append(f"\n[House Rulers ({ruler_mode_en})]")
                    
                    is_without = ruler_mode_raw in ["5度前ルール適用なし", "Without 5-degree rule"]
                    target_rulers_for_copy = (
                        data.get("house_rulers", []) 
                        if is_without 
                        else data.get("house_rulers_with_5deg", data.get("house_rulers", []))
                    )
                    
                    for r_line in target_rulers_for_copy:
                        # ★ 英語モード用の共通関数呼び出し
                        formatted_r = clean_and_format_ruler(r_line, "英語")
                        copy_lines.append(f"- {formatted_r}")

                copy_lines.append("\n[Main Aspects]")
                clean_aspects = clean_html(data["aspects"]).replace("■ ", "")
                copy_lines.append(clean_aspects)

                if data["patterns"]:
                    copy_lines.append("\n[Complex Patterns]")
                    for pat in data["patterns"]:
                        copy_lines.append(f"- {clean_html(pat)}")

                midpoints_data = data.get("midpoints", [])
                if midpoints_data:
                    copy_lines.append("\n[Midpoints]")
                    for m_line in midpoints_data:
                        clean_m = clean_html(m_line).lstrip("- ").strip()
                        copy_lines.append(f"- {clean_m}")

            st.code("\n".join(copy_lines), language="text")
            
            full_text = "\n".join(copy_lines)
            boms_text = "\ufeff" + full_text
            
            st.download_button(
                label="💾 テキストファイルとしてダウンロード / Download as text",
                data=boms_text,
                file_name=f"horoscope_{u_name}.txt",
                mime="text/plain;charset=utf-8"
            )
        
        # ==========================================
        # 🌟 ここから下が「一番下に追加する note & 質問箱リンク」です！
        # ==========================================
        st.divider()
        
        st.markdown(f"""
        <div style="background-color: var(--secondary-background-color); padding: 20px; border-radius: 10px; text-align: center; border: 1px solid var(--border-color);">
        <h3 style="margin-top: 0; color: var(--text-color);">❕ 何かお気づきの点がありましたら</h3>
        <p style="color: var(--text-color);">今回のホロスコープのより詳しい解説は、noteの方で発信しています。</p>
        <a href="https://note.com/marroscorps" target="_blank" style="text-decoration: none; display: inline-block; margin-top: 15px;">
        <button style="background-color: #41d1a7; color: white; border: none; padding: 10px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; width: 290px;">
        noteをチェックする / Visit Note
        </button>
        </a>
        <br><br>
        <p style="color: var(--text-color); margin-bottom: 10px;">匿名での質問も可能です。詳しくは以下からどうぞ</p>
        <a href="https://note.com/qa/marroscorps" target="_blank" style="text-decoration: none; display: inline-block;">
        <button style="background-color: #41d1a7; color: white; border: none; padding: 10px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; width: 290px;">
        匿名で質問する / Ask anonymously
        </button>
        </a>
        </div>
        """, unsafe_allow_html=True)
        st.write("")

    else:
        # 🌟 シナストリーモード用の表示（左右に分ける）
        st.markdown(f"""
        <div style="padding: 20px; border: 2px solid #D4AF37; border-radius: 12px; background: linear-gradient(135deg, rgba(212,175,55,0.05), rgba(75,0,130,0.05)); text-align: center; margin-bottom: 25px;">
            <h2 style="margin: 0; color: #B8860B;">✨ {u_name} & {p2_name} {"のシナストリー鑑定" if lang=="日本語" else "'s Synastry Reading"} ✨</h2>
        </div>
        """, unsafe_allow_html=True)

        synastry_tabs_labels = (
            ["🌟 2人分の天体配置", "🔗 2人分のアスペクト比較"] 
            if lang == "日本語" 
            else ["🌟 Celestial Bodies", "🔗 Aspects Comparison"]
        )
        stab1, stab2 = st.tabs(synastry_tabs_labels)

        with stab1:
            col_l, col_r = st.columns(2)
            with col_l:
                st.markdown(f"#### 👤 {u_name}")
                p1_bodies = data.get("person1", {}).get("bodies", data.get("bodies", []))
                for p in p1_bodies:
                    st.markdown(f"- {localize_text(convert_to_dms(p), lang)}", unsafe_allow_html=True)
            with col_r:
                st.markdown(f"#### 👤 {p2_name}")
                p2_bodies = data.get("person2", {}).get("bodies", data.get("person2_bodies", []))
                for p in p2_bodies:
                    st.markdown(f"- {localize_text(convert_to_dms(p), lang)}", unsafe_allow_html=True)
        with stab2:
            st.markdown(f"#### 🔗 {u_name} & {p2_name} のシナストリー・アスペクト" if lang=="日本語" else f"#### 🔗 Synastry Aspects between {u_name} & {p2_name}")
            
            # 各種キーのバリエーションに対応して取得
            synastry_aspects = (
                data.get("synastry_aspects") or 
                data.get("person1_to_person2_aspects") or 
                data.get("aspects") or 
                []
            )
            
            if synastry_aspects and synastry_aspects is not Ellipsis:
                if isinstance(synastry_aspects, str):
                    lines = [l.strip() for l in synastry_aspects.split("\n") if l.strip()]
                elif isinstance(synastry_aspects, list):
                    lines = []
                    for item in synastry_aspects:
                        if item is not Ellipsis and str(item) != "Ellipsis":
                            if isinstance(item, str):
                                lines.extend([l.strip() for l in item.split("\n") if l.strip()])
                            else:
                                lines.append(str(item))
                else:
                    lines = [str(synastry_aspects)]

                valid_lines = [l for l in lines if l and str(l) != "Ellipsis"]
                if valid_lines:
                    for line in valid_lines:
                        converted_line = localize_text(convert_to_dms(line), lang)
                        st.markdown(converted_line if converted_line.startswith("-") else f"- {converted_line}")
                else:
                    st.info("*(該当するアスペクトはありません)*" if lang=="日本語" else "*(No synastry aspects found)*")
            else:
                st.info("*(データなし)*" if lang=="日本語" else "*(No data)*")

        st.divider()

        with st.expander("📋 結果をテキストで一括コピー / Copy All Results"):
            def clean_html(text):
                if not isinstance(text, str):
                    return str(text)
                text = re.sub(r'<[^>]+>', '', text)
                text = text.replace('&nbsp;', '')
                text = text.replace('**', '').replace('`', '')
                text = localize_text(text, lang)
                return text

            copy_lines = []
            if lang == "日本語":
                copy_lines.append(f"【シナストリー鑑定データ: {u_name} & {p2_name}】\n")
                
                copy_lines.append(f"--- 👤 {u_name} の天体配置 ---")
                p1_bodies = data.get("person1", {}).get("bodies", data.get("bodies", []))
                for p in p1_bodies:
                    copy_lines.append(f"- {clean_html(convert_to_dms(p))}")

                copy_lines.append(f"\n--- 👤 {p2_name} の天体配置 ---")
                p2_bodies = data.get("person2", {}).get("bodies", data.get("person2_bodies", []))
                for p in p2_bodies:
                    copy_lines.append(f"- {clean_html(convert_to_dms(p))}")

                copy_lines.append(f"\n--- 🔗 シナストリー・アスペクト ---")
                synastry_aspects = (
                    data.get("synastry_aspects") or 
                    data.get("person1_to_person2_aspects") or 
                    data.get("aspects") or 
                    []
                )
                if isinstance(synastry_aspects, list):
                    for a in synastry_aspects:
                        if a is not Ellipsis and str(a) != "Ellipsis":
                            copy_lines.append(f"- {clean_html(convert_to_dms(a))}")
                elif isinstance(synastry_aspects, str):
                    for line in synastry_aspects.split("\n"):
                        if line.strip():
                            copy_lines.append(f"- {clean_html(convert_to_dms(line))}")
            else:
                # 英語用の出力も同様にシナストリー・アスペクトを反映
                copy_lines.append(f"[Synastry Reading Data: {u_name} & {p2_name}]\n")
                
                copy_lines.append(f"--- 👤 {u_name}'s Celestial Bodies ---")
                p1_bodies = data.get("person1", {}).get("bodies", data.get("bodies", []))
                for p in p1_bodies:
                    copy_lines.append(f"- {clean_html(convert_to_dms(p))}")
                
                copy_lines.append(f"\n--- 👤 {u_name}'s Aspects ---")
                p1_aspects = data.get("person1", {}).get("aspects", data.get("person1_aspects", data.get("aspects", [])))
                if isinstance(p1_aspects, list):
                    for a in p1_aspects:
                        if a is not Ellipsis and str(a) != "Ellipsis":
                            copy_lines.append(f"- {clean_html(convert_to_dms(a))}")
                elif isinstance(p1_aspects, str):
                    for line in p1_aspects.split("\n"):
                        if line.strip():
                            copy_lines.append(f"- {clean_html(convert_to_dms(line))}")

                copy_lines.append(f"\n--- 👤 {p2_name}'s Celestial Bodies ---")
                p2_bodies = data.get("person2", {}).get("bodies", data.get("person2_bodies", []))
                for p in p2_bodies:
                    copy_lines.append(f"- {clean_html(convert_to_dms(p))}")

                copy_lines.append(f"\n--- 👤 {p2_name}'s Aspects ---")
                p2_aspects = data.get("person2", {}).get("aspects", data.get("person2_aspects", []))
                if isinstance(p2_aspects, list):
                    for a in p2_aspects:
                        if a is not Ellipsis and str(a) != "Ellipsis":
                            copy_lines.append(f"- {clean_html(convert_to_dms(a))}")
                elif isinstance(p2_aspects, str):
                    for line in p2_aspects.split("\n"):
                        if line.strip():
                            copy_lines.append(f"- {clean_html(convert_to_dms(line))}")

            st.code("\n".join(copy_lines), language="text")
            
            full_text = "\n".join(copy_lines)
            boms_text = "\ufeff" + full_text
            
            st.download_button(
                label="💾 テキストファイルとしてダウンロード / Download as text",
                data=boms_text,
                file_name=f"synastry_{u_name}_{p2_name}.txt",
                mime="text/plain;charset=utf-8"
            )
            
        # ==========================================
        # 🌟 ここから下が「一番下に追加する note & 質問箱リンク」です！
        # ==========================================
        st.divider()
        
        st.markdown(f"""
        <div style="background-color: var(--secondary-background-color); padding: 20px; border-radius: 10px; text-align: center; border: 1px solid var(--border-color);">
        <h3 style="margin-top: 0; color: var(--text-color);">❕ 何かお気づきの点がありましたら</h3>
        <p style="color: var(--text-color);">今回のホロスコープのより詳しい解説は、noteの方で発信しています。</p>
        <a href="https://note.com/marroscorps" target="_blank" style="text-decoration: none; display: inline-block; margin-top: 15px;">
        <button style="background-color: #41d1a7; color: white; border: none; padding: 10px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; width: 290px;">
        noteをチェックする / Visit Note
        </button>
        </a>
        <br><br>
        <p style="color: var(--text-color); margin-bottom: 10px;">匿名での質問も可能です。詳しくは以下からどうぞ</p>
        <a href="https://note.com/qa/marroscorps" target="_blank" style="text-decoration: none; display: inline-block;">
        <button style="background-color: #41d1a7; color: white; border: none; padding: 10px 20px; border-radius: 8px; font-weight: bold; cursor: pointer; width: 290px;">
        匿名で質問する / Ask anonymously
        </button>
        </a>
        </div>
        """, unsafe_allow_html=True)
        st.write("")
