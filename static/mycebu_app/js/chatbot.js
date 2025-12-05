document.addEventListener('DOMContentLoaded', () => {
  // 1. SELECTORS
  const root = document.getElementById('chatbot-root');
  const toggleBtn = document.getElementById('chatbot-toggle');
  const closeBtn = document.getElementById('chatbot-close');
  const newChatBtn = document.getElementById('chatbot-new-chat');
  const panel = document.getElementById('chatbot-panel');
  const form = document.getElementById('chatbot-form');
  const input = document.getElementById('chatbot-input');
  const tabs = document.querySelectorAll('.chatbot-tab');
  const views = document.querySelectorAll('.chatbot-body');
  const chatView = document.querySelector('.chatbot-body[data-view="chat"]');
  const historyList = document.querySelector('[data-history-list]');

  // STATE
  let currentConversationId = null;

  // 2. INITIALIZE & RESTORE
  restoreChatSession();

  // 3. HELPER: COOKIES
  function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
      const cookies = document.cookie.split(';');
      for (let i = 0; i < cookies.length; i++) {
        const cookie = cookies[i].trim();
        if (cookie.substring(0, name.length + 1) === (name + '=')) {
          cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
          break;
        }
      }
    }
    return cookieValue;
  }

  function scrollToBottom() {
    if (chatView) chatView.scrollTop = chatView.scrollHeight;
  }

  // 4. MARKDOWN PARSER
  function parseMarkdown(text) {
    if (!text) return '';
    let html = text
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/__(.*?)__/g, '<strong>$1</strong>')
      .replace(/^\s*\*\s+(.*)$/gm, '<li>$1</li>')
      .replace(/\n/g, '<br>');

    if (html.includes('<li>')) {
      html = html.replace(/(<li>.*<\/li>)/s, '<ul style="padding-left:20px; margin:5px 0;">$1</ul>');
    }
    return html;
  }

  // 5. TOGGLE CHAT
  function toggleChat() {
    root.classList.toggle('is-open');
    const isOpen = root.classList.contains('is-open');
    toggleBtn.setAttribute('aria-expanded', isOpen);
    panel.setAttribute('aria-hidden', !isOpen);
    if (isOpen) setTimeout(() => input.focus(), 100);
  }
  if (toggleBtn) toggleBtn.addEventListener('click', toggleChat);
  if (closeBtn) closeBtn.addEventListener('click', toggleChat);

  // 6. NEW CHAT (HARD RESET)
  function startNewChat() {
    currentConversationId = null;
    sessionStorage.removeItem('mycebu_chat_id');
    sessionStorage.removeItem('mycebu_chat_msgs');

    // Wipe UI
    chatView.innerHTML = `
                <div class="chatbot-message-placeholder" style="display:block;">
                    <p>How can we help you today?</p>
                </div>
            `;
    input.innerText = '';
    switchToChatTab();
    input.focus();
  }
  if (newChatBtn) newChatBtn.addEventListener('click', startNewChat);

  // 7. TAB SWITCHING
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('is-active'));
      tab.classList.add('is-active');
      const targetView = tab.getAttribute('data-tab');

      views.forEach(view => {
        if (view.getAttribute('data-view') === targetView) {
          view.classList.remove('chatbot-body--hidden');
        } else {
          view.classList.add('chatbot-body--hidden');
        }
      });

      if (targetView === 'history') {
        form.classList.add('hidden');
        loadHistoryList();
      } else {
        form.classList.remove('hidden');
      }
    });
  });

  function switchToChatTab() {
    tabs.forEach(t => t.classList.remove('is-active'));
    tabs[0].classList.add('is-active');
    views.forEach(v => v.classList.add('chatbot-body--hidden'));
    chatView.classList.remove('chatbot-body--hidden');
    form.classList.remove('hidden');
  }

  // 8. SEND MESSAGE
  if (input) {
    input.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        form.dispatchEvent(new Event('submit'));
      }
    });
  }

  if (form) {
    form.addEventListener('submit', async (e) => {
      e.preventDefault();
      const message = input.innerText.trim();
      if (!message) return;

      input.innerText = '';

      // Remove placeholder
      const placeholder = chatView.querySelector('.chatbot-message-placeholder');
      if (placeholder) placeholder.style.display = 'none';

      // Optimistic UI Update
      appendMessage(message, 'user');
      saveToStorage(message, 'user');

      const loadingId = appendLoading();

      try {
        const response = await fetch('/api/chat/send/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
          },
          body: JSON.stringify({
            prompt: message,
            conversation_id: currentConversationId
          })
        });

        const data = await response.json();
        removeLoading(loadingId);

        if (data.success) {
          if (data.conversation_id) {
            currentConversationId = data.conversation_id;
            sessionStorage.setItem('mycebu_chat_id', currentConversationId);
          }
          appendMessage(data.message, 'bot');
          saveToStorage(data.message, 'bot');
        } else {
          appendMessage("Error: " + (data.error || "Unknown error"), 'bot');
        }
      } catch (error) {
        removeLoading(loadingId);
        appendMessage("Network error.", 'bot');
      }
    });
  }

  // 9. RENDER UI HELPERS
  function appendMessage(text, type) {
    const msgDiv = document.createElement('div');
    msgDiv.style.display = 'flex';
    msgDiv.style.justifyContent = type === 'user' ? 'flex-end' : 'flex-start';
    msgDiv.style.width = '100%';
    msgDiv.style.marginBottom = '8px';

    const innerDiv = document.createElement('div');
    innerDiv.classList.add('chatbot-msg', type);
    innerDiv.innerHTML = parseMarkdown(text);

    msgDiv.appendChild(innerDiv);
    chatView.appendChild(msgDiv);
    scrollToBottom();
  }

  function appendLoading() {
    const id = 'loading-' + Date.now();
    const msgDiv = document.createElement('div');
    msgDiv.id = id;
    msgDiv.style.display = 'flex';
    msgDiv.style.justifyContent = 'flex-start';
    msgDiv.style.marginBottom = '8px';
    msgDiv.innerHTML = `<div class="chatbot-msg bot">Typing...</div>`;
    chatView.appendChild(msgDiv);
    scrollToBottom();
    return id;
  }

  function removeLoading(id) {
    const el = document.getElementById(id);
    if (el) el.remove();
  }

  // 10. HISTORY LIST
  async function loadHistoryList() {
    if (!historyList) return;
    historyList.innerHTML = '<div style="padding:10px; font-size:0.8rem;">Loading...</div>';

    try {
      const response = await fetch('/api/chat/history/');
      const data = await response.json();
      historyList.innerHTML = '';

      if (data.success && data.history.length > 0) {
        document.querySelector('[data-history-empty]').style.display = 'none';
        data.history.forEach(session => {
          const itemDiv = document.createElement('div');
          itemDiv.classList.add('chatbot-history-item');
          const date = new Date(session.date).toLocaleDateString();

          itemDiv.innerHTML = `
                            <div style="font-weight:600; color:#333;">${session.title}</div>
                            <div style="font-size:0.7rem; color:#999; margin-top:4px;">${date}</div>
                        `;

          // ON CLICK: LOAD SESSION
          itemDiv.addEventListener('click', () => {
            loadFullSession(session.conversation_id);
          });

          historyList.appendChild(itemDiv);
        });
      } else {
        historyList.innerHTML = '';
        document.querySelector('[data-history-empty]').style.display = 'block';
      }
    } catch (error) {
      historyList.innerHTML = '<div style="padding:10px; color:red;">Failed to load.</div>';
    }
  }

  // 11. HISTORY DETAIL (FIXED APPEND BUG)
  async function loadFullSession(conversationId) {
    // A. CLEAR SCREEN IMMEDIATELY
    chatView.innerHTML = '';

    // Re-add placeholder (hidden) for structure
    const placeholder = document.createElement('div');
    placeholder.className = 'chatbot-message-placeholder';
    placeholder.style.display = 'none';
    chatView.appendChild(placeholder);

    // B. SHOW LOADING & SWITCH TAB
    const loadingId = appendLoading();
    switchToChatTab();

    try {
      // C. FETCH
      const response = await fetch(`/api/chat/session/${conversationId}/`);
      const data = await response.json();

      // D. REMOVE LOADING
      removeLoading(loadingId);

      if (data.success) {
        // E. SET STATE
        currentConversationId = conversationId;
        sessionStorage.setItem('mycebu_chat_id', currentConversationId);

        // Clear persistence cache and rebuild it
        sessionStorage.removeItem('mycebu_chat_msgs');
        let newStorage = [];

        // F. RENDER MESSAGES
        if (data.messages && data.messages.length > 0) {
          data.messages.forEach(msg => {
            // Backend now sends {text: "...", type: "user/bot"}
            // Check keys: views.py sends 'text', 'type' in updated view
            // If using older view, it sends 'user_message', 'bot_response'
            if (msg.type) {
              appendMessage(msg.text, msg.type);
              newStorage.push({ text: msg.text, type: msg.type });
            } else {
              // Fallback for safety
              appendMessage(msg.user_message, 'user');
              appendMessage(msg.bot_response, 'bot');
              newStorage.push({ text: msg.user_message, type: 'user' });
              newStorage.push({ text: msg.bot_response, type: 'bot' });
            }
          });
        }

        // G. SAVE TO STORAGE
        sessionStorage.setItem('mycebu_chat_msgs', JSON.stringify(newStorage));
      } else {
        appendMessage("Could not load conversation.", 'bot');
      }
    } catch (e) {
      removeLoading(loadingId);
      console.error(e);
      appendMessage("Failed to load history item.", 'bot');
    }
  }

  // 12. STORAGE UTILS
  function saveToStorage(text, type) {
    let conversation = JSON.parse(sessionStorage.getItem('mycebu_chat_msgs') || '[]');
    conversation.push({ text: text, type: type });
    sessionStorage.setItem('mycebu_chat_msgs', JSON.stringify(conversation));
  }

  function restoreChatSession() {
    currentConversationId = sessionStorage.getItem('mycebu_chat_id');
    let conversation = JSON.parse(sessionStorage.getItem('mycebu_chat_msgs') || '[]');

    if (conversation.length > 0) {
      const placeholder = chatView.querySelector('.chatbot-message-placeholder');
      if (placeholder) placeholder.style.display = 'none';

      conversation.forEach(msg => {
        appendMessage(msg.text, msg.type);
      });
    }
  }
});