import { io, type Socket } from "socket.io-client";

import { SOCKET_URL } from "./constants";

let socket: Socket | null = null;

export function getSocket() {
  if (!socket) {
    socket = io(SOCKET_URL, {
      autoConnect: false,
      transports: ["websocket", "polling"],
      reconnectionAttempts: 10,
      reconnectionDelay: 1000
    });
  }
  return socket;
}
