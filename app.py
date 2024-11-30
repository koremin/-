from flask import Flask, render_template, request, send_file, redirect, url_for
from PIL import Image
import os
import io
import zipfile
import re
from pdf2image import convert_from_bytes
import fitz  # PyMuPDF

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'bmp', 'tiff', 'webp', 'pdf'}
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
    'pdf': 'application/pdf',
}

@app.route('/', methods=['GET', 'POST'])
def upload_files():
    if request.method == 'POST':
        # 폼 데이터 가져오기
        files = request.files.getlist('files')
        width = request.form.get('width')
        height = request.form.get('height')
        convert_to = request.form.get('convert_to')
        convert_direction = request.form.get('convert_direction')

        # 파일이 선택되지 않은 경우
        if not files or files[0].filename == '':
            return redirect(request.url)

        images = []
        for file in files:
            if file and allowed_file(file.filename):
                original_filename = safe_filename(file.filename)
                ext = original_filename.rsplit('.', 1)[1].lower()

                if convert_direction == 'pdf_to_image' and ext == 'pdf':
                    # PDF를 이미지로 변환
                    try:
                        # PDF 파일을 바이트로 읽기
                        pdf_bytes = file.read()
                        # PDF를 이미지로 변환
                        pages = convert_from_bytes(pdf_bytes)
                        for i, page in enumerate(pages):
                            img_io = io.BytesIO()
                            page.save(img_io, format='PNG')
                            img_io.seek(0)
                            filename_without_ext = '.'.join(original_filename.split('.')[:-1])
                            new_filename = f"{filename_without_ext}_page_{i + 1}.png"
                            images.append((new_filename, img_io))
                    except Exception as e:
                        print(f"PDF 변환 오류: {e}")
                        continue

                elif convert_direction == 'image_to_pdf' and ext in app.config['ALLOWED_EXTENSIONS'] - {'pdf'}:
                    # 이미지를 PDF로 변환
                    try:
                        img = Image.open(file.stream)
                        img = img.convert('RGB')
                        images.append((original_filename, img))
                    except Exception as e:
                        print(f"이미지 변환 오류: {e}")
                        continue

                else:
                    # 기존 이미지 처리 (크기 조절 및 포맷 변환)
                    try:
                        img = Image.open(file.stream)

                        # 크기 조절
                        if width or height:
                            w, h = img.size
                            width_val = int(width) if width else None
                            height_val = int(height) if height else None

                            if width_val and height_val:
                                img = img.resize((width_val, height_val))
                            elif width_val:
                                ratio = width_val / w
                                height_val = int(h * ratio)
                                img = img.resize((width_val, height_val))
                            elif height_val:
                                ratio = height_val / h
                                width_val = int(w * ratio)
                                img = img.resize((width_val, height_val))

                        # 확장자 변환 여부 확인
                        if convert_to:
                            target_ext = convert_to.lower()
                        else:
                            target_ext = img.format.lower()
                            if target_ext == 'jpeg':
                                target_ext = 'jpg'

                        # 이미지 메모리에 저장
                        img_io = io.BytesIO()
                        img.save(img_io, format=target_ext.upper())
                        img_io.seek(0)

                        # 파일 이름 업데이트 (확장자 변경 시)
                        filename_without_ext = '.'.join(original_filename.split('.')[:-1])
                        new_filename = f"{filename_without_ext}.{target_ext}"
                        images.append((new_filename, img_io))
                    except Exception as e:
                        print(f"이미지 처리 오류: {e}")
                        continue

        if not images:
            return redirect(request.url)

        if convert_direction == 'image_to_pdf':
            # 이미지들을 하나의 PDF로 변환
            try:
                pdf_io = io.BytesIO()
                img_list = [img for fname, img in images]
                if img_list:
                    img_list[0].save(pdf_io, format='PDF', save_all=True, append_images=img_list[1:])
                pdf_io.seek(0)

                response = send_file(
                    pdf_io,
                    mimetype='application/pdf',
                    as_attachment=True,
                    download_name='converted.pdf')
                response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
                return response
            except Exception as e:
                print(f"PDF 생성 오류: {e}")
                return redirect(request.url)

        elif len(images) == 1:
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
                    if isinstance(img_io, Image.Image):
                        img_bytes = io.BytesIO()
                        img_io.save(img_bytes, format='PDF')
                        zipf.writestr(f"{filename}.pdf", img_bytes.getvalue())
                    else:
                        zipf.writestr(filename, img_io.getvalue())
            zip_io.seek(0)

            response = send_file(
                zip_io,
                mimetype='application/zip',
                as_attachment=True,
                download_name='converted_files.zip')
            response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
            return response

    return render_template('index.html')

if __name__ == '__main__':
    app.run(debug=True)
