import socket
from typing import List

class EndException(Exception):
    pass


class ByeException(Exception):
    pass


class UnknownCommand(Exception):
    pass


def bytes_to_int(data: bytes) -> int:
    return int.from_bytes(data, "little")


class ClientSocket:
    def __init__(self, ip: str = 'localhost', port: int = 5555):
        self._socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._ip = ip
        self._port = port
        self._connected = False
        self.connect_to_server(self._ip, self._port)
        print(f"socket: {self._socket}")


    def connect_to_server(self, ip, port):
        if not self._connected:
            self._socket.connect((ip, port))
            self._connected = True

    def _get_command(self) -> str:
        if not self._connected:
            self.connect_to_server(self._ip, self._port)
        data = bytes()
        while len(data) < 3:
            data += self._socket.recv(3 - len(data))
        return data.decode()

    def _get_message(self, length: int) -> int:
        if not self._connected:
            self.connect_to_server(self._ip, self._port)
        data: bytes = bytes()
        while len(data) < length:
            data += self._socket.recv(1 - len(data))
        return bytes_to_int(data)

    def _parse_message(self) -> List:
        command: str = self._get_command()
        if command == "END":
            raise EndException()
        if command == "BYE":
            raise ByeException()
        elif command not in ["SET", "HUM", "HME", "MAP", "UPD"]:
            raise ValueError("Command unknown")

        if command == "SET":
            return ["set", [self._get_message(1), self._get_message(1)]]

        if command == "HUM":
            humans = []
            nb = self._get_message(1)
            for i in range(nb):
                humans.append([self._get_message(1), self._get_message(1)])
            return ["hum", humans]

        if command == "HME":
            return ["hme", [self._get_message(1), self._get_message(1)]]

        if command == "MAP":
            map = []
            nb = self._get_message(1)
            for i in range(nb):
                map.append((self._get_message(1), self._get_message(1), self._get_message(1), self._get_message(1),
                            self._get_message(1)))
            return ["map", map]

        if command == "UPD":
            upd = []
            nb = self._get_message(1)
            for i in range(nb):
                upd.append((self._get_message(1), self._get_message(1), self._get_message(1), self._get_message(1),
                            self._get_message(1)))
            return ["upd", upd]

    def get_message(self) -> List:
        try:
            return self._parse_message()
        except OSError:
            return None
        except IOError as e:
            print(e)
        except EndException:
            raise
        except ByeException:
            raise

    def send_nme(self, name: str):
        if not self._connected:
            print("trying to connect to server")
            self.connect_to_server(self._ip, self._port)

        self._socket.send("NME".encode() + bytes([len(name)]) + name.encode())

    def send_mov(self, nb_moves: int, moves):
        message = bytes([nb_moves])
        for move in moves:
            for data in move:
                message += bytes([data])

        self._socket.send("MOV".encode() + message)
