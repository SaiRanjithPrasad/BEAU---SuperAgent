import gradio as gr
from beau.core.orchestrator import run_beau
async def chat_fn(msg, history):
    reply = await run_beau(msg)
    return reply
with gr.Blocks(title="BEAU - Jarvis") as demo:
    gr.Markdown("# BEAU — Jarvis SuperAgent (Muse Spark + Fish Audio)")
    chatbot = gr.Chatbot()
    msg = gr.Textbox(label="Talk to BEAU")
    audio_in = gr.Audio(type="filepath", label="Voice input (OpenCode/Fish)")
    msg.submit(lambda m,h: h+[ (m,"...")], [msg, chatbot], [chatbot])
if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
