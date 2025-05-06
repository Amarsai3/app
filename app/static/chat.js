const socket = io();

function joinChat(room) {
    socket.emit('join', { room });
}

function sendMessage() {
    const messageInput = document.getElementById("message");
    const message = messageInput.value;
    const room = "{{ joined_room }}";
    const username = "{{ username }}";

    if (message.trim() !== "") {
        socket.emit("send_message", {
            username,
            room,
            message
        });
        messageInput.value = "";
    }
}

socket.on("receive_message", function(data) {
    const messages = document.getElementById("messages");
    const li = document.createElement("li");
    li.textContent = `${data.username}: ${data.message}`;
    messages.appendChild(li);
});
