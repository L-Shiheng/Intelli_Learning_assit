import streamlit as st
from openai import OpenAI
import base64
import re

# ==========================================
# 0. 分数转换为孩子友好的纯文本格式
# ==========================================
def fraction_to_text(text: str) -> str:
    """将所有 LaTeX 分数转换为 分子/分母 的简单形式，并移除所有 LaTeX 标记"""
    if not isinstance(text, str):
        return text

    # 1. 处理各种带括号的 \frac 变体，统一替换为 分子/分母
    # 匹配形如 \frac{5}{10}, \frac{(5)}{10}, \frac{5}{(10)}, (\frac{5}{10}) 等
    text = re.sub(
        r'\(?\\frac\{\(?(\d+)\)?\}\{\(?(\d+)\)?\}\)?',
        r'\1/\2',
        text
    )

    # 2. 移除残留的 LaTeX 标记符号
    text = text.replace(r'\(', '').replace(r'\)', '')
    text = text.replace(r'\[', '').replace(r'\]', '')
    text = text.replace('$', '')  # 移除美元符号

    # 3. 清理末尾无意义的汉字（如“没盖好”“希望这些批改对你有帮助”）
    nonsense_patterns = [
        r'没盖好$',
        r'希望这些批改对你有帮助[。.]?.*$',
        r'如果有任何疑问.*$'
    ]
    for pat in nonsense_patterns:
        text = re.sub(pat, '', text)
    
    # 4. 去掉首尾空白
    text = text.strip()
    return text

# ==========================================
# 1. 页面与侧边栏
# ==========================================
st.set_page_config(page_title="AI 名师伴读", page_icon="🦉", layout="centered")

with st.sidebar:
    st.title("⚙️ 系统配置")
    api_key = st.text_input("请输入智谱 API Key (GLM-4V-Flash)", type="password")
    st.markdown("[免费获取智谱API Key](https://open.bigmodel.cn/)")
    st.markdown("---")
    
    # 显示模式选择（默认纯文本，绝对安全）
    use_latex = st.checkbox(
        "尝试显示美观公式（需要环境支持 LaTeX 渲染）", 
        value=False,
        help="如果开启后看到乱码，请关闭此选项"
    )
    if not use_latex:
        st.success("✅ 当前使用纯文本分数格式（如 5/10），孩子一定能看懂。")
    else:
        st.warning("⚠️ 开启后需要您的 Streamlit 环境支持 LaTeX 渲染，否则孩子会看到代码。")

# ==========================================
# 2. 系统提示词（简化，不再强求 LaTeX 格式）
# ==========================================
SYSTEM_PROMPT = """你是一位极具亲和力的小学数学教师。辅导对象是三年级学生。
核心原则：绝对不要直接给出最终答案或完整算式，采用苏格拉底启发式教学。
【格式要求】请使用简单分数写法，比如 5/10 或 4/5。不要使用反斜杠或 LaTeX 命令。
请用活泼、鼓励的语气，每次只问一个小问题。"""

# ==========================================
# 3. 状态管理
# ==========================================
if "messages" not in st.session_state:
    st.session_state.messages = []

# ==========================================
# 4. 主界面
# ==========================================
st.title("🦉 你的专属数学思维伴侣")

uploaded_file = st.file_uploader("📸 遇到不会的题？把错题拍下来传给我吧！", type=["jpg", "jpeg", "png"])
if uploaded_file:
    st.image(uploaded_file, caption="当前题目", use_container_width=True)

# 显示历史消息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        if isinstance(msg["content"], list):
            for item in msg["content"]:
                if item["type"] == "text":
                    display_text = item["text"].replace("（这是我上传的题目图片）\n", "")
                    if use_latex:
                        # 尝试保留 LaTeX（但您已知不可用，一般不开启）
                        st.markdown(display_text)
                    else:
                        st.markdown(fraction_to_text(display_text))
        else:
            if use_latex:
                st.markdown(msg["content"])
            else:
                st.markdown(fraction_to_text(msg["content"]))

# 用户输入
if prompt := st.chat_input("和老师说说你是怎么想的，或者你卡在哪里了？"):
    if not api_key:
        st.error("⚠️ 请先在左侧边栏配置 API Key！")
        st.stop()

    is_first_user_msg = all(m["role"] != "user" for m in st.session_state.messages)

    if uploaded_file and is_first_user_msg:
        base64_image = base64.b64encode(uploaded_file.getvalue()).decode("utf-8")
        image_format = uploaded_file.type.split('/')[-1]
        user_msg_content = [
            {"type": "text", "text": f"（这是我上传的题目图片）\n{prompt}"},
            {"type": "image_url", "image_url": {"url": f"data:image/{image_format};base64,{base64_image}"}}
        ]
    else:
        user_msg_content = prompt

    st.session_state.messages.append({"role": "user", "content": user_msg_content})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 调用 AI
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""

        try:
            client = OpenAI(api_key=api_key, base_url="https://open.bigmodel.cn/api/paas/v4/")
            api_messages = [{"role": "system", "content": SYSTEM_PROMPT}] + st.session_state.messages

            response = client.chat.completions.create(
                model="glm-4v-flash",
                messages=api_messages,
                stream=True,
            )

            for chunk in response:
                if chunk.choices and chunk.choices[0].delta.content:
                    full_response += chunk.choices[0].delta.content
                    # 实时显示根据模式处理
                    if use_latex:
                        message_placeholder.markdown(full_response + "▌")
                    else:
                        message_placeholder.markdown(fraction_to_text(full_response) + "▌")

            # 最终显示
            if use_latex:
                final_display = full_response
            else:
                final_display = fraction_to_text(full_response)
            message_placeholder.markdown(final_display)

            st.session_state.messages.append({"role": "assistant", "content": full_response})

        except Exception as e:
            st.error(f"调用 AI 老师时出错了: {str(e)}")
