import sys
if sys.prefix == '/usr':
    sys.real_prefix = sys.prefix
    sys.prefix = sys.exec_prefix = '/home/elmeripk/robots/src/test_bot_controller/install/test_bot_controller'
