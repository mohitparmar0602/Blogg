// Live Markdown preview using marked.js (loaded via CDN in editor.html)
document.addEventListener('DOMContentLoaded', () => {
    const textarea = document.getElementById('md-input');
    const preview = document.getElementById('md-preview');

    if (!textarea || !preview) return;
    if (window.marked) {
        marked.setOptions({
            gfm: true,
            breaks: true,
        });
    }
    function updatePreview() {
        if (!window.marked) {
            preview.innerHTML = '<p style="color:#f59e0b">⚠ marked.js not loaded yet. Try refreshing.</p>';
            return;
        }
        const raw = textarea.value.trim() || '*Start typing...*';
        preview.innerHTML = marked.parse(raw);
        if (window.hljs) {
            preview.querySelectorAll('pre code').forEach(block => hljs.highlightElement(block));
        }
    }

    textarea.addEventListener('input', updatePreview);
    updatePreview();
    textarea.addEventListener('keydown', e => {
        if (e.key === 'Tab') {
            e.preventDefault();
            const start = textarea.selectionStart;
            const end = textarea.selectionEnd;
            textarea.value = textarea.value.substring(0, start) + '  ' + textarea.value.substring(end);
            textarea.selectionStart = textarea.selectionEnd = start + 2;
            updatePreview();
        }
    });
});