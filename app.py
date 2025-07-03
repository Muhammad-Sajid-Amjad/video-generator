from flask import Flask, request, jsonify, send_file
from moviepy.editor import VideoFileClip, CompositeVideoClip, ImageClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import os
import uuid
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

video_path = "template.mp4"
font_path = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"  # Fallback safe font
font_size = 90
font_color = "black"
bg_color = "white"

def create_text_image(text, width):
    font = ImageFont.truetype(font_path, font_size)
    dummy_img = Image.new("RGB", (width, 1000), color=bg_color)
    draw = ImageDraw.Draw(dummy_img)

    paragraphs = text.split("\n")
    lines = []

    for para in paragraphs:
        words = para.split(" ")
        line = ""
        for word in words:
            test_line = line + " " + word if line else word
            if draw.textlength(test_line, font=font) < width - 100:
                line = test_line
            else:
                lines.append(line)
                line = word
        lines.append(line)

    line_height = font_size + 10
    total_height = 50 + len(lines) * line_height + 50

    img = Image.new("RGB", (width, total_height), color=bg_color)
    draw = ImageDraw.Draw(img)

    y_offset = 50
    for line in lines:
        text_width = draw.textlength(line, font=font)
        x = (width - int(text_width)) // 2
        draw.text((x, y_offset), line, font=font, fill=font_color)
        y_offset += line_height

    return np.array(img)

@app.route('/generate', methods=['POST'])
def generate_videos():
    try:
        data = request.get_json(force=True)
        hook_texts = data.get("hooks", "")
        if not hook_texts.strip():
            return jsonify({"error": "No hooks provided"}), 400

        hooks = [h.strip() for h in hook_texts.strip().split("\n\n") if h.strip()]
        saved_files = []

        os.makedirs("videos", exist_ok=True)

        for i, hook in enumerate(hooks, 1):
            app.logger.info(f"Generating video {i}")
            video = VideoFileClip(video_path)
            video_width = video.w
            y_offset = int(video.h * 0.15)

            img_np = create_text_image(hook, video_width)
            txt_clip = ImageClip(img_np).set_duration(video.duration).set_position(("center", y_offset))
            final = CompositeVideoClip([video, txt_clip])

            filename = f"output_{uuid.uuid4().hex[:8]}.mp4"
            filepath = os.path.join("videos", filename)
            final.write_videofile(filepath, codec="libx264", audio_codec="aac", logger=None)

            saved_files.append(f"https://{request.host}/download/{filename}")

        return jsonify({"status": "success", "files": saved_files})

    except Exception as e:
        app.logger.error("🔥 Error generating video", exc_info=True)
        return jsonify({"error": "Internal server error"}), 500

@app.route('/download/<filename>', methods=['GET'])
def download(filename):
    filepath = os.path.join("videos", filename)
    if os.path.exists(filepath):
        return send_file(filepath, as_attachment=True)
    return jsonify({"error": "File not found"}), 404

# Don't specify port manually; Render handles it
if __name__ == "__main__":
    app.run(host="0.0.0.0")
