import os
import struct

def what(file):
    if hasattr(file, 'read'):
            head = file.read(32)
                else:
                        with open(file, 'rb') as f:
                                    head = f.read(32)

                                        if len(head) < 4:
                                                return None

                                                    if head[:4] == b'\x89PNG':
                                                            return 'png'
                                                                if head[:3] == b'GIF':
                                                                        return 'gif'
                                                                            if head[:2] == b'\xff\xd8':
                                                                                    return 'jpeg'
                                                                                        if head[:4] == b'RIFF' and head[8:12] == b'WEBP':
                                                                                                return 'webp'
                                                                                                    if head[:2] == b'BM':
                                                                                                            return 'bmp'
                                                                                                                return None