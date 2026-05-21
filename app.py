import streamlit as st
from openai import OpenAI
import base64

# ==========================================
# 1. 页面与侧边栏基础配置
# ==========================================
st.set_page_config(page_title="AI 名师伴读", page_icon="🦉", layout="centered")

with st.sidebar:
    st.title("⚙️ 系统配置")
    # 动态输入 API Key，保证不在代码中硬编码，保护你的隐私
    api_key = st.text_input("请输入智谱 API Key (GLM-4V-Flash)", type="password")
    st.markdown("[免费获取智谱API Key](https://open.bigmodel.cn/)")
    st.markdown("---")
    st.info("💡 提示：本应用采用智谱最新免费视觉大模型。请引导孩子拍摄清晰的题目照片。")

# ==========================================
# 2. 苏格拉底式教育大脑设定 (Prompt Engineering)
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

# 步骤二：渲染历史聊天记录
for msg in st.session_state.messages:
    if msg["role"]!= "system":
        with st.chat_message(msg["role"]):
            # 由于我们的消息内容可能包含图片结构，需要专门提取文字部分进行展示
            if isinstance(msg["content"], list):
                for item in msg["content"]:
                    if item["type"] == "text":
                        # 过滤掉系统附加的后台提示
                        display_text = item["text"].replace("（这是我上传的题目图片）\n", "")
                        st.markdown(display_text)
            else:
                st.markdown(msg["content"])

# 步骤三：用户输入与 AI 响应
if prompt := st.chat_input("和老师说说你是怎么想的，或者你卡在哪里了？"):
    if not api_key:
        st.error("⚠️ 请先在左侧边栏配置 API Key！")
        st.stop()

    # 处理用户输入结构 (判断是否需要包含图片)
    user_msg_content =
    
    # 我们只在孩子发出的第一条消息中附带图片，避免后续对话 Token 过载
    is_first_user_msg = all(m["role"]!= "user" for m in st.session_state.messages)
    
    if uploaded_file and is_first_user_msg:
        # 将图片转换为大模型需要的 Base64 格式
        base64_image = base64.b64encode(uploaded_file.getvalue()).decode("utf-8")
        image_format = uploaded_file.type.split('/')[-1]
        
        user_msg_content.append({
            "type": "image_url",
            "image_url": {
                "url": f"data:image/{image_format};base64,{base64_image}"
            }
        })
        user_msg_content.append({
            "type": "text", 
            "text": f"（这是我上传的题目图片）\n{prompt}"
        })
    else:
        user_msg_content = prompt

    # 1. 记录并展示用户消息
    st.session_state.messages.append({"role": "user", "content": user_msg_content})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 2. 调用大模型并流式输出
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        try:
            # 使用智谱的兼容 OpenAI SDK 接口
            client = OpenAI(
                api_key=api_key,
                base_url="https://open.bigmodel.cn/api/paas/v4/"
            )
            
            # 组装发送给大模型的完整记忆，强制加入系统提示词作为最高指令
            api_messages = + st.session_state.messages
            
            # 调用免费视觉模型 GLM-4V-Flash
            response = client.chat.completions.create(
                model="glm-4v-flash",
                messages=api_messages,
                stream=True,
            )
            
            # 打字机效果呈现
            for chunk in response:
                if chunk.choices.delta.content is not None:
                    full_response += chunk.choices.delta.content
                    message_placeholder.markdown(full_response + "▌")
            message_placeholder.markdown(full_response)
            
            # 保存 AI 的回答到记忆中
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            
        except Exception as e:
            st.error(f"调用 AI 老师时出错了，请检查网络或 API Key: {str(e)}")
