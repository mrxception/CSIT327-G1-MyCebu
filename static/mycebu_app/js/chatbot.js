document.addEventListener("DOMContentLoaded", function () {
  var root = document.getElementById("chatbot-root");
  if (!root) return;

  var toggleBtn = document.getElementById("chatbot-toggle");
  var closeBtn = document.getElementById("chatbot-close");
  var panel = document.getElementById("chatbot-panel");
  var form = document.getElementById("chatbot-form");
  var input = document.getElementById("chatbot-input");
  var tabs = root.querySelectorAll(".chatbot-tab");
  var bodies = root.querySelectorAll(".chatbot-body");

  var chatBody = root.querySelector('.chatbot-body[data-view="chat"]');
  var historyBody = root.querySelector('.chatbot-body[data-view="history"]');
  var historyList = root.querySelector("[data-history-list]");
  var historyEmpty = root.querySelector("[data-history-empty]");

  var STORAGE_KEY = "mycebu_chat_conversations";

  var conversations = [];
  var currentConversationId = null;

  function loadState() {
    try {
      var raw = window.localStorage.getItem(STORAGE_KEY);
      if (!raw) return;
      var parsed = JSON.parse(raw);
      if (parsed && Array.isArray(parsed.conversations)) {
        conversations = parsed.conversations;
        currentConversationId = parsed.currentConversationId || null;
      }
    } catch (e) {}
  }

  function saveState() {
    try {
      window.localStorage.setItem(
        STORAGE_KEY,
        JSON.stringify({
          conversations: conversations,
          currentConversationId: currentConversationId
        })
      );
    } catch (e) {}
  }

  function ensureCleared(container) {
    if (!container.dataset.hasMessages) {
      container.innerHTML = "";
      container.dataset.hasMessages = "1";
    }
  }

  function renderMessage(target, sender, text) {
    ensureCleared(target);
    var el = document.createElement("div");
    el.className = sender === "user" ? "chatbot-msg user" : "chatbot-msg bot";
    el.textContent = text;
    target.appendChild(el);
    target.scrollTop = target.scrollHeight;
  }

  function isSameDay(a, b) {
    var d1 = new Date(a), d2 = new Date(b);
    return (
      d1.getFullYear() === d2.getFullYear() &&
      d1.getMonth() === d2.getMonth() &&
      d1.getDate() === d2.getDate()
    );
  }

  function formatTimestamp(ts) {
    var d = new Date(ts);
    return d.toLocaleString();
  }

  function renderConversationInChat(conv) {
    chatBody.innerHTML = "";
    chatBody.dataset.hasMessages = "1";
    conv.messages.forEach(function (m) {
      renderMessage(chatBody, m.sender, m.text);
    });
  }

  function getConversationById(id) {
    return conversations.find(c => c.id === id) || null;
  }

  function createConversation(initialText) {
    var now = Date.now();
    var id = "c_" + now.toString(36) + Math.random().toString(36).slice(2, 8);
    var conv = {
      id,
      title: initialText.slice(0, 40),
      createdAt: now,
      updatedAt: now,
      messages: []
    };
    conversations.unshift(conv);
    currentConversationId = id;
    saveState();
    return conv;
  }

  function getOrCreateCurrentConversation(initialText) {
    var now = Date.now();
    if (currentConversationId) {
      var conv = getConversationById(currentConversationId);
      if (conv && isSameDay(conv.createdAt, now)) return conv;
    }
    return createConversation(initialText);
  }

  function updateConversationMeta(conv) {
    conv.updatedAt = Date.now();
    saveState();
  }

  function renderHistory() {
    historyList.innerHTML = "";
    if (conversations.length === 0) {
      historyEmpty.style.display = "block";
      return;
    }
    historyEmpty.style.display = "none";

    conversations.forEach(function (conv) {
      var item = document.createElement("button");
      item.type = "button";
      item.className =
        "chatbot-history-item" +
        (conv.id === currentConversationId ? " is-active" : "");
      item.setAttribute("data-conversation-id", conv.id);

      var title = document.createElement("div");
      title.className = "chatbot-history-title";
      title.textContent = conv.title || "Conversation";

      var meta = document.createElement("div");
      meta.className = "chatbot-history-meta";
      meta.textContent = formatTimestamp(conv.updatedAt);

      item.appendChild(title);
      item.appendChild(meta);

      historyList.appendChild(item);
    });
  }

  function setOpen(open) {
    if (open) {
      root.classList.add("is-open");
      renderHistory();
      setTimeout(() => input.focus(), 100);
    } else {
      root.classList.remove("is-open");
    }
  }

  loadState();
  renderHistory();
  if (currentConversationId) {
    var existing = getConversationById(currentConversationId);
    if (existing) renderConversationInChat(existing);
  }

  toggleBtn.addEventListener("click", () => setOpen(true));
  closeBtn.addEventListener("click", () => setOpen(false));

  tabs.forEach(tab => {
    tab.addEventListener("click", () => {
      var target = tab.getAttribute("data-tab");
      tabs.forEach(t => t.classList.remove("is-active"));
      tab.classList.add("is-active");

      bodies.forEach(body => {
        if (body.getAttribute("data-view") === target)
          body.classList.remove("chatbot-body--hidden");
        else body.classList.add("chatbot-body--hidden");
      });
    });
  });

  historyBody.addEventListener("click", function (e) {
    var item = e.target.closest(".chatbot-history-item");
    if (!item) return;
    var id = item.getAttribute("data-conversation-id");
    var conv = getConversationById(id);
    currentConversationId = id;
    saveState();
    renderConversationInChat(conv);
    renderHistory();
    tabs[0].click();
  });

  function getInputText() {
    return input.innerText.trim();
  }

  function clearInput() {
    input.innerText = "";
  }

  // Auto-grow input
  input.addEventListener("input", function () {
    input.style.height = "auto";
    var max = 120;
    var newHeight = Math.min(input.scrollHeight, max);
    input.style.height = newHeight + "px";
  });

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var text = getInputText();
    if (!text) return;

    var conv = getOrCreateCurrentConversation(text);
    conv.messages.push({
      sender: "user",
      text,
      timestamp: Date.now()
    });

    updateConversationMeta(conv);
    renderMessage(chatBody, "user", text);

    clearInput();

    setTimeout(function () {
      var reply = "This is a testing reply, testing rani siya";
      conv.messages.push({
        sender: "bot",
        text: reply,
        timestamp: Date.now()
      });
      updateConversationMeta(conv);
      renderMessage(chatBody, "bot", reply);
    }, 400);
  });
});
