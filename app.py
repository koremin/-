from flask import Flask, render_template, request, send_file, redirect, url_for
from PIL import Image
import os
import io
import zipfile
import re

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp'}
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 최대 파일 크기: 16MB

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# 허용된 파일 확장자 확인
def allowed_file(filename):
    return '.' in filename and \
        filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# 안전한 파일 이름 생성 (비ASCII 문자 허용)
def safe_filename(filename):
    # NULL 바이트 제거
    filename = filename.replace('\x00', '')
    # 경로 구분자 제거
    filename = filename.replace('/', '').replace('\\', '')
    # 제어 문자 제거
    filename = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', filename)
    return filename

# 확장자에 따른 MIME 타입 매핑
MIMETYPES = {
    'jpg': 'image/jpeg',
    'jpeg': 'image/jpeg',
    'png': 'image/png',
    'gif': 'image/gif',
    'bmp': 'image/bmp',
    'tiff': 'image/tiff',
    'webp': 'image/webp',
}

@app.route('/', methods=['GET', 'POST'])
def upload_files():
    if request.method == 'POST':
        # 폼 데이터 가져오기
        files = request.files.getlist('files')
        width = request.form.get('width')
        height = request.form.get('height')
        convert_to = request.form.get('convert_to')

        # 파일이 선택되지 않은 경우
        if not files or files[0].filename == '':
            return redirect(request.url)

        images = []
        for file in files:
            if file and allowed_file(file.filename):
                original_filename = safe_filename(file.filename)
                img = Image.open(file.stream)

                # 크기 조절
                if width or height:
                    w, h = img.size
                    width = int(width) if width else None
                    height = int(height) if height else None

                    if width and height:
                        img = img.resize((width, height))
                    elif width:
                        ratio = width / w
                        height = int(h * ratio)
                        img = img.resize((width, height))
                    elif height:
                        ratio = height / h
                        width = int(w * ratio)
                        img = img.resize((width, height))

                # 확장자 변환 여부 확인
                if convert_to:
                    ext = convert_to.lower()
                else:
                    ext = img.format.lower()
                    if ext == 'jpeg':
                        ext = 'jpg'

                # 이미지 메모리에 저장
                img_io = io.BytesIO()
                img.save(img_io, format=ext.upper())
                img_io.seek(0)

                # 파일 이름 업데이트 (확장자 변경 시)
                filename_without_ext = '.'.join(original_filename.split('.')[:-1])
                new_filename = f"{filename_without_ext}.{ext}"
                images.append((new_filename, img_io))

        if len(images) == 1:
            filename, img_io = images[0]
            ext = filename.rsplit('.', 1)[1].lower()
            mime = MIMETYPES.get(ext, 'application/octet-stream')

            response = send_file(
                img_io,
                mimetype=mime,
                as_attachment=True,
                download_name=filename)
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return response
        else:
            # ZIP 파일 생성
            zip_io = io.BytesIO()
            with zipfile.ZipFile(zip_io, mode='w') as zipf:
                for filename, img_io in images:
                    zipf.writestr(filename, img_io.getvalue())
            zip_io.seek(0)

            response = send_file(
                zip_io,
                mimetype='application/zip',
                as_attachment=True,
                download_name='images.zip')
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return response

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
