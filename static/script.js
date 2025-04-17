document.getElementById('send-btn').addEventListener('click', sendMessage);
document.getElementById('user-input').addEventListener('keypress', function (e) {
    if (e.key === 'Enter') sendMessage();
});

let currentSession = {};

function sendMessage() {
    const inputBox = document.getElementById('user-input');
    const message = inputBox.value.trim();
    if (!message) return;

    appendMessage(message, 'user');
    inputBox.value = '';

    fetch("/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json"
        },
        body: JSON.stringify({
          message: message,
          session: currentSession
        })
    })
    .then(res => res.json())
    .then(data => {
        console.log("Bot:", data.response);
        appendMessage(data.response, 'bot');
        currentSession = data.session;
    })
    .catch(err => console.error("Error:", err));
}

function appendMessage(msg, sender) {
    const msgEl = document.createElement('div');
    msgEl.className = sender === 'user' ? 'user-msg' : 'bot-msg';
    msgEl.innerText = msg;
    document.getElementById('chat-box').appendChild(msgEl);
    document.getElementById('chat-box').scrollTop = document.getElementById('chat-box').scrollHeight;
}
