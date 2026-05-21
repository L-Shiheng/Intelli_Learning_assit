import streamlit as st
from openai import OpenAI
import base64

# ==========================================
# 0. 核心工具函数：修复 LaTeX 数学公式乱码
# ==========================================
def format_latex(text):
    """转换大模型的 LaTeX 公式包裹符为 Streamlit 兼容格式"""
    if not isinstance(text, str):
        return text
    # 替换行内公式的括号为 $，替换块级公式的括号为 $$
    return text.replace(r'\(', '$').replace(r'\)', '$').replace(r'\[', '$$').replace(r'\]', '$$')

# ==========================================
# 1. 页面与侧边栏基础配置
# ==========================================
st.set_page_config(page_title="AI 名师伴读", page_icon="🦉", layout="centered")

with st.sidebar:
    st.title("⚙️ 系统配置")
    api_key = st.text_input("请输入智谱 API Key (GLM-4V-Flash)", type="password")
    st.markdown("[免费获取智谱API Key](https://open.bigmodel.cn/)")
    st.markdown("---")
    st.info("💡 提示：本应用采用智谱最新免费视觉大模型。请引导孩子拍摄清晰的题目照片。")

# ==========================================
# 2. 苏格拉底式教育大脑设定
# ==========================================
SYSTEM_PROMPT = """你是一位极具亲和力、专业素养极高的北京海淀区顶尖小学数学教师。你的辅导对象是一名三年级的学生。
你的核心教学红线：【无论如何，绝对不可以直接给出计算的最终答案，也不能直接写出完整的解题算式】！

你需要采用“苏格拉底启发式教学法”，按照以下步骤引导学生：
1. 鼓励与肯定：先给予孩子积极的情绪反馈（如“老师看到你已经在思考了，很棒！”）。
2. 剖析题意：用符合三年级认知水平的语言，或者生活中的简单类比（比如分糖果、搭积木）来解释题目。
3. 引导反问：每次只问一个关键的小问题，引导学生自己推导下一步。
4. 动态降维：如果学生回答“不知道”或表现出沮丧，请把问题拆解得极其简单（例如降维到基础的加减乘除）来帮他找回自信。

请使用生动、活泼、充满鼓励的语气，你现在的角色就是孩子的思维伴侣。"""

# ==========================================
# 3. 状态管理 (维持上下文记忆)
# ==========================================
# 修复1：正确初始化空列表
if "messages" not in st.session_state:
    st.session_state.messages =

# ==========================================
# 4. 主界面与多模态交互
# ==========================================
st.title("🦉 你的专属数学思维伴侣")

# 步骤一：图片上传
uploaded_file = st.file_uploader("📸 遇到不会的题？把错题拍下来传给我吧！", type=["jpg", "jpeg", "png"])
if uploaded_file:
    st.image(uploaded_file, caption="当前题目", use_container_width=True)

# 步骤二：渲染历史聊天记录 (应用 LaTeX 格式修复及兼容列表/字符串格式)
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        # 修复4：正确处理多模态列表消息与纯文本消息的展示
        if isinstance(msg["content"], list):
            for item in msg["content"]:
                if item["type"] == "text":
                    display_text = item["text"].replace("（这是我上传的题目图片）\n", "")
                    st.markdown(format_latex(display_text))
        else:
            st.markdown(format_latex(msg["content"]))

# 步骤三：用户输入与 AI 响应
if prompt := st.chat_input("和老师说说你是怎么想的，或者你卡在哪里了？"):
    if not api_key:
        st.error("⚠️ 请先在左侧边栏配置 API Key！")
        st.stop()

    is_first_user_msg = all(m["role"]!= "user" for m in st.session_state.messages)
    
    # 修复2：不再使用空列表append，直接根据条件构造正确的 content 结构
    if uploaded_file and is_first_user_msg:
        base64_image = base64.b64encode(uploaded_file.getvalue()).decode("utf-8")
        image_format = uploaded_file.type.split('/')[-1]
        
        user_msg_content = [
            {
                "type": "text", 
                "text": f"（这是我上传的题目图片）\n{prompt}"
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/{image_format};base64,{base64_image}"
                }
            }
        ]
    else:
        # 后续对话直接传入纯文本字符串
        user_msg_content = prompt

    st.session_state.messages.append({"role": "user", "content": user_msg_content})
    
    # 界面回显用户输入
    with st.chat_message("user"):
        st.markdown(prompt)

    # 步骤四：调用大模型并流式输出
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            client = OpenAI(
                api_key=api_key,
                base_url="https://open.bigmodel.cn/api/paas/v4/"
            )
            
            # 修复3：正确地将系统提示词作为列表元素拼接到历史记录最前方
            api_messages = + st.session_state.messages
            
            response = client.chat.completions.create(
                model="glm-4v-flash",
                messages=api_messages,
                stream=True,
            )
            
            # 修复5：正确解析 OpenAI SDK 的 chunk 结构 (chunk.choices)
            for chunk in response:
                if chunk.choices and chunk.choices.delta.content is not None:
                    full_response += chunk.choices.delta.content
                    message_placeholder.markdown(format_latex(full_response) + "▌")
                    
            # 最终输出去掉光标
            message_placeholder.markdown(format_latex(full_response))
            
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"调用 AI 老师时出错了，请检查网络或 API Key: {str(e)}")
