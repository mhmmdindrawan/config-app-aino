import serial # type: ignore
from datetime import datetime
from time import sleep

class DebitTransactionException(Exception):
    def __init__(self, result):
        super().__init__(str(result))
        self.result = result
        if isinstance(result, dict):
            self.status = result.get("status")
            self.response_as_hex = result.get("response_ashex")
            self.amount = result.get("amount")
        else:
            self.status = (result, "status", None)
            self.response_as_hex = (result, "status", None)
            self.amount = (result, "status", None)

class Aino:
    def __init__(self) -> None:
        self.port = "COM3"
        self.ser = None
        self.baud_rate = 115200
        self.pos_id = 2
        self.is_ready: bool = True
        self.last_debit_transaction = None

    def set_config(self, port: str, baud_rate: int, pos_id: str) -> None:
        self.port = port
        self.baud_rate = baud_rate
        self.pos_id = pos_id
        try:
            self.ser = serial.Serial(port, baud_rate, timeout=3)
        except serial.SerialException as e:
            print(f"Error opening serial port {port}: {e}")
            self.is_ready = False

    def __serial_check(self) -> None:
        if self.ser and self.ser.is_open:
            print(f"Serial port {self.port} is open.")
        else:
            print(f"Serial port {self.port} is not open or not initialized.")
            self.is_ready = False

    def start_serial(self) -> None:
        def begin() -> None:
            self.ser = serial.Serial(
                self.port,
                self.baud_rate,
                timeout=3
            )
            print("Serial port telah dibuka.")

        if self.ser:
            if not self.ser.is_open:
                print("Serial port tidak terbuka. Mencoba membuka...")
                begin()
            else:
                print("Serial port sudah terbuka. Menutup dan membuka kembali...")
                self.ser.close()
                sleep(1)
                begin()
        else:
            print("Serial port belum diinisialisasi. Mencoba inisialisasi...")
            begin()

    def close_connection(self) -> None:
            self.ser.close()

    def __get_status(self, byte_string: bytes) -> str:
        status_dict = {
            (0x01, 0x00): "Transaction Success",
            (0x01, 0x01): "Transaction Failed",
            (0x01, 0x02): "Lost Contact",
            (0x01, 0x03): "Not enough balance",
            (0x01, 0x04): "Request Timeout",
            (0x01, 0x05): "Expired",
            (0x01, 0x06): "Not Active",
            (0x01, 0x07): "Same ID Transaction",
            (0x01, 0x08): "Mandiri Transaction < 10s",
            (0x01, 0x09): "BNI Expired Card",
            (0x01, 0x98): "Checksum Error",
            (0x01, 0x99): "Undefined",
            (0x02, 0x00): "Echo Success",
            (0x03, 0x00): "Get Last Transaction Success",
            (0x03, 0x01): "Get Last Transaction Failed",
            (0x04, 0x00): "Check Balance Success",
            (0x04, 0x01): "Check Balance Failed",
            (0x04, 0x04): "Request Timeout",
            (0x05, 0x00): "Member with CSN Success",
            (0x05, 0x01): "Member with CSN Failed",
            (0x06, 0x00): "Cancel Debit Success",
            (0x06, 0x01): "Cancel Debit Failed",
            (0x07, 0x00): "LinkAja Payment Success",
            (0x07, 0x01): "LinkAja Payment Failed",
            (0x07, 0x04): "LinkAja Payment Time Out",
            (0x07, 0x07): "LinkAja Order ID Existed",
            (0x08, 0x00): "Reversal Refund Success",
            (0x08, 0x01): "Reversal Refund LinkAja Failed Id Transaction not found",
            (0x08, 0x02): "Reversal Refund LinkAja Server Error",
            (0x08, 0x04): "Reversal Refund LinkAja TimeOut Server",
            (0x09, 0x00): "Check Status LinkAja Payment Paid",
            (0x09, 0x01): "Check Status LinkAja Payment Unpaid",
            (0x09, 0x02): "Check Status LinkAja Payment ID Transaction Not Exist",
            (0x09, 0x03): "Check Status LinkAja Payment Server Error",
            (0x09, 0x04): "Check Status LinkAja Payment Server Timeout",
            (0x09, 0x05): "Check Status LinkAja Payment Expired",
            (0x10, 0x00): "Check Status CIMB Payment Paid",
            (0x10, 0x02): "Check Status CIMB Payment ID Transaction Not Exist",
            (0x10, 0x03): "Check Status CIMB Payment Server Error",
            (0x10, 0x04): "Check Status CIMB Payment Server Timeout",
            (0x10, 0x05): "Check Status CIMB Payment Expired"
        }

         # Unpack the byte string into individual bytes
        byte1, byte2 = byte_string[0], byte_string[1]

        # Get the transaction status
        return status_dict.get((byte1, byte2), "Unknown Status")
    
    # def _get_lrc(self, data_bytes: bytearray) -> bytes:
    #     """Menghitung checksum LRC untuk memastikan integritas data."""
    #     lrc = 0
    #     for b in data_bytes:
    #         lrc ^= b  # XOR semua byte untuk mendapatkan LRC
    #     return bytes([lrc])

    def debit_transaction(self, amount: int, transaction_code: str) -> dict:
        # if not self.is_ready:
        #     raise Exception("Device is not ready")

        self.is_ready = False
        byte_array = bytearray(63)

        _STX = bytes([0x10, 0x02])
        _CMD = bytes([0x01])
        _ID_POS = self._set_length(self.pos_id, 8, True)
        _SHIFT_CODE = bytes([0x32, 0x30, 0x32, 0x31, 0x30, 0x31, 0x32, 0x31])
        _DATA_LENGHT = bytes([0x00, 0x2A])
        _TRANSACTION_ID = self._generate_id(transaction_code)
        _AMOUNT = self._set_length(amount, 8, True)
        _TRANSACTION_DATE = self._get_date_now(to_bytes=True)
        _ETX = bytes([0x10, 0x03])

        byte_array[0:2] = _STX
        byte_array[2:3] = _CMD
        byte_array[3:8] = _ID_POS
        byte_array[8:16] = _SHIFT_CODE
        byte_array[16:18] = _DATA_LENGHT
        byte_array[18:38] = _TRANSACTION_ID
        byte_array[38:46] = _AMOUNT
        byte_array[46:60] = _TRANSACTION_DATE
        byte_array[60:61] = self._get_lrc(byte_array)  # * checksum
        byte_array[61:63] = _ETX


        data_to_send = bytes(byte_array)

        self.ser.write(data_to_send)

        print(f"Send Data as HEX : {data_to_send.hex()}")

        while True:
            response_line: bytes = self.ser.readline()
            print(response_as_hex := response_line.hex())

            if response_line.endswith(b'\x10\x03'): # type: ignore
                status = self.__get_status(response_line[2:4])
                response_as_hex = response_line.hex()

                print(
                    f"Debit transaction response as hex :\n{response_as_hex}")
                if (response_line[3] == 0):

                    transaction_date = response_line[47:61].decode(
                        'utf-8', 'ignore')  # * byte convert to string
                    formatted_date = datetime(
                        int(transaction_date[4:8]),
                        int(transaction_date[2:4]),
                        int(transaction_date[0:2]),
                        int(transaction_date[8:10]),
                        int(transaction_date[10:12]),
                        int(transaction_date[12:14]),
                    ).strftime("%d-%m-%Y %H:%M:%S")

                    bank = response_line[93:96].decode('utf-8', 'ignore')
                    tid, mid = self.get_tid_mid(bank_name=bank)
                    result = {
                        "transaction_id":       response_line[19:39].decode('utf-8', 'ignore'),
                        "amount":               int(response_line[39:47].decode('utf-8', 'ignore')),
                        "transaction_date":     formatted_date,
                        "card_number":          response_line[61:77].decode('utf-8', 'ignore'),
                        "beginning_balance":    int(response_line[77:85].decode('utf-8', 'ignore')),
                        "ending_balance":       int(response_line[85:93].decode('utf-8', 'ignore')),
                        "bank":                 bank,
                        "tid":                  tid,
                        "mid":                  mid,
                        "response_as_hex":      response_as_hex
                    }
                    
                    self.last_debit_transaction = result
                    self.is_ready = True
                    return status, result
                
                else:
                    result = {
                        "status": status,
                        "response_ashex": response_as_hex,
                        "amount": amount
                    }
                    self.is_ready = True
                    raise DebitTransactionException(result)
    def balence_check(self) -> dict:
        if not self.is_ready:
            raise Exception("Device is not ready")

        self.is_ready = False

        data_to_send: bytes = bytes(
            [0x10, 0x2, 0x4, 0x30, 0x30, 0x30, 0x30, 0x31, 0x31, 0x0, 0x0, 0x0, 0x10, 0x3])
        self.ser.write(data_to_send)

        print(f"Send Data as HEX : {data_to_send.hex()}")

        while True:
            response_line: bytes = self.ser.readline()
            if response_line.endswith(b'\x10\x03'): # type: ignore
                status = self.__get_status(response_line[2:4])
                response_as_hex = response_line.hex()
                print(
                    f"Debit transaction response as hex :\n{response_as_hex}")
            if (response_line[3] == 0):
                result = {
                    "status": status,
                    "response_ashex": response_as_hex,
                    "amount": int(response_line[39:47].decode('utf-8', 'ignore'))
                }
                self.is_ready = True
                return result
            else:
                self.is_ready = True
                raise DebitTransactionException(result)

    def get_last_transaction(self):
        byte_array = bytearray(21)

        _STX = bytes([0x10, 0x02])
        _CMD = bytes([0x03])
        _ID_POS = self._set_length(self.pos_id, 5, True)
        _SHIFT_CODE = bytes([0x32, 0x30, 0x32, 0x31, 0x30, 0x31, 0x32, 0x31])
        _DATA_LENGHT = bytes([0x00, 0x00])
        _ETX = bytes([0x10, 0x03])

        byte_array[0:2] = _STX
        byte_array[2:3] = _CMD
        byte_array[3:8] = _ID_POS
        byte_array[8:16] = _SHIFT_CODE
        byte_array[16:18] = _DATA_LENGHT
        byte_array[18:19] = self._get_lrc(byte_array)  # * checksum
        byte_array[19:21] = _ETX

        data_to_send = bytes(byte_array)

        self.ser.write(data_to_send)

        print(f"get last transaction data sent as HEX :\n{data_to_send.hex()}")

        response_line: bytes = self.ser.readline()
        print(response_as_hex := response_line.hex())

        print("hasil", response_line)

        # * get status from bytes
        status = self.__get_status(response_line[2:4])
        response_as_hex = response_line.hex()

        # * start formatted data
        transaction_date = response_line[47:61].decode(
            'utf-8', 'ignore')  # * byte convert to string
        formatted_date = datetime(
            int(transaction_date[4:8]),
            int(transaction_date[2:4]),
            int(transaction_date[0:2]),
            int(transaction_date[8:10]),
            int(transaction_date[10:12]),
            int(transaction_date[12:14]),
        ).strftime("%d-%m-%Y %H:%M:%S")

        bank = response_line[93:96].decode('utf-8', 'ignore')
        tid, mid = self.get_tid_mid(bank_name=bank)
        result = {
            "transaction_id":       response_line[19:39].decode('utf-8', 'ignore'),
            "amount":               int(response_line[39:47].decode('utf-8', 'ignore')),
            "transaction_date":     formatted_date,
            "card_number":          response_line[61:77].decode('utf-8', 'ignore'),
            "beginning_balance":    int(response_line[77:85].decode('utf-8', 'ignore')),
            "ending_balance":       int(response_line[85:93].decode('utf-8', 'ignore')),
            "bank":                 bank,
            "tid":                  tid,
            "mid":                  mid,
            "response_as_hex":      response_as_hex
        }

        return status, result
    
    # def csn_check(self) -> None:
    #     if not
    #     raise Exception("Device is not ready")
    
    # self. is_ready = False

    # data_to_send: bytes = bytes([0x10, 0x02, 0x05, 0x10, 0x03])
    # self.ser.write(data_to_send)

    # print(f"Send Data as HEX : {data_to_send.hex()}")

    # while True:
    #     response_line: bytes = self.ser.readline()
    #     if response_line.endswith(b'\x10\x03'): # type: ignore
    #         status = self.__get_status(response_line[2:4])
    #         response_as_hex = response_line.hex()
    #         print(f"Debit transaction response as hex :\n{response_as_hex}")
    #     if (response_line[3] == 0):
    #         data_result = {
    #             "csn_number": response_line[4:20].decode('utf-8', 'ignore'),
    #             "response_as_hex": response_as_hex
    #         }

    #         self.is_ready = True
    #         return status, data_result
        
    #     else:
    #         self.is_ready = True
    #         raise DebitTransactionException(status)


    def _generate_id(self, transaction_code: str) -> bytes:
        rest_date = datetime.now().strftime("%m%d%H%M")
        year_date = int(datetime.now().strftime("%Y")) % 100

        new_id = self._set_length(
            f"{transaction_code}{year_date}{rest_date}", 20)
        return new_id.encode()

    def _get_lrc(self, data_bytes: bytearray) -> bytes:
        lrc = 0
        variable_data = data_bytes[3:-3]
        for item in variable_data:
            lrc ^= item

        return bytes([lrc])

    def _set_length(self,
                    data: str | int,
                    length: int,
                    get_bytes=False) -> str | bytes:

        data_str = str(data)

        if (len(data_str) < length):
            rest = length - len(data_str)
            data_str = ("0"*rest)+data_str

        elif (len(data_str) > length):
            data_str = data_str[0:length]

        if (get_bytes):
            return data_str.encode()

        return data_str

    def _get_date_now(self,
                      format: str = "%d%m%Y%H%M%S",
                      to_bytes=False) -> str | bytes:

        date = datetime.now()
        formatted = date.strftime(format)

        if to_bytes:
            return formatted.encode()

        return formatted

    def get_tid_mid(self, bank_name: str) -> tuple:
        match bank_name:
            case "BRI":
                return ("55550000", "123456789012345")

            case "BCA":
                return ("EBC12359", "000885789012349")

            case "MDR":
                return ("12345678", "000000000011234")

            case "BNI":
                return ("89235999", "123456789012345")

            case _:
                return ("00000000", "000000000000000")