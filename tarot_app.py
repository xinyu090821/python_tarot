import streamlit as st
import random
import json
import os
import base64  # 用於將圖片轉換為網頁內嵌編碼
from google import genai  # 引入 Gemini AI 套件
from PIL import Image, ImageDraw, ImageFont
import io
import urllib.parse

# ================= 1. 讀取 JSON 資料庫 =================
@st.cache_data
def load_tarot_data():
    json_path = "tarot_data.json" 
    if not os.path.exists(json_path):
        st.error(f"找不到 {json_path} 檔案，請確認檔案是否放在同一個資料夾中。")
        return {}
    with open(json_path, "r", encoding="utf-8") as f:
        return json.load(f)

tarot_db = load_tarot_data()

# --- 2. 初始化 Session State (狀態管理) ---
if 'is_setup' not in st.session_state:
    st.session_state.is_setup = False      # 是否填完名字與問題
if 'chosen_indices' not in st.session_state:
    st.session_state.chosen_indices = []   # 使用者點選了哪幾個牌背的索引
if 'drawn_results' not in st.session_state:
    st.session_state.drawn_results = None  # 儲存最終抽出的三張牌的數據

# ================= 3. 網頁標題與說明 =================
st.set_page_config(page_title="專屬互動塔羅占卜", page_icon="🔮", layout="wide") # wide 模式展開整排牌組

# ==================== 🪄 全域魔幻背景與按鈕優化 CSS ====================
st.markdown("""
    <style>
    /* 1. 核心修正：唯獨在最底層容器套用漸層，創造滑順的單一星空大背景 */
    div[data-testid="stAppViewContainer"] {
        background: linear-gradient(135deg, #0a0716 0%, #251545 50%, #080a18 100%) !important;
    }
    
    /* 2. 關鍵透明化：強迫 Streamlit 所有上層包裝盒、主區塊、欄位容器全面變透明，把底層漸層完美透上來 */
    .stApp, section.main, div[data-testid="stHeader"], div[data-testid="stBlockContainer"], div[data-testid="stVerticalBlock"] {
        background: transparent !important;
        background-color: transparent !important;
        color: #f0e6ff !important;
    }
    
    /* 3. 讓輸入框的標題和提示文字更清晰美麗 */
    .stTextInput label p, .stSelectbox label p, .stSubheader p, h3 {
        color: #e2d5ff !important;
        font-weight: bold !important;
        text-shadow: 0px 0px 8px rgba(187, 134, 252, 0.6);
    }

    /* 4. 讓一般操作按鈕（連結能量、重新占卜、下載）變身為清晰高對比的魔幻發光按鈕 */
    div.stButton > button {
        background: linear-gradient(90deg, #4b1a7a 0%, #631f9a 100%) !important; 
        color: #ffffff !important; 
        border: 1px solid #9d4edd !important; 
        font-weight: bold !important;
        border-radius: 8px !important;
        box-shadow: 0px 4px 12px rgba(157, 78, 221, 0.4) !important; 
        transition: all 0.25s ease-in-out !important;
    }

    /* 一般按鈕滑鼠懸停（Hover）特效 */
    div.stButton > button:hover {
        background: linear-gradient(90deg, #631f9a 0%, #7b2cbf 100%) !important;
        box-shadow: 0px 4px 20px rgba(187, 134, 252, 0.8) !important; 
        color: #ffffff !important;
        transform: translateY(-2px); 
    }
    </style>
""", unsafe_allow_html=True)
# =====================================================================

st.title("🔮 專屬互動塔羅占卜網頁")
st.write("結合現代網頁架構與外掛資料庫設計，為你量身打造的命運解答。")

# ================= 4. 使用者設定介面 =================
st.write("---")
col_input_a, col_input_b, col_input_c = st.columns([1.2, 2, 1.5])
with col_input_a:
    name = st.text_input("請輸入你的名字：", placeholder="例如：Shona")
with col_input_b:
    question = st.text_input("請輸入你想占卜的問題：", placeholder="例如：期末報告會順利度過嗎？")
with col_input_c:
    teller_style = st.selectbox(
        "🔮 選擇占卜分析風格：",
        ["溫柔心靈導師", "理性邏輯分析師", "古典塔羅解讀師", "客觀專業占卜師"]
    )

if st.button("🔮 連結宇宙能量..."):
    if name and question:
        st.session_state.is_setup = True
        st.session_state.chosen_indices = []
        st.session_state.drawn_results = None
        st.success(f"Hi {name}，宇宙已準備就緒。將以【{teller_style}】視角為你解鎖訊息。")
    else:
        st.warning("⚠️ 請先填寫「名字」與「占卜問題」，宇宙才能幫你感應牌陣喔！")

# ================= 💥 核心核心：卡牌本人直接點選＋扇形重疊盲選邏輯 =================
if st.session_state.is_setup and st.session_state.drawn_results is None:
    st.write("---")
    st.markdown("### 🃏 **請憑直覺從牌組中點選三張牌**")
    
    cards_left = 3 - len(st.session_state.chosen_indices)
    if cards_left > 0:
        st.info(f"✨ 專注於你的問題... 目前已選擇 {len(st.session_state.chosen_indices)} 張，還需要點選 {cards_left} 張")
    
    img_dir = os.path.join(os.path.dirname(__file__), "images")
    card_back_path = os.path.join(img_dir, "card_back.png")
    if not os.path.exists(card_back_path):
        card_back_path = os.path.join(img_dir, "card_back.jpg")
        
    card_back_b64 = ""
    if os.path.exists(card_back_path):
        with open(card_back_path, "rb") as img_file:
            card_back_b64 = base64.b64encode(img_file.read()).decode()
        
    st.markdown(f"""
        <style>
        div[data-testid="stHorizontalBlock"]:has(button) {{ gap: 0px !important; }}
        div[data-testid="stHorizontalBlock"]:has(button) div[data-testid="stColumn"] {{
            margin-right: -28px !important;   
            transition: transform 0.25s ease-in-out, z-index 0.2s;
            position: relative;
        }}
        div[data-testid="stHorizontalBlock"]:has(button) div[data-testid="stColumn"] div.stButton > button {{
            background: none !important;
            background-image: url(data:image/png;base64,{card_back_b64}) !important;
            background-size: 100% 100% !important;
            background-repeat: no-repeat !important;
            background-position: center !important;
            background-color: #2D2D44 !important; 
            border: 1px solid rgba(255, 215, 0, 0.3) !important; 
            height: 140px !important;  
            width: 100% !important;
            padding: 0 !important;
            box-shadow: -4px 4px 10px rgba(0, 0, 0, 0.5) !important; 
            border-radius: 6px !important;
            transform: none !important;
        }}
        div[data-testid="stHorizontalBlock"]:has(button) div[data-testid="stColumn"]:hover {{
            transform: translateY(-25px) !important;     
            z-index: 9999 !important;          
        }}
        div[data-testid="stHorizontalBlock"]:has(button) div[data-testid="stColumn"] div.stButton > button:disabled {{
            filter: brightness(0.6) !important; 
        }}
        div[data-testid="stHorizontalBlock"]:has(button) div[data-testid="stColumn"] div.stButton > button:disabled p {{
            color: #00FF00 !important;
            font-size: 26px !important;
            font-weight: bold !important;
            background-color: rgba(0, 0, 0, 0.5) !important; 
            width: 100% !important;
            height: 100% !important;
            display: flex !important;
            align-items: center !important;
            justify-content: center !important;
            margin: 0 !important;
            border-radius: 6px !important;
        }}
        </style>
    """, unsafe_allow_html=True)
        
    cols_count = 26
    cols = st.columns(cols_count)
    
    for i in range(cols_count):
        with cols[i]:
            button_key = f"card_back_btn_{i}"
            if i in st.session_state.chosen_indices:
                st.button("✅", key=button_key, disabled=True, use_container_width=True)
            else:
                if st.button(" ", key=button_key, use_container_width=True):
                    if len(st.session_state.chosen_indices) < 3:
                        st.session_state.chosen_indices.append(i)
                        st.balloons() 
                        if len(st.session_state.chosen_indices) == 3:
                            with st.spinner(f"✨ 三張卡牌已集齊！正在連結【{teller_style}】解析中..."):
                                drawn_cards = random.sample(list(tarot_db.keys()), 3)
                                directions = [random.choice(["正位", "逆位"]) for _ in range(3)]
                                st.session_state.drawn_results = {
                                    "name": name,
                                    "question": question,
                                    "cards": drawn_cards,
                                    "directions": directions,
                                    "time_labels": ["⬅️ 過去 (Past)", "⬇️ 現在 (Present)", "➡️ 未來 (Future)"],
                                    "teller_style": teller_style
                                }
                        st.rerun()

    st.write("---")
    
# ================= 5. 顯示解牌結果 =================
if st.session_state.drawn_results:
    res = st.session_state.drawn_results
    current_style = res.get("teller_style", "客觀專業占卜師")
    
    st.divider()
    st.subheader("✨ 你的占卜結果")
    st.success(f"🔮 針對問題「{res['question']}」，你的【{current_style}】分析如下：")
    
    col_res1, col_res2, col_res3 = st.columns(3)
    cols_res = [col_res1, col_res2, col_res3]
    
    img_dir = os.path.join(os.path.dirname(__file__), "images")
    
    for i in range(3):
        with cols_res[i]:
            st.info(res["time_labels"][i])
            card_name = res["cards"][i]
            direction = res["directions"][i]
            
            st.subheader(card_name)
            st.markdown(f"**狀態：【{direction}】**")
            
            pure_target = card_name.replace(" ", "").lower()
            pure_target = pure_target.replace("(", "").replace(")", "").replace("（", "").replace("）", "")
            
            card_img_path = None
            if os.path.exists(img_dir):
                for filename in os.listdir(img_dir):
                    name_part, ext_part = os.path.splitext(filename)
                    if ext_part.lower() in [".jpeg", ".jpg", ".png"]:
                        pure_file = name_part.replace(" ", "").lower()
                        pure_file = pure_file.replace("(", "").replace(")", "").replace("（", "").replace("）", "")
                        if pure_file == pure_target:
                            card_img_path = os.path.join(img_dir, filename)
                            break
            
            if card_img_path and os.path.exists(card_img_path):
                with open(card_img_path, "rb") as img_file:
                    card_b64 = base64.b64encode(img_file.read()).decode()
                
                rotate_style = "transform: rotate(180deg);" if direction == "逆位" else ""
                st.markdown(f"""
                    <div style="text-align: center; margin-bottom: 15px;">
                        <img src="data:image/jpeg;base64,{card_b64}" 
                             style="{rotate_style} max-width: 170px; width: 100%; border-radius: 8px; box-shadow: 0px 4px 15px rgba(0,0,0,0.5);">
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.caption(f"✨（找不到對應圖片）")
            
            st.write(tarot_db[card_name][direction])
            
    st.divider()
    
    # ================= 6. 串接 Gemini AI 綜合講評 =================
    st.subheader(f"📝 {current_style} 的綜合分析")
    
    if "ai_analysis" not in st.session_state.drawn_results:
        st.session_state.drawn_results["ai_analysis"] = None

    if not st.session_state.drawn_results["ai_analysis"]:
        with st.spinner(f"✨ 正在由【{current_style}】為你深度解讀..."):
            try:
                try:
                    MY_API_KEY = st.secrets["GEMINI_API_KEY"]
                except:
                    # 萬一本地測試沒設定，就先留空或用原本的
                    MY_API_KEY = "AIzaSyBcuq0X1Cx-v6_l_NWvO9nGeSwJqIcVKjs" 
                    
                client = genai.Client(api_key=MY_API_KEY)
                
                prompt = f"""
                你現在是一位設定為【{current_style}】風格的資深心理諮詢師與塔羅占卜專家。
                有一位名叫「{res['name']}」的大學生問了一個問題：「{res['question']}」。
                抽到的牌陣為：
                - 過去：{res['cards'][0]} ({res['directions'][0]})
                - 現在：{res['cards'][1]} ({res['directions'][1]})
                - 未來：{res['cards'][2]} ({res['directions'][2]})

                請根據【{current_style}】的人設特點提供 150~200 字的深度解析：
                1. 溫柔心靈導師：充滿同理心、語氣溫暖、給予心靈上的療癒與支持、側重情緒疏導。
                2. 理性邏輯分析師：語氣冷靜、層次分明、著重於因果關係與客觀Facts分析、側重決策路徑。
                3. 古典塔羅解讀師：语氣帶有神祕與文學感、使用傳統象徵、古典詮釋學、側重命運原型與歷史寓意。
                4. 客觀專業占占卜師：語氣中立且專業、實事求是、側重於卡牌表面訊息的直白轉譯、不帶過多個人論斷。
                
                注意：請準確傳達牌意，維持知性且專業的口吻，絕對不要有機器感。
                """
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )
                st.session_state.drawn_results["ai_analysis"] = response.text
                
            except Exception as e:
                st.error(f"呼叫 API 時發生錯誤：{e}")
                # 💥 已修正：將原本錯誤的 turb_results 修正為正確的 drawn_results
                st.session_state.drawn_results["ai_analysis"] = "哎呀，宇宙訊號有點干擾，請稍後再試！"

    st.write(st.session_state.drawn_results["ai_analysis"])
    
    # ================= 7. 社群一鍵分享 =================
    st.write("---")
    st.subheader("📢 分享你的占卜訊息")
    
    share_text = f"🔮 我的今日塔羅占卜報告 🔮\n\n【占卜師流派】：{current_style}\n【我的提問】：『{res['question']}』\n🃏 過去 (Past)：{res['cards'][0]} ({res['directions'][0]})\n🃏 現在 (Present)：{res['cards'][1]} ({res['directions'][1]})\n🃏 未來 (Future)：{res['cards'][2]} ({res['directions'][2]})\n\n快來測測你的今日運勢吧！\n-- 來自《Python 智慧占卜大師》"
    encoded_text = urllib.parse.quote(share_text)
    
    my_app_url = "https://tarotap.com" 
    encoded_url = urllib.parse.quote(my_app_url)
    
    share_col1, share_col2, share_col3 = st.columns(3)
    
    with share_col1:
        line_url = f"https://line.me/R/share?text={encoded_text}%20{encoded_url}"
        st.markdown(f'<a href="{line_url}" target="_blank"><button style="width:100%; background-color:#06C755; color:white; border:none; padding:12px; border-radius:8px; font-weight:bold; cursor:pointer; box-shadow: 0px 4px 10px rgba(6,199,85,0.3);">🟢 分享到 LINE 聊天室</button></a>', unsafe_allow_html=True)
        
    with share_col2:
        threads_url = f"https://threads.net/intent/post?text={encoded_text}"
        st.markdown(f'<a href="{threads_url}" target="_blank"><button style="width:100%; background-color:#000000; color:white; border:1px solid #333; padding:12px; border-radius:8px; font-weight:bold; cursor:pointer; box-shadow: 0px 4px 10px rgba(255,255,255,0.1);">🖤 一鍵發布到 Threads</button></a>', unsafe_allow_html=True)
        
    with share_col3:
        fb_url = f"https://www.facebook.com/sharer/sharer.php?u={encoded_url}"
        st.markdown(f'<a href="{fb_url}" target="_blank"><button style="width:100%; background-color:#1877F2; color:white; border:none; padding:12px; border-radius:8px; font-weight:bold; cursor:pointer; box-shadow: 0px 4px 10px rgba(24,119,242,0.3);">🔵 分享主頁到 Facebook</button></a>', unsafe_allow_html=True)
        
    st.text_area(label="快速複製專用貼文框", value=share_text, height=140, label_visibility="collapsed")

    # ================= 8. 🔄 重新占卜功能 =================
    st.divider()
    if st.button("🔄 重新占卜"):
        st.session_state.is_setup = False
        st.session_state.chosen_indices = []
        st.session_state.drawn_results = None
        st.rerun()