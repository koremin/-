// 폼 제출 시 '변환 중...' 메시지 표시
const form = document.getElementById('upload-form');
const loading = document.getElementById('loading');
form.addEventListener('submit', function () {
    form.style.display = 'none';
    loading.style.display = 'block';
});

// 파일 선택 시 파일 이름 표시
const fileInput = document.querySelector('input[type="file"]');
const fileName = document.getElementById('file-name');

fileInput.addEventListener('change', function () {
    if (fileInput.files.length > 0) {
        fileName.textContent = Array.from(fileInput.files).map(f => f.name).join(', ');
    } else {
        fileName.textContent = '선택된 파일이 없습니다.';
    }
});
