# microdot_asyncio.py
# Minimal Microdot-like implementation for MicroPython (asyncio)
# Soporta: Microdot class, @app.route decorator, Response, send_file, app.run_task
import uasyncio as asyncio
import ure as re
import os

class Response:
    default_content_type = 'text/html; charset=utf-8'
    def __init__(self, body='', status=200, headers=None):
        self.body = body if isinstance(body, (bytes, str)) else str(body)
        self.status = status
        self.headers = headers or {}

    def to_bytes(self):
        body = self.body if isinstance(self.body, bytes) else self.body.encode('utf-8')
        hdrs = 'HTTP/1.1 {} OK\r\n'.format(self.status)
        hdrs += 'Content-Type: {}\r\n'.format(self.headers.get('Content-Type', self.default_content_type))
        hdrs += 'Content-Length: {}\r\nConnection: close\r\n\r\n'.format(len(body))
        return hdrs.encode('utf-8') + body

class Request:
    def __init__(self, method, path, query, reader, writer):
        self.method = method
        self.path = path
        self.args = query
        self._reader = reader
        self._writer = writer

class Microdot:
    def __init__(self):
        self._routes = {}
        self._host = "0.0.0.0"
        self._port = 80

    def route(self, path):
        def decorator(fn):
            self._routes[path] = fn
            return fn
        return decorator

    async def _handle_client(self, reader, writer):
        try:
            head = await reader.read(1024)
            if not head:
                try: await writer.aclose()
                except: pass
                return
            line = head.decode('utf-8', 'ignore').splitlines()[0]
            parts = line.split(' ')
            method = parts[0] if len(parts)>0 else 'GET'
            raw = parts[1] if len(parts)>1 else '/'
            path = raw
            query = {}
            if '?' in raw:
                p, q = raw.split('?',1)
                path = p
                for pair in q.split('&'):
                    if '=' in pair:
                        k,v = pair.split('=',1)
                        query[k]=v
            # match exact route or dynamic /html/<path>
            handler = self._routes.get(path)
            if not handler:
                # try pattern /html/<path>
                if path.startswith('/html/'):
                    handler = self._routes.get('/html/<path>')
                    if handler:
                        req = Request(method, path, query, reader, writer)
                        resp = await handler(req, path[len('/html/'):])
                    else:
                        resp = Response('Not found', status=404)
                else:
                    resp = Response('Not found', status=404)
            else:
                req = Request(method, path, query, reader, writer)
                resp = await handler(req)
            if isinstance(resp, Response):
                await writer.awrite(resp.to_bytes())
            elif isinstance(resp, (bytes, bytearray)):
                await writer.awrite(resp)
            else:
                body = str(resp)
                await writer.awrite(Response(body).to_bytes())
        except Exception as e:
            try:
                await writer.awrite(Response('Internal error: {}'.format(e), status=500).to_bytes())
            except:
                pass
        finally:
            try:
                await writer.aclose()
            except:
                pass

    async def run_task(self, host="0.0.0.0", port=80):
        self._host = host
        self._port = port
        server = await asyncio.start_server(self._handle_client, host, port)
        try:
            await server.wait_closed()
        finally:
            try:
                server.close()
            except:
                pass

# helper to send file contents as Response (async-compatible)
async def send_file(path):
    try:
        with open(path, 'rb') as f:
            data = f.read()
        return Response(data)
    except Exception as e:
        return Response('Not found: {}'.format(e), status=404)
