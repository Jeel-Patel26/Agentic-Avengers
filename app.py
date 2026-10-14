
import streamlit as st
import ollama
import speech_recognition as sr
import qrcode

from gtts import gTTS
from io import BytesIO
from pypdf import PdfReader
from docx import Document
from urllib.parse import quote

st.set_page_config(
    page_title="Sahakaar Saathi AI",
    page_icon="🤝",
    layout="wide"
)

st.title("🤝 Sahakaar Saathi AI")
st.write("Your AI learning assistant: answers, voice, QR, videos and mind maps.")

languages = {
    "English": {
        "instruction": "Answer in simple English.",
        "speech": "en",
        "recognition": "en-IN"
    },
    "ગુજરાતી": {
        "instruction": "જવાબ સરળ ગુજરાતીમાં આપો.",
        "speech": "gu",
        "recognition": "gu-IN"
    },
    "हिन्दी": {
        "instruction": "जवाब आसान हिन्दी में दें।",
        "speech": "hi",
        "recognition": "hi-IN"
    }
}

language = st.selectbox("Choose Language", list(languages.keys()))
settings = languages[language]


def ask_ai(prompt):
    result = ollama.chat(
        model="qwen3.5:0.8b",
        messages=[
            {
                "role": "system",
                "content": (
                    settings["instruction"]
                    + " Be helpful and accurate. Use simple words."
                )
            },
            {"role": "user", "content": prompt}
        ],
        think=False,
        options={"temperature": 0, "num_predict": 700}
    )
    return result["message"]["content"]


def read_file(file):
    data = file.getvalue()
    name = file.name.lower()

    if name.endswith(".pdf"):
        pdf = PdfReader(BytesIO(data))
        return "\n".join(page.extract_text() or "" for page in pdf.pages)

    if name.endswith(".txt"):
        return data.decode("utf-8", errors="ignore")

    if name.endswith(".docx"):
        doc = Document(BytesIO(data))
        return "\n".join(p.text for p in doc.paragraphs)

    return ""


def make_voice(text):
    audio = BytesIO()
    gTTS(text=text, lang=settings["speech"]).write_to_fp(audio)
    return audio.getvalue()


def make_qr(text):
    qr = qrcode.QRCode(box_size=8, border=3)
    qr.add_data(text[:2500])
    qr.make(fit=True)

    image = qr.make_image(fill_color="black", back_color="white")
    output = BytesIO()
    image.save(output, format="PNG")
    return output.getvalue()


def dot_escape(text):
    return text.replace("\\", "\\\\").replace('"', '\\"')


# Optional document upload
st.subheader("📄 Upload Document (Optional)")

uploaded_file = st.file_uploader(
    "PDF, DOCX or TXT",
    type=["pdf", "docx", "txt"]
)

if st.button("📂 Read Document"):
    if uploaded_file is None:
        st.warning("You can ask questions without a document.")
    else:
        try:
            text = read_file(uploaded_file)
            if text.strip():
                st.session_state["document_text"] = text[:20000]
                st.success("Document loaded successfully!")
            else:
                st.error("No readable text found in this file.")
        except Exception as e:
            st.error(f"Document error: {e}")


# Voice question
st.subheader("🎙️ Voice Assistant")

recording = st.audio_input("Record your question")

if st.button("🗣️ Convert Voice to Text"):
    if recording is None:
        st.warning("Please record your question first.")
    else:
        try:
            recognizer = sr.Recognizer()
            with sr.AudioFile(BytesIO(recording.getvalue())) as source:
                audio_data = recognizer.record(source)

            spoken = recognizer.recognize_google(
                audio_data,
                language=settings["recognition"]
            )
            st.session_state["voice_question"] = spoken
            st.success("Question recognized!")
            st.write(spoken)

        except Exception as e:
            st.error(f"Voice recognition error: {e}")


# Ask anything
st.subheader("💬 Ask Any Question")

question = st.text_input("Type your question")
voice_question = st.session_state.get("voice_question", "")
final_question = question.strip() or voice_question.strip()

if st.button("🤖 Get Answer"):
    if not final_question:
        st.warning("Please type or record a question.")
    else:
        try:
            document = st.session_state.get("document_text", "")

            if document:
                prompt = (
                    "Answer the question. Use the document when relevant. "
                    "If unrelated, answer using general knowledge.\n\n"
                    f"Question: {final_question}\n\nDocument:\n{document}"
                )
            else:
                prompt = (
                    "Answer this general question clearly and helpfully:\n"
                    + final_question
                )

            with st.spinner("AI is preparing your answer..."):
                answer = ask_ai(prompt)

            st.session_state["last_answer"] = answer
            st.session_state["last_question"] = final_question
            st.session_state["voice_question"] = ""

        except Exception as e:
            st.error(f"AI error: {e}")


# Display answer and learning tools
answer = st.session_state.get("last_answer", "")
topic = st.session_state.get("last_question", "")

if answer:
    st.divider()
    st.subheader("📝 AI Answer")
    st.write(answer)

    # Text to voice
    try:
        audio_bytes = make_voice(answer)
        st.audio(audio_bytes, format="audio/mp3")
    except Exception:
        st.info("Voice generation failed. Check your internet connection.")

    # QR code
    st.subheader("📱 QR Code for Answer")
    try:
        qr_image = make_qr(
            f"Question: {topic}\n\nAnswer:\n{answer}"
        )
        st.image(qr_image, width=220)
        st.download_button(
            "⬇️ Download QR Code",
            data=qr_image,
            file_name="sahakaar_answer_qr.png",
            mime="image/png"
        )
        st.caption("The QR contains the question and answer as text.")
    except Exception as e:
        st.error(f"QR error: {e}")

    # Video search
    st.subheader("🎥 Learn Through Videos")
    video_url = (
        "https://www.youtube.com/results?search_query="
        + quote(topic + " explained in " + language)
    )
    st.link_button("▶️ Search Related YouTube Videos", video_url)
    st.caption("This opens YouTube search results, not a verified single video.")

    # Mind map
    st.subheader("🧠 AI Mind Map")

    if st.button("✨ Generate Mind Map"):
        try:
            with st.spinner("Creating mind map..."):
                mind_text = ask_ai(
                    "Create a mind map for this topic: " + topic
                    + "\nUse the answer below as reference:\n" + answer
                    + "\nReturn exactly 5 to 7 short branches, one branch per line. "
                    + "Do not use numbering, bullets, or explanations."
                )

            branches = [
                line.strip().lstrip("-•*0123456789. ").strip()
                for line in mind_text.splitlines()
                if line.strip()
            ][:7]

            if not branches:
                branches = ["Main idea", "Key points", "Examples", "Conclusion"]

            root = dot_escape(topic[:70])
            dot = (
                'graph MindMap { graph [overlap=false, splines=true]; '
                'node [shape=box, style="rounded,filled", '
                'fillcolor="lightyellow"]; '
                f'center [label="{root}", shape=ellipse, fillcolor="lightblue"]; '
            )

            for i, branch in enumerate(branches):
                label = dot_escape(branch[:100])
                dot += f'n{i} [label="{label}"]; center -- n{i}; '

            dot += "}"

            st.graphviz_chart(dot)
            st.session_state["mindmap_text"] = "\n".join(branches)

            st.download_button(
                "⬇️ Download Mind Map Text",
                data="TOPIC: " + topic + "\n\n" + "\n".join(branches),
                file_name="mind_map.txt",
                mime="text/plain"
            )

        except Exception as e:
            st.error(f"Mind map error: {e}")

st.caption(
    "Voice features require internet. Video links open YouTube search. "
    "AI answers may need verification for important legal information."
)
