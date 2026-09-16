import gradio as gr
from beau.core.orchestrator import run_beau

async def chat_fn(msg, history):
    if not msg:
        return history
    history = history or []
    reply = await run_beau(msg)
    return history + [(msg, reply)]


async def audio_fn(audio_path, history):
    if not audio_path:
        return history
    history = history or []
    try:
        with open(audio_path, "rb") as f:
            audio_bytes = f.read()
        from beau.voice.stt.provider import get_stt

        text = await get_stt().transcribe(audio_bytes)
        if not text or text.startswith("[STT error"):
            return history + [(f"[audio: {audio_path}]", text or "[STT empty]")]
        reply = await run_beau(text)
        # optional TTS: try fish audio but don't fail chat if unavailable
        try:
            from beau.voice.fish_audio.client import FishAudioClient

            client = FishAudioClient()
            if client.is_available():
                wav = await client.tts(reply)
                # try hermes playback if enabled
                try:
                    from beau.browser.hermes import HermesBridge

                    bridge = HermesBridge()
                    await bridge.play_audio(wav)
                except Exception:
                    pass
        except Exception:
            pass
        return history + [(text, reply)]
    except Exception as e:
        return (history or []) + [(f"[audio error: {audio_path}]", f"[error: {e}]")]


with gr.Blocks(title="BEAU - Jarvis") as demo:
    gr.Markdown("# BEAU — Jarvis SuperAgent (Muse Spark + Fish Audio)")
    chatbot = gr.Chatbot()
    msg = gr.Textbox(label="Talk to BEAU")
    audio_in = gr.Audio(type="filepath", label="Voice input (OpenCode/Fish)")
    msg.submit(chat_fn, [msg, chatbot], [chatbot])
    audio_in.change(audio_fn, [audio_in, chatbot], [chatbot])

demo.queue()

if __name__ == "__main__":
    demo.launch(server_name="0.0.0.0", server_port=7860)
