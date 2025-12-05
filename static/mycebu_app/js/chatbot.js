document.addEventListener('DOMContentLoaded', () => {
  // 1. SELECTORS
  const root = document.getElementById('chatbot-root');
  const toggleBtn = document.getElementById('chatbot-toggle');
  const closeBtn = document.getElementById('chatbot-close');
  const newChatBtn = document.getElementById('chatbot-new-chat'); // New Chat Button
  const panel = document.getElementById('chatbot-panel');
  const form = document.getElementById('chatbot-form');
  const input = document.getElementById('chatbot-input');
  const tabs = document.querySelectorAll('.chatbot-tab');
  const views = document.querySelectorAll('.chatbot-body');
  const chatView = document.querySelector('.chatbot-body[data-view="chat"]');
  const historyList = document.querySelector('[data-history-list]');

  // 2. HELPER: COOKIES
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

  // 3. RESTORE CHAT FROM SESSION STORAGE
  restoreChatSession();

  // 4. NEW CHAT LOGIC (Clears everything)
  function startNewChat() {
    // Clear UI
    chatView.innerHTML = `
                <div class="chatbot-message-placeholder" style="display:block;">
                    <p>This is a preview of the MyCebu assistant. Type a question below to start a conversation.</p>
                </div>
            `;
    input.innerText = '';

    // Clear Storage
    sessionStorage.removeItem('mycebu_chat');

    // Switch to chat tab if not there
    switchToChatTab();
    input.focus();
  }

  if (newChatBtn) newChatBtn.addEventListener('click', startNewChat);

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

  // 6. TAB SWITCHING
  tabs.forEach(tab => {
    tab.addEventListener('click', () => {
      tabs.forEach(t => t.classList.remove('is-active'));
      tab.classList.add('is-active');
      const targetView = tab.getAttribute('data-tab');

      // Toggle Views
      views.forEach(view => {
        if (view.getAttribute('data-view') === targetView) {
          view.classList.remove('chatbot-body--hidden');
        } else {
          view.classList.add('chatbot-body--hidden');
        }
      });

      // Toggle Input Bar visibility (Hide on history tab)
      if (targetView === 'history') {
        form.classList.add('hidden');
        loadHistory();
      } else {
        form.classList.remove('hidden');
      }
    });
  });

  function switchToChatTab() {
    tabs.forEach(t => t.classList.remove('is-active'));
    tabs[0].classList.add('is-active'); // Assume 0 is Chat

    views.forEach(v => v.classList.add('chatbot-body--hidden'));
    chatView.classList.remove('chatbot-body--hidden');

    form.classList.remove('hidden'); // Show input
  }

  // 7. SEND MESSAGE
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

      // Hide placeholder
      const placeholder = chatView.querySelector('.chatbot-message-placeholder');
      if (placeholder) placeholder.style.display = 'none';

      appendMessage(message, 'user');
      saveMessageToStorage(message, 'user');

      const loadingId = appendLoading();

      try {
        const response = await fetch('/api/chat/send/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCookie('csrftoken')
          },
          body: JSON.stringify({ prompt: message })
        });

        const data = await response.json();
        removeLoading(loadingId);

        if (data.success) {
          appendMessage(data.message, 'bot');
          saveMessageToStorage(data.message, 'bot');
        } else {
          appendMessage("Error: " + (data.error || "Unknown error"), 'bot');
        }
      } catch (error) {
        removeLoading(loadingId);
        appendMessage("Network error. Please try again later.", 'bot');
        console.error(error);
      }
    });
  }

  // 8. RENDER HELPERS
  function appendMessage(text, type) {
    const msgDiv = document.createElement('div');
    msgDiv.style.display = 'flex';
    msgDiv.style.justifyContent = type === 'user' ? 'flex-end' : 'flex-start';
    msgDiv.style.width = '100%';
    msgDiv.style.marginBottom = '8px';

    const innerDiv = document.createElement('div');
    innerDiv.classList.add('chatbot-msg', type);
    innerDiv.innerHTML = text.replace(/\n/g, '<br>');

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

  // 9. HISTORY LOGIC
  async function loadHistory() {
    if (!historyList) return;
    historyList.innerHTML = '<div style="padding:10px; font-size:0.8rem;">Loading...</div>';

    try {
      const response = await fetch('/api/chat/history/');
      const data = await response.json();
      historyList.innerHTML = '';

      if (data.success && data.history.length > 0) {
        document.querySelector('[data-history-empty]').style.display = 'none';
        data.history.forEach(item => {
          const itemDiv = document.createElement('div');
          itemDiv.classList.add('chatbot-history-item');
          const date = new Date(item.created_at).toLocaleDateString();

          itemDiv.innerHTML = `
                            <div style="font-weight:600;">You: ${item.user_message.substring(0, 20)}...</div>
                            <div style="color:#666;">Bot: ${item.bot_response.substring(0, 30)}...</div>
                            <div style="font-size:0.7rem; color:#999; margin-top:4px;">${date}</div>
                        `;

          // ON CLICK: Clear Chat -> Load this item
          itemDiv.addEventListener('click', () => {
            loadHistoryToChat(item.user_message, item.bot_response);
          });

          historyList.appendChild(itemDiv);
        });
      } else {
        historyList.innerHTML = '';
        document.querySelector('[data-history-empty]').style.display = 'block';
      }
    } catch (error) {
      historyList.innerHTML = '<div style="padding:10px; color:red;">Failed to load history.</div>';
    }
  }

  function loadHistoryToChat(userMsg, botMsg) {
    // 1. Clear Current Chat
    chatView.innerHTML = ''; // This wipes the previous messages

    // 2. Hide Placeholder (if it exists in the markup, it's gone now, but standard safety)
    const placeholder = document.createElement('div'); // Recreate invisible placeholder for logic consistency
    placeholder.className = 'chatbot-message-placeholder';
    placeholder.style.display = 'none';
    chatView.appendChild(placeholder);

    // 3. Append Selected Messages
    appendMessage(userMsg, 'user');
    appendMessage(botMsg, 'bot');

    // 4. Overwrite Storage (So it persists if you reload)
    sessionStorage.removeItem('mycebu_chat');
    saveMessageToStorage(userMsg, 'user');
    saveMessageToStorage(botMsg, 'bot');

    // 5. Switch Tabs
    switchToChatTab();
  }

  // 10. STORAGE HELPERS
  function saveMessageToStorage(text, type) {
    let conversation = JSON.parse(sessionStorage.getItem('mycebu_chat') || '[]');
    conversation.push({ text: text, type: type });
    sessionStorage.setItem('mycebu_chat', JSON.stringify(conversation));
  }

  function restoreChatSession() {
    let conversation = JSON.parse(sessionStorage.getItem('mycebu_chat') || '[]');
    if (conversation.length > 0) {
      const placeholder = chatView.querySelector('.chatbot-message-placeholder');
      if (placeholder) placeholder.style.display = 'none';

      conversation.forEach(msg => {
        appendMessage(msg.text, msg.type);
      });
    }
  }
});