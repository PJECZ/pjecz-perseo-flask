// Socket.IO
const socket = io();
socket.on("connect", function (data) {
  console.log("Connected to the server!");
});
socket.send("Hello!");
