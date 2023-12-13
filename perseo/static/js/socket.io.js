// Socket.IO
var socket = io();
socket.on("connect", function () {
  socket.emit("test", { data: "I'm connected!" });
});
