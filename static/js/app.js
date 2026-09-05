/* ═══════════════════════════════════════════════════════════════
   AgenticMart — Dashboard JavaScript
   Chat, real-time audit, mandate visualization, AI buyer demo
   ═══════════════════════════════════════════════════════════════ */

// ── State ──────────────────────────────────────────────────────
let isProcessing = false;
let lastAuditId = 0;
let selectedPersona = 'grocery_shopper';
let aiBuyerPolling = null;
let auditPolling = null;

// ── DOM Refs ───────────────────────────────────────────────────
const chatMessages = document.getElementById('chatMessages');
const chatInput = document.getElementById('chatInput');
const btnSend = document.getElementById('btnSend');
const loadingOverlay = document.getElementById('loadingOverlay');

// ── Chat ───────────────────────────────────────────────────────

function addMessage(role, text) {
    // Remove welcome screen on first message
    const welcome = chatMessages.querySelector('.chat-welcome');
    if (welcome) welcome.remove();

    const div = document.createElement('div');
    const avatarEmoji = role === 'user' ? '🧑' : role === 'system' ? '⚠️' : '🤖';
    const roleClass = role === 'user' ? 'message-user' : role === 'system' ? 'message-system' : 'message-assistant';

    // Convert markdown-like formatting
    let html = text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\n/g, '<br>');

    div.className = `message ${roleClass}`;
    div.innerHTML = `
        <div class="message-avatar">${avatarEmoji}</div>
        <div class="message-content">${html}</div>
    `;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function addThinking() {
    const div = document.createElement('div');
    div.className = 'message message-assistant';
    div.id = 'thinkingIndicator';
    div.innerHTML = `
        <div class="message-avatar">🤖</div>
        <div class="thinking">
            <div class="thinking-dots"><span></span><span></span><span></span></div>
            Thinking...
        </div>
    `;
    chatMessages.appendChild(div);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

function removeThinking() {
    const el = document.getElementById('thinkingIndicator');
    if (el) el.remove();
}

async function sendMessage(text) {
    if (isProcessing) return;

    const message = text || chatInput.value.trim();
    if (!message) return;

    chatInput.value = '';
    addMessage('user', message);

    isProcessing = true;
    btnSend.disabled = true;
    addThinking();

    try {
        const resp = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message }),
        });

        const data = await resp.json();
        removeThinking();

        if (data.error) {
            addMessage('system', data.response);
        } else {
            addMessage('assistant', data.response);
        }

        if (data.session) {
            updateSessionState(data.session);
        }
    } catch (err) {
        removeThinking();
        addMessage('system', `Connection error: ${err.message}`);
    } finally {
        isProcessing = false;
        btnSend.disabled = false;
        chatInput.focus();
    }
}

// Enter key handler
chatInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        sendMessage();
    }
});

// ── Voice Input (Speech Recognition) ───────────────────────────
const btnVoice = document.getElementById('btnVoice');
let recognition = null;
if ('webkitSpeechRecognition' in window || 'SpeechRecognition' in window) {
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    recognition = new SpeechRecognition();
    recognition.continuous = false;
    recognition.interimResults = false;
    recognition.lang = 'en-US';

    recognition.onstart = () => {
        btnVoice.classList.add('recording');
        btnVoice.innerHTML = '<span class="btn-icon" style="color: var(--danger)">🔴</span>';
        chatInput.placeholder = 'Listening...';
    };

    recognition.onresult = (event) => {
        const transcript = event.results[0][0].transcript;
        chatInput.value = transcript;
        sendMessage();
    };

    recognition.onerror = (event) => {
        console.error('Speech recognition error', event.error);
        resetVoiceBtn();
    };

    recognition.onend = () => {
        resetVoiceBtn();
    };
} else {
    btnVoice.style.display = 'none'; // Hide if not supported
}

function resetVoiceBtn() {
    btnVoice.classList.remove('recording');
    btnVoice.innerHTML = '<span class="btn-icon">🎤</span>';
    chatInput.placeholder = 'Type or speak your message...';
}

btnVoice.addEventListener('click', () => {
    if (!recognition) return;
    if (btnVoice.classList.contains('recording')) {
        recognition.stop();
    } else {
        recognition.start();
    }
});

// ── Session State ──────────────────────────────────────────────

function updateSessionState(session) {
    // Spend bar
    const pct = session.spend_pct || 0;
    const fill = document.getElementById('spendBarFill');
    fill.style.width = `${pct}%`;
    fill.className = 'metric-bar-fill' +
        (pct > 80 ? ' danger' : pct > 60 ? ' warning' : '');

    document.getElementById('spendValue').textContent =
        `${session.session_spent_display} / ${session.session_cap_display}`;

    // Cart count
    document.getElementById('cartCount').textContent =
        session.cart?.item_count || 0;

    // Upsell rate
    document.getElementById('upsellRate').textContent =
        session.upsell?.acceptance_rate_display || '0%';

    // Orders
    document.getElementById('orderCount').textContent =
        session.orders?.length || 0;

    // Mandates
    if (session.current_mandate) {
        updateMandateChain(session.current_mandate);
    }
}

// ── Mandate Chain Visualization ────────────────────────────────

function updateMandateChain(chain) {
    const intentCard = document.getElementById('mandateIntent');
    const cartCard = document.getElementById('mandateCart');
    const paymentCard = document.getElementById('mandatePayment');
    const arrow1 = document.getElementById('arrow1');
    const arrow2 = document.getElementById('arrow2');

    // Reset classes
    [intentCard, cartCard, paymentCard].forEach(c => {
        c.classList.remove('active', 'completed', 'blocked');
    });
    [arrow1, arrow2].forEach(a => {
        a.classList.remove('active', 'completed');
    });

    // Intent
    if (chain.intent) {
        const i = chain.intent;
        intentCard.classList.add(i.status === 'resolved' ? 'completed' : 'active');
        document.getElementById('intentStatus').textContent = i.status;
        document.getElementById('intentStatus').className = `mandate-status status-${i.status}`;
        document.getElementById('intentDetail').textContent = i.parsed_intent || i.raw_request;
        arrow1.classList.add(i.status === 'resolved' ? 'completed' : 'active');
    }

    // Cart
    if (chain.cart) {
        const c = chain.cart;
        const status = c.status;
        cartCard.classList.add(status === 'finalized' ? 'completed' : 'active');
        document.getElementById('cartStatus').textContent = status;
        document.getElementById('cartStatus').className = `mandate-status status-${status}`;
        document.getElementById('cartDetail').textContent =
            `${c.items?.length || 0} items — ${c.total_display}`;
        arrow2.classList.add(status === 'finalized' ? 'completed' : 'active');
    }

    // Payment
    if (chain.payment) {
        const p = chain.payment;
        const status = p.status;
        paymentCard.classList.add(
            status === 'completed' || status === 'approved' ? 'completed' :
            status === 'blocked' ? 'blocked' : 'active'
        );
        document.getElementById('paymentStatus').textContent = status;
        document.getElementById('paymentStatus').className = `mandate-status status-${status}`;

        let detail = p.amount_display;
        if (p.razorpay_order_id) detail += ` — ${p.razorpay_order_id}`;
        else if (status === 'blocked') detail = '⚠️ Policy blocked';
        document.getElementById('paymentDetail').textContent = detail;
    }
}

// ── Audit Trail ────────────────────────────────────────────────

async function pollAudit() {
    try {
        const resp = await fetch('/api/audit?limit=200');
        const data = await resp.json();

        if (!data.events || data.events.length === 0) return;

        const latestId = Math.max(...data.events.map(e => e.id));
        if (latestId <= lastAuditId) return; // no new events

        renderAuditLog(data.events);
        lastAuditId = latestId;
        document.getElementById('auditCount').textContent = `${data.count} events`;
    } catch (err) {
        // silent fail on polling
    }
}

function renderAuditLog(events) {
    const log = document.getElementById('auditLog');
    log.innerHTML = '';

    // Show most recent first (events are already in order from API)
    const displayEvents = events.slice(-100).reverse();

    displayEvents.forEach(event => {
        const entry = document.createElement('div');
        entry.className = 'audit-entry';

        const actor = event.actor || 'unknown';
        const action = event.action || '';
        const reason = event.reason || '';
        const outcome = event.rule_outcome || 'n/a';
        const amount = event.amount ? ` [₹${(event.amount / 100).toFixed(0)}]` : '';

        const outcomeClass = outcome === 'allowed' ? 'outcome-allowed' :
                             outcome === 'blocked' ? 'outcome-blocked' : 'outcome-na';

        entry.innerHTML = `
            <span class="audit-actor actor-${actor}">${actor}${amount}</span>
            <span class="audit-action" title="${action}">${action}</span>
            <span class="audit-reason" title="${reason}">${reason}</span>
            <span class="audit-outcome ${outcomeClass}">${outcome}</span>
        `;
        log.appendChild(entry);
    });
}

// ── AI Buyer ───────────────────────────────────────────────────

function selectPersona(btn) {
    document.querySelectorAll('.persona-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    selectedPersona = btn.dataset.persona;
}

async function launchAIBuyer() {
    const btn = document.getElementById('btnLaunchAI');
    const badge = document.getElementById('aiBuyerBadge');
    const convDiv = document.getElementById('aiConversation');
    const controls = document.getElementById('aiBuyerControls');

    btn.disabled = true;
    btn.textContent = '⏳ Running...';
    badge.textContent = 'Running';
    badge.className = 'panel-badge badge-running';
    convDiv.style.display = 'flex';
    convDiv.innerHTML = '<div class="ai-msg ai-msg-merchant">Starting AI buyer agent...</div>';

    try {
        const resp = await fetch('/api/ai-buyer/start', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ persona: selectedPersona }),
        });

        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || 'Failed to start');
        }

        // Start polling for AI buyer status
        aiBuyerPolling = setInterval(pollAIBuyer, 2000);
    } catch (err) {
        btn.disabled = false;
        btn.textContent = '🚀 Launch AI Buyer Demo';
        badge.textContent = 'Error';
        badge.className = 'panel-badge';
        convDiv.innerHTML = `<div class="ai-msg ai-msg-merchant" style="color: var(--danger)">Error: ${err.message}</div>`;
    }
}

async function pollAIBuyer() {
    try {
        const resp = await fetch('/api/ai-buyer/status');
        const data = await resp.json();

        const convDiv = document.getElementById('aiConversation');
        const badge = document.getElementById('aiBuyerBadge');
        const btn = document.getElementById('btnLaunchAI');

        // Render conversation
        if (data.conversation && data.conversation.length > 0) {
            convDiv.innerHTML = '';
            data.conversation.forEach(msg => {
                const div = document.createElement('div');
                const role = msg.role === 'buyer' ? 'buyer' : 'merchant';
                div.className = `ai-msg ai-msg-${role}`;

                const label = role === 'buyer' ? `🤖 ${data.persona?.name || 'Buyer'}` : '🏪 Merchant';
                div.innerHTML = `<strong>${label}:</strong> ${msg.message.substring(0, 300)}${msg.message.length > 300 ? '...' : ''}`;
                convDiv.appendChild(div);
            });
            convDiv.scrollTop = convDiv.scrollHeight;
        }

        // Check if done
        if (data.status !== 'running') {
            clearInterval(aiBuyerPolling);
            aiBuyerPolling = null;

            badge.textContent = data.status === 'completed' ? 'Completed ✓' : 'Failed';
            badge.className = data.status === 'completed'
                ? 'panel-badge'
                : 'panel-badge';
            badge.style.background = data.status === 'completed'
                ? 'rgba(16, 185, 129, 0.15)' : 'rgba(239, 68, 68, 0.15)';
            badge.style.color = data.status === 'completed'
                ? 'var(--success)' : 'var(--danger)';

            btn.disabled = false;
            btn.textContent = '🚀 Launch AI Buyer Demo';
        }
    } catch (err) {
        // silent fail
    }
}

// ── Reset Session ──────────────────────────────────────────────

document.getElementById('btnReset').addEventListener('click', async () => {
    if (!confirm('Reset the shopping session? This clears your cart and conversation.')) return;

    try {
        await fetch('/api/session/reset', { method: 'POST' });

        // Reset UI
        chatMessages.innerHTML = `
            <div class="chat-welcome">
                <div class="welcome-icon">🤖</div>
                <h3>Welcome to AgenticMart!</h3>
                <p>I'm your AI shopping assistant. Search for products, build your cart, and checkout — all through conversation.</p>
                <div class="welcome-suggestions">
                    <button class="suggestion-chip" onclick="sendMessage('Show me all snacks')">🍫 Browse snacks</button>
                    <button class="suggestion-chip" onclick="sendMessage('I need groceries for the week')">🛒 Weekly groceries</button>
                    <button class="suggestion-chip" onclick="sendMessage('What electronics do you have?')">🔌 Electronics</button>
                    <button class="suggestion-chip" onclick="sendMessage('Show me your best deals')">💰 Best deals</button>
                </div>
            </div>`;

        // Reset mandate viz
        ['mandateIntent', 'mandateCart', 'mandatePayment'].forEach(id => {
            const el = document.getElementById(id);
            el.classList.remove('active', 'completed', 'blocked');
        });
        ['arrow1', 'arrow2'].forEach(id => {
            const el = document.getElementById(id);
            el.classList.remove('active', 'completed');
        });
        document.getElementById('intentStatus').textContent = 'Waiting';
        document.getElementById('cartStatus').textContent = 'Waiting';
        document.getElementById('paymentStatus').textContent = 'Waiting';
        document.getElementById('intentDetail').textContent = "Buyer's request will appear here";
        document.getElementById('cartDetail').textContent = 'Proposed items will appear here';
        document.getElementById('paymentDetail').textContent = 'Approval status will appear here';

        // Reset metrics
        document.getElementById('spendBarFill').style.width = '0%';
        document.getElementById('spendValue').textContent = '₹0 / ₹2,000';
        document.getElementById('cartCount').textContent = '0';
        document.getElementById('upsellRate').textContent = '0%';
        document.getElementById('orderCount').textContent = '0';
    } catch (err) {
        alert('Failed to reset session');
    }
});

// ── Initialize ─────────────────────────────────────────────────

// Start polling audit log every 2 seconds
auditPolling = setInterval(pollAudit, 2000);

// Initial state fetch
(async () => {
    try {
        const resp = await fetch('/api/session');
        const data = await resp.json();
        updateSessionState(data);
    } catch (err) {
        // Server might not be ready yet
    }
    // Initial audit fetch
    pollAudit();
})();

// Focus input
chatInput.focus();
