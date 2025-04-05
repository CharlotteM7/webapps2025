#This module configures the payapp Django application and starts the
#Thrift timestamp service in a separate thread when the app is ready.

import threading
from django.apps import AppConfig

class PayappConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payapp'

    def ready(self):
        # Start the Thrift server in a separate thread
        self.start_thrift_server()

    def start_thrift_server(self):
        import time
        # Define the function that runs the Thrift server
        def run_thrift():
            from thrift.transport import TSocket, TTransport
            from thrift.protocol import TBinaryProtocol
            from thrift.server import TServer
            from datetime import datetime

            try:
                from payapp.gen import TimestampService
            except ImportError as e:
                print("Error importing Thrift generated code:", e)
                return

            class TimestampHandler:
                def getTimestamp(self):
                    return datetime.now().isoformat()

            handler = TimestampHandler()
            processor = TimestampService.Processor(handler)
            transport = TSocket.TServerSocket(port=10000)
            tfactory = TTransport.TBufferedTransportFactory()
            pfactory = TBinaryProtocol.TBinaryProtocolFactory()
            server = TServer.TSimpleServer(processor, transport, tfactory, pfactory)
            print("Thrift server running on port 10000...")
            # Run the server.
            server.serve()

        # Create and start a daemon thread to run the Thrift server
        thread = threading.Thread(target=run_thrift, daemon=True)
        thread.start()
        # Wait a brief moment to ensure the server starts before other operations.
        time.sleep(1)
