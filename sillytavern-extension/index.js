import {
    eventSource,
    event_types,
    getContext,
    saveSettingsDebounced
} from '../../../../script.js';
import {
    extension_settings,
    renderExtensionTemplateAsync
} from '../../../extensions.js';
import { SlashCommandParser } from '../../../slash-commands/SlashCommandParser.js';
import { SlashCommand } from '../../../slash-commands/SlashCommand.js';
import { SlashCommandArgument, SlashCommandNamedArgument } from '../../../slash-commands/SlashCommandArgument.js';
import { ARGUMENT_TYPE } from '../../../slash-commands/SlashCommandArgumentType.js';

// Extension Identifier & Defaults
const MODULE_NAME = 'lemon_image_bridge';
const DEFAULT_SETTINGS = {
    server_url: 'http://127.0.0.1:8000',
    model: 'freegen',
    aspect_ratio: '1:1',
    style_preset: '',
    enable_msg_btn: true,
    auto_char_context: true,
    auto_embed_chat: true
};

const RATIO_DIMENSIONS = {
    '1:1': '512x512',
    '16:9': '1024x576',
    '9:16': '576x1024',
    '4:3': '768x576',
    '3:4': '576x768'
};

/**
 * Get the current extension settings merged with defaults
 */
function getSettings() {
    extension_settings[MODULE_NAME] = extension_settings[MODULE_NAME] || {};
    for (const [key, val] of Object.entries(DEFAULT_SETTINGS)) {
        if (extension_settings[MODULE_NAME][key] === undefined) {
            extension_settings[MODULE_NAME][key] = val;
        }
    }
    return extension_settings[MODULE_NAME];
}

/**
 * Save settings to SillyTavern storage
 */
function updateSettings(patch) {
    Object.assign(getSettings(), patch);
    saveSettingsDebounced();
}

/**
 * Ping Lemon API server health
 */
async function checkServerHealth(quiet = false) {
    const settings = getSettings();
    const url = settings.server_url.replace(/\/+$/, '');
    const badge = document.getElementById('lemon_status_badge');
    const text = document.getElementById('lemon_status_text');

    try {
        const response = await fetch(`${url}/health`, { method: 'GET', signal: AbortSignal.timeout(3000) });
        if (response.ok) {
            const data = await response.json();
            if (badge && text) {
                badge.className = 'lemon-status-badge online';
                text.textContent = 'Online';
            }
            if (!quiet && window.toastr) {
                window.toastr.success(`Connected to Lemon API (${data.models?.join(', ') || 'ready'})`, 'Lemon Image Bridge');
            }
            return true;
        }
    } catch (err) {
        // Fallback or offline
    }

    if (badge && text) {
        badge.className = 'lemon-status-badge offline';
        text.textContent = 'Offline';
    }
    if (!quiet && window.toastr) {
        window.toastr.warning(`Could not reach Lemon API at ${url}. Make sure startlemon.bat is running.`, 'Lemon Image Bridge');
    }
    return false;
}

/**
 * Call the Lemon Image API with OpenAI-compatible payload
 */
async function generateImage(prompt, customModel = null, customRatio = null) {
    const settings = getSettings();
    const url = settings.server_url.replace(/\/+$/, '');
    const model = customModel || settings.model || 'freegen';
    const ratio = customRatio || settings.aspect_ratio || '1:1';
    const size = RATIO_DIMENSIONS[ratio] || '512x512';

    // Apply Style Preset if configured
    let finalPrompt = prompt.trim();
    if (settings.style_preset && !finalPrompt.includes(settings.style_preset)) {
        finalPrompt = `${finalPrompt}, ${settings.style_preset}`;
    }

    const payload = {
        model: model,
        prompt: finalPrompt,
        size: size,
        n: 1
    };

    const response = await fetch(`${url}/v1/images/generations`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    });

    if (!response.ok) {
        let errorDetail = 'Generation failed';
        try {
            const errData = await response.json();
            errorDetail = errData.detail || errorDetail;
        } catch {
            errorDetail = await response.text();
        }
        throw new Error(errorDetail);
    }

    const data = await response.json();
    if (!data.data || !data.data[0] || !data.data[0].b64_json) {
        throw new Error('No image returned by the server.');
    }

    return `data:image/png;base64,${data.data[0].b64_json}`;
}

/**
 * Extract active character description/appearance tags to enhance scene prompt
 */
function getCharacterPromptContext() {
    try {
        const context = getContext();
        if (!context || !context.characters || context.characterId === undefined) return '';
        const char = context.characters[context.characterId];
        if (!char) return '';

        const parts = [];
        if (char.name) parts.push(char.name);
        if (char.description) {
            // Take concise descriptors from character card
            const cleanDesc = char.description.replace(/\r?\n+/g, ' ').slice(0, 200);
            parts.push(cleanDesc);
        }
        return parts.join(', ');
    } catch {
        return '';
    }
}

/**
 * Open the visualizer modal for in-chat generation
 */
async function openVisualizerModal(initialPrompt = '', messageElement = null) {
    const settings = getSettings();
    let charContext = '';
    if (settings.auto_char_context) {
        charContext = getCharacterPromptContext();
    }

    let defaultPrompt = initialPrompt.trim();
    if (charContext && !defaultPrompt.includes(charContext)) {
        defaultPrompt = defaultPrompt ? `${charContext}, ${defaultPrompt}` : charContext;
    }

    // Modal template
    const modalHtml = `
    <div id="lemon_modal" class="lemon-modal-overlay">
        <div class="lemon-modal-content">
            <div class="lemon-modal-header">
                <div class="lemon-title">
                    <span>🎨</span>
                    <span>Scene Visualizer (${settings.model.toUpperCase()})</span>
                </div>
                <button id="lemon_modal_close" class="lemon-modal-close">&times;</button>
            </div>

            <div class="lemon-input-group">
                <label class="lemon-section-label" for="lemon_modal_prompt">Prompt</label>
                <textarea id="lemon_modal_prompt" class="text_pole" rows="3" style="width: 100%; box-sizing: border-box;">${defaultPrompt}</textarea>
            </div>

            <div class="lemon-input-row" style="justify-content: space-between; align-items: center;">
                <div class="lemon-ratio-grid" style="flex: 1;">
                    <div class="lemon-ratio-pill ${settings.aspect_ratio === '1:1' ? 'active' : ''}" data-ratio="1:1">1:1</div>
                    <div class="lemon-ratio-pill ${settings.aspect_ratio === '16:9' ? 'active' : ''}" data-ratio="16:9">16:9</div>
                    <div class="lemon-ratio-pill ${settings.aspect_ratio === '9:16' ? 'active' : ''}" data-ratio="9:16">9:16</div>
                    <div class="lemon-ratio-pill ${settings.aspect_ratio === '4:3' ? 'active' : ''}" data-ratio="4:3">4:3</div>
                    <div class="lemon-ratio-pill ${settings.aspect_ratio === '3:4' ? 'active' : ''}" data-ratio="3:4">3:4</div>
                </div>
                <button id="lemon_modal_gen_btn" class="lemon-btn" style="min-width: 130px;">
                    <span>✨ Generate</span>
                </button>
            </div>

            <div id="lemon_modal_preview" class="lemon-modal-preview">
                <span style="color: #94a3b8; font-style: italic;">Generated scene will appear here...</span>
            </div>

            <div id="lemon_modal_actions" class="lemon-input-row" style="display: none; justify-content: flex-end;">
                <button id="lemon_modal_embed_btn" class="lemon-btn">
                    <i class="fa-solid fa-comment-medical"></i> Insert into Chat
                </button>
                <a id="lemon_modal_download_btn" class="lemon-btn lemon-btn-secondary" download="scene.png">
                    <i class="fa-solid fa-download"></i> Save Image
                </a>
            </div>
        </div>
    </div>
    `;

    document.body.insertAdjacentHTML('beforeend', modalHtml);
    const modal = document.getElementById('lemon_modal');
    let selectedRatio = settings.aspect_ratio || '1:1';
    let currentB64Image = null;

    // Ratio selectors
    modal.querySelectorAll('.lemon-ratio-pill').forEach(pill => {
        pill.addEventListener('click', () => {
            modal.querySelectorAll('.lemon-ratio-pill').forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            selectedRatio = pill.dataset.ratio;
        });
    });

    // Close logic
    const closeModal = () => modal?.remove();
    document.getElementById('lemon_modal_close').addEventListener('click', closeModal);
    modal.addEventListener('click', (e) => {
        if (e.target === modal) closeModal();
    });

    // Generate handler
    const genBtn = document.getElementById('lemon_modal_gen_btn');
    const promptInput = document.getElementById('lemon_modal_prompt');
    const previewArea = document.getElementById('lemon_modal_preview');
    const actionsArea = document.getElementById('lemon_modal_actions');
    const downloadBtn = document.getElementById('lemon_modal_download_btn');
    const embedBtn = document.getElementById('lemon_modal_embed_btn');

    genBtn.addEventListener('click', async () => {
        const prompt = promptInput.value.trim();
        if (!prompt) {
            if (window.toastr) window.toastr.warning('Please enter a prompt');
            return;
        }

        genBtn.disabled = true;
        genBtn.innerHTML = '<div class="lemon-spinner" style="width: 16px; height: 16px; border-width: 2px;"></div>';
        previewArea.innerHTML = '<div class="lemon-spinner"></div>';
        actionsArea.style.display = 'none';

        try {
            const b64 = await generateImage(prompt, settings.model, selectedRatio);
            currentB64Image = b64;
            previewArea.innerHTML = `<img src="${b64}" alt="Generated scene" />`;
            downloadBtn.href = b64;
            actionsArea.style.display = 'flex';

            // Auto embed if enabled and a message element was provided
            if (settings.auto_embed_chat && messageElement) {
                appendImageToChatMessage(messageElement, b64);
            }
        } catch (err) {
            previewArea.innerHTML = `<span style="color: #f87171; padding: 12px;">Error: ${err.message}</span>`;
            if (window.toastr) window.toastr.error(err.message, 'Generation Failed');
        } finally {
            genBtn.disabled = false;
            genBtn.innerHTML = '<span>✨ Generate</span>';
        }
    });

    // Embed button
    embedBtn.addEventListener('click', () => {
        if (currentB64Image) {
            if (messageElement) {
                appendImageToChatMessage(messageElement, currentB64Image);
            } else {
                appendImageToActiveChat(currentB64Image);
            }
            if (window.toastr) window.toastr.success('Image embedded into chat');
            closeModal();
        }
    });
}

/**
 * Append generated image directly to a chat message DOM element
 */
function appendImageToChatMessage(messageElement, b64Url) {
    const textElement = messageElement.querySelector('.mes_text');
    if (textElement) {
        const imgWrap = document.createElement('div');
        imgWrap.className = 'lemon-chat-img-wrapper';
        imgWrap.style.marginTop = '10px';
        imgWrap.innerHTML = `<img src="${b64Url}" style="max-width: 100%; border-radius: 10px; cursor: pointer; box-shadow: 0 4px 12px rgba(0,0,0,0.3);" />`;
        textElement.appendChild(imgWrap);
    }
}

/**
 * Append image to the active chat stream
 */
function appendImageToActiveChat(b64Url) {
    const chatContainer = document.getElementById('chat');
    if (chatContainer) {
        const lastMsg = chatContainer.querySelector('.mes:last-child');
        if (lastMsg) {
            appendImageToChatMessage(lastMsg, b64Url);
        }
    }
}

/**
 * Add the 🎨 Visualizer action button to a message toolbar
 */
function addVisualizerButton(messageId) {
    const settings = getSettings();
    if (!settings.enable_msg_btn) return;

    const messageEl = document.querySelector(`.mes[mesid="${messageId}"]`);
    if (!messageEl) return;

    const buttonsBar = messageEl.querySelector('.mes_buttons');
    if (!buttonsBar || buttonsBar.querySelector('.lemon-msg-btn')) return;

    const btn = document.createElement('div');
    btn.className = 'lemon-msg-btn';
    btn.title = 'Visualizer: Generate an AI image for this scene';
    btn.innerHTML = '🎨';

    btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const textContent = messageEl.querySelector('.mes_text')?.textContent || '';
        // Extract dialog/action snippet as starter prompt
        const promptSnippet = textContent.replace(/<[^>]*>?/gm, '').slice(0, 300);
        openVisualizerModal(promptSnippet, messageEl);
    });

    buttonsBar.appendChild(btn);
}

/**
 * Register all Slash Commands
 */
function registerSlashCommands() {
    // /lemon <prompt>
    SlashCommandParser.addCommandObject(
        SlashCommand.fromProps({
            name: 'lemon',
            callback: async (args, value) => {
                const prompt = (value || args.prompt || '').trim();
                if (!prompt) return 'Please provide a prompt for /lemon.';
                try {
                    if (window.toastr) window.toastr.info(`Generating with ${getSettings().model}...`, 'Lemon Image Bridge');
                    const b64 = await generateImage(prompt);
                    appendImageToActiveChat(b64);
                    return '';
                } catch (err) {
                    if (window.toastr) window.toastr.error(err.message, 'Generation Failed');
                    return `Error: ${err.message}`;
                }
            },
            unnamedArgumentList: [
                SlashCommandArgument.fromProps({
                    description: 'Image prompt description',
                    typeList: [ARGUMENT_TYPE.STRING],
                    isRequired: true
                })
            ],
            helpString: 'Generate an image using the active Lemon Image Bridge provider and embed it in chat.'
        })
    );

    // Specific provider commands: /ezmaker, /freegen, /zimage, /redpanda, /bing
    const providers = ['ezmaker', 'freegen', 'zimage', 'redpanda', 'bing'];
    for (const provider of providers) {
        SlashCommandParser.addCommandObject(
            SlashCommand.fromProps({
                name: provider,
                callback: async (args, value) => {
                    const prompt = (value || args.prompt || '').trim();
                    if (!prompt) return `Please provide a prompt for /${provider}.`;
                    try {
                        if (window.toastr) window.toastr.info(`Generating with ${provider.toUpperCase()}...`, 'Lemon Image Bridge');
                        const b64 = await generateImage(prompt, provider);
                        appendImageToActiveChat(b64);
                        return '';
                    } catch (err) {
                        if (window.toastr) window.toastr.error(err.message, 'Generation Failed');
                        return `Error: ${err.message}`;
                    }
                },
                unnamedArgumentList: [
                    SlashCommandArgument.fromProps({
                        description: `Prompt for ${provider}`,
                        typeList: [ARGUMENT_TYPE.STRING],
                        isRequired: true
                    })
                ],
                helpString: `Generate an image specifically using ${provider.toUpperCase()}.`
            })
        );
    }

    // /lemon-model <model>
    SlashCommandParser.addCommandObject(
        SlashCommand.fromProps({
            name: 'lemon-model',
            callback: (args, value) => {
                const model = (value || '').trim().toLowerCase();
                if (!providers.includes(model)) {
                    return `Unknown model '${model}'. Available: ${providers.join(', ')}`;
                }
                updateSettings({ model: model });
                if (window.toastr) window.toastr.success(`Active provider set to ${model}`, 'Lemon Image Bridge');
                return `Active provider set to ${model}`;
            },
            unnamedArgumentList: [
                SlashCommandArgument.fromProps({
                    description: 'Model name (freegen, ezmaker, zimage, redpanda, bing)',
                    typeList: [ARGUMENT_TYPE.STRING],
                    isRequired: true
                })
            ],
            helpString: 'Set the active image generation provider.'
        })
    );

    // /lemon-ratio <ratio>
    SlashCommandParser.addCommandObject(
        SlashCommand.fromProps({
            name: 'lemon-ratio',
            callback: (args, value) => {
                const ratio = (value || '').trim();
                if (!RATIO_DIMENSIONS[ratio]) {
                    return `Invalid ratio. Available: ${Object.keys(RATIO_DIMENSIONS).join(', ')}`;
                }
                updateSettings({ aspect_ratio: ratio });
                if (window.toastr) window.toastr.success(`Aspect ratio set to ${ratio}`, 'Lemon Image Bridge');
                return `Aspect ratio set to ${ratio}`;
            },
            unnamedArgumentList: [
                SlashCommandArgument.fromProps({
                    description: 'Aspect ratio (1:1, 16:9, 9:16, 4:3, 3:4)',
                    typeList: [ARGUMENT_TYPE.STRING],
                    isRequired: true
                })
            ],
            helpString: 'Set the default aspect ratio for image generations.'
        })
    );
}

/**
 * Initialize UI listeners in the Settings Drawer
 */
function initSettingsUI() {
    const settings = getSettings();

    // Server URL input
    const urlInput = document.getElementById('lemon_server_url');
    if (urlInput) {
        urlInput.value = settings.server_url;
        urlInput.addEventListener('input', (e) => {
            updateSettings({ server_url: e.target.value });
        });
    }

    // Ping button
    document.getElementById('lemon_test_conn_btn')?.addEventListener('click', () => checkServerHealth(false));

    // Model Cards
    const modelCards = document.querySelectorAll('.lemon-model-card');
    modelCards.forEach(card => {
        if (card.dataset.model === settings.model) card.classList.add('active');
        else card.classList.remove('active');

        card.addEventListener('click', () => {
            modelCards.forEach(c => c.classList.remove('active'));
            card.classList.add('active');
            updateSettings({ model: card.dataset.model });
        });
    });

    // Ratio Pills
    const ratioPills = document.querySelectorAll('.lemon-ratio-pill');
    ratioPills.forEach(pill => {
        if (pill.dataset.ratio === settings.aspect_ratio) pill.classList.add('active');
        else pill.classList.remove('active');

        pill.addEventListener('click', () => {
            ratioPills.forEach(p => p.classList.remove('active'));
            pill.classList.add('active');
            updateSettings({ aspect_ratio: pill.dataset.ratio });
        });
    });

    // Style preset
    const presetSelect = document.getElementById('lemon_style_preset');
    if (presetSelect) {
        presetSelect.value = settings.style_preset || '';
        presetSelect.addEventListener('change', (e) => {
            updateSettings({ style_preset: e.target.value });
        });
    }

    // Toggles
    const msgBtnToggle = document.getElementById('lemon_enable_msg_btn');
    if (msgBtnToggle) {
        msgBtnToggle.checked = !!settings.enable_msg_btn;
        msgBtnToggle.addEventListener('change', (e) => {
            updateSettings({ enable_msg_btn: e.target.checked });
        });
    }

    const charContextToggle = document.getElementById('lemon_auto_char_context');
    if (charContextToggle) {
        charContextToggle.checked = !!settings.auto_char_context;
        charContextToggle.addEventListener('change', (e) => {
            updateSettings({ auto_char_context: e.target.checked });
        });
    }

    const autoEmbedToggle = document.getElementById('lemon_auto_embed_chat');
    if (autoEmbedToggle) {
        autoEmbedToggle.checked = !!settings.auto_embed_chat;
        autoEmbedToggle.addEventListener('change', (e) => {
            updateSettings({ auto_embed_chat: e.target.checked });
        });
    }

    // Live Test Bench
    const testBtn = document.getElementById('lemon_test_gen_btn');
    const testPrompt = document.getElementById('lemon_test_prompt');
    const testResultArea = document.getElementById('lemon_test_result_area');

    testBtn?.addEventListener('click', async () => {
        const prompt = testPrompt?.value.trim();
        if (!prompt) {
            if (window.toastr) window.toastr.warning('Please enter a test prompt');
            return;
        }

        testBtn.disabled = true;
        testBtn.innerHTML = '<div class="lemon-spinner" style="width: 16px; height: 16px; border-width: 2px;"></div> Generating...';
        testResultArea.style.display = 'flex';
        testResultArea.innerHTML = '<div class="lemon-spinner"></div>';

        try {
            const b64 = await generateImage(prompt);
            testResultArea.innerHTML = `<img src="${b64}" alt="Generated image" style="max-height: 250px; border-radius: 8px;" />`;
            if (window.toastr) window.toastr.success('Test image generated successfully!', 'Lemon Image Bridge');
        } catch (err) {
            testResultArea.innerHTML = `<span style="color: #f87171; padding: 10px;">Error: ${err.message}</span>`;
            if (window.toastr) window.toastr.error(err.message, 'Generation Failed');
        } finally {
            testBtn.disabled = false;
            testBtn.innerHTML = '<span>✨ Generate Image</span>';
        }
    });

    // Check status quietly on load
    checkServerHealth(true);
}

// Module Entrypoint
jQuery(async () => {
    // Render extension settings template
    try {
        const template = await renderExtensionTemplateAsync('third-party/lemon-image-bridge', 'settings');
        $('#extensions_settings').append(template);
    } catch {
        try {
            const template = await renderExtensionTemplateAsync('lemon-image-bridge', 'settings');
            $('#extensions_settings').append(template);
        } catch (e) {
            console.warn('[Lemon Image Bridge] Could not render settings template automatically:', e);
        }
    }

    initSettingsUI();
    registerSlashCommands();

    // Attach message rendering hooks
    eventSource.on(event_types.CHARACTER_MESSAGE_RENDERED, (messageId) => addVisualizerButton(messageId));
    eventSource.on(event_types.USER_MESSAGE_RENDERED, (messageId) => addVisualizerButton(messageId));
    eventSource.on(event_types.APP_READY, () => checkServerHealth(true));
});
