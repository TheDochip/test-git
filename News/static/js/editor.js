// Конструктор публикации (templates/news/post_edit.html).
//
// Каждый блок отправляется полями:
//   block_<N>_type, block_<N>_content, block_<N>_file, block_<N>_existing_id
// N — порядковый номер блока на странице; сервер берёт из него позицию.

(function () {
    'use strict';

    const form = document.querySelector('[data-editor]');
    if (!form) {
        return;
    }

    const list = form.querySelector('[data-blocks]');
    const emptyState = form.querySelector('[data-blocks-empty]');
    const template = document.getElementById('eblock-template');
    const dataScript = document.getElementById('existing-blocks-data');

    const NAMES = {
        text: 'Текст',
        image: 'Изображение',
        video: 'Видео',
        file: 'Файл',
        link: 'Ссылка',
        quote: 'Цитата',
        divider: 'Разделитель',
    };

    const ACCEPT = {
        image: 'image/*',
        video: 'video/*',
        file: '.pdf,.txt,.csv,.rtf,.doc,.docx,.xls,.xlsx,.ppt,.pptx,.odt,.ods,.odp,.zip,.rar,.7z',
    };

    const TOOLBAR = [
        { label: 'Ж', title: 'Жирный', command: 'bold' },
        { label: 'К', title: 'Курсив', command: 'italic' },
        { label: 'Ч', title: 'Подчёркнутый', command: 'underline' },
        { label: 'H2', title: 'Заголовок', command: 'formatBlock', value: 'h2' },
        { label: 'H3', title: 'Подзаголовок', command: 'formatBlock', value: 'h3' },
        { label: '•', title: 'Список', command: 'insertUnorderedList' },
        { label: '1.', title: 'Нумерованный список', command: 'insertOrderedList' },
        { label: '“”', title: 'Цитата', command: 'formatBlock', value: 'blockquote' },
        { label: 'Ссылка', title: 'Вставить ссылку', command: 'createLink' },
        { label: '¶', title: 'Обычный абзац', command: 'formatBlock', value: 'p' },
    ];

    let isDirty = false;
    let isSubmitting = false;


    // ---------- утилиты ----------

    function create(tag, attrs, children) {
        const node = document.createElement(tag);
        Object.entries(attrs || {}).forEach(function ([key, value]) {
            if (value === undefined || value === null || value === false) {
                return;
            }
            if (key === 'text') {
                node.textContent = value;
            } else if (key === 'className') {
                node.className = value;
            } else {
                node.setAttribute(key, value === true ? '' : value);
            }
        });
        (children || []).forEach(function (child) {
            if (child) {
                node.appendChild(child);
            }
        });
        return node;
    }

    function fieldName(suffix) {
        // Реальный номер подставляет renumber().
        return 'block_0_' + suffix;
    }

    function markDirty() {
        isDirty = true;
    }


    // ---------- содержимое блоков ----------

    function buildTextBody(body, data) {
        const area = create('div', {
            className: 'rich-editor-area',
            contenteditable: 'true',
            role: 'textbox',
            'aria-multiline': 'true',
            'aria-label': 'Текст',
            'data-placeholder': 'Начните писать...',
        });
        // Содержимое уже очищено на сервере (bleach), поэтому его можно вставить как HTML.
        area.innerHTML = data.content || '';

        const input = create('textarea', { name: fieldName('content'), hidden: true });
        input.value = area.innerHTML;

        const toolbar = create('div', { className: 'rich-toolbar', role: 'toolbar', 'aria-label': 'Форматирование' });
        TOOLBAR.forEach(function (item) {
            const button = create('button', { type: 'button', title: item.title, text: item.label });
            button.addEventListener('mousedown', function (event) {
                event.preventDefault(); // не терять выделение в редакторе
            });
            button.addEventListener('click', function () {
                area.focus();
                if (item.command === 'createLink') {
                    const url = window.prompt('Адрес ссылки (https://...)');
                    if (!url || !/^https?:\/\//i.test(url.trim())) {
                        return;
                    }
                    document.execCommand('createLink', false, url.trim());
                } else {
                    document.execCommand(item.command, false, item.value || null);
                }
                sync();
            });
            toolbar.appendChild(button);
        });

        function sync() {
            input.value = area.innerHTML;
            markDirty();
        }

        area.addEventListener('input', sync);

        // Вставляем только текст, без чужих стилей и разметки из Word или сайтов.
        area.addEventListener('paste', function (event) {
            event.preventDefault();
            const text = (event.clipboardData || window.clipboardData).getData('text/plain');
            document.execCommand('insertText', false, text);
        });

        body.append(toolbar, area, input);
        return area;
    }

    function buildFileBody(body, type, data) {
        const preview = create('div', { className: 'current-file' });

        if (data.file_url) {
            if (type === 'image') {
                preview.appendChild(create('img', { src: data.file_url, alt: '' }));
            }
            preview.appendChild(create('a', {
                href: data.file_url,
                target: '_blank',
                rel: 'noopener',
                className: 'link',
                text: data.file_name || 'Текущий файл',
            }));
            preview.appendChild(create('span', { className: 'muted', text: 'Выберите новый файл, чтобы заменить.' }));
        }

        const input = create('input', {
            type: 'file',
            name: fieldName('file'),
            accept: ACCEPT[type],
            'aria-label': NAMES[type],
        });

        const livePreview = create('img', { className: 'upload-preview', alt: '', hidden: true });

        input.addEventListener('change', function () {
            markDirty();
            const file = input.files && input.files[0];
            if (type === 'image' && file) {
                livePreview.src = URL.createObjectURL(file);
                livePreview.hidden = false;
                preview.hidden = true;
            } else {
                livePreview.hidden = true;
                preview.hidden = false;
            }
        });

        body.append(preview, livePreview, input);
        return input;
    }

    function buildBody(body, type, data) {
        if (type === 'text') {
            return buildTextBody(body, data);
        }

        if (type === 'image' || type === 'video' || type === 'file') {
            return buildFileBody(body, type, data);
        }

        if (type === 'link') {
            const input = create('input', {
                type: 'url',
                name: fieldName('content'),
                placeholder: 'https://example.com/statya',
                'aria-label': 'Адрес ссылки',
            });
            input.value = data.content || '';
            input.addEventListener('input', markDirty);
            body.appendChild(input);
            return input;
        }

        if (type === 'quote') {
            const textarea = create('textarea', {
                name: fieldName('content'),
                rows: '3',
                placeholder: 'Текст цитаты',
                'aria-label': 'Цитата',
            });
            textarea.value = data.content || '';
            textarea.addEventListener('input', markDirty);
            body.appendChild(textarea);
            return textarea;
        }

        if (type === 'divider') {
            body.appendChild(create('hr', { className: 'block-divider' }));
        }

        return null;
    }


    // ---------- список блоков ----------

    function addBlock(type, data, options) {
        if (!NAMES[type]) {
            return;
        }

        data = data || {};
        const block = template.content.firstElementChild.cloneNode(true);
        block.dataset.type = type;
        block.classList.add('eblock--' + type);
        block.querySelector('[data-block-name]').textContent = NAMES[type];

        const body = block.querySelector('[data-block-body]');
        body.appendChild(create('input', { type: 'hidden', name: fieldName('type'), value: type }));
        if (data.id) {
            body.appendChild(create('input', { type: 'hidden', name: fieldName('existing_id'), value: data.id }));
        }

        const focusTarget = buildBody(body, type, data);

        list.appendChild(block);
        refresh();

        if (options && options.focus && focusTarget) {
            focusTarget.focus();
            block.scrollIntoView({ block: 'nearest' });
        }
    }

    function hasContent(block) {
        const area = block.querySelector('.rich-editor-area');
        if (area && area.textContent.trim()) {
            return true;
        }
        return Array.from(block.querySelectorAll('input[type="url"], textarea:not([hidden]), input[type="file"]'))
            .some(function (field) {
                return field.type === 'file' ? field.files.length > 0 : field.value.trim() !== '';
            }) || Boolean(block.querySelector('[name$="_existing_id"]'));
    }

    function renumber() {
        list.querySelectorAll('.eblock').forEach(function (block, index) {
            block.querySelectorAll('[name]').forEach(function (field) {
                field.name = field.name.replace(/^block_\d+_/, 'block_' + index + '_');
            });

            const blocks = list.children.length;
            block.querySelector('[data-action="up"]').disabled = index === 0;
            block.querySelector('[data-action="down"]').disabled = index === blocks - 1;
        });
    }

    function refresh() {
        emptyState.hidden = list.children.length > 0;
        renumber();
    }

    list.addEventListener('click', function (event) {
        const button = event.target.closest('[data-action]');
        if (!button) {
            return;
        }

        const block = button.closest('.eblock');
        const action = button.dataset.action;

        if (action === 'delete') {
            if (hasContent(block) && !window.confirm('Удалить этот блок?')) {
                return;
            }
            block.remove();
        } else if (action === 'up' && block.previousElementSibling) {
            list.insertBefore(block, block.previousElementSibling);
            button.focus();
        } else if (action === 'down' && block.nextElementSibling) {
            list.insertBefore(block.nextElementSibling, block);
            button.focus();
        }

        markDirty();
        refresh();
    });

    form.querySelectorAll('[data-add-block]').forEach(function (button) {
        button.addEventListener('click', function () {
            addBlock(button.dataset.addBlock, {}, { focus: true });
            markDirty();
        });
    });


    // ---------- заголовок: растёт по высоте, Enter не переносит строку ----------

    form.querySelectorAll('[data-autosize]').forEach(function (textarea) {
        function resize() {
            textarea.style.height = 'auto';
            textarea.style.height = textarea.scrollHeight + 'px';
        }
        textarea.addEventListener('input', function () {
            resize();
            markDirty();
        });
        textarea.addEventListener('keydown', function (event) {
            if (event.key === 'Enter') {
                event.preventDefault();
            }
        });
        resize();
    });

    form.querySelectorAll('select, input[type="file"]').forEach(function (field) {
        field.addEventListener('change', markDirty);
    });


    // ---------- отправка и защита от потери изменений ----------

    form.addEventListener('submit', function () {
        form.querySelectorAll('.rich-editor-area').forEach(function (area) {
            area.parentElement.querySelector('textarea[hidden]').value = area.innerHTML;
        });
        renumber();
        isSubmitting = true;
    });

    window.addEventListener('beforeunload', function (event) {
        if (isDirty && !isSubmitting) {
            event.preventDefault();
            event.returnValue = '';
        }
    });


    // ---------- начальные блоки ----------

    let initial = [];
    try {
        initial = JSON.parse(dataScript ? dataScript.textContent : '[]') || [];
    } catch (error) {
        initial = [];
    }

    initial.forEach(function (block) {
        addBlock(block.type, block);
    });

    if (initial.length === 0) {
        addBlock('text', {});
    }

    refresh();
    isDirty = false;
})();
