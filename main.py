#!/usr/local/bin/python3.4
import flask
import os
import urllib.request
from lxml.html import HTMLParser, document_fromstring
#Port Number: 10213

#!/usr/local/bin/python3.4
import flask
import os

app = flask.Flask(__name__)
banned_list = ['facebook','snapchat','reddit','twitter','instagram','myspace']

@app.route('/')
def root_page():
    return flask.render_template('root.html')


@app.route('/view')
def view_page():
    url = flask.request.args.get("url")
    return get_html_at_url(url)


#def check_url(url):
#    return True

def get_html_at_url(url, charset='UTF-8'):
    for banned in banned_list:
        if(banned in url):
            return flask.render_template('error.html')

    try:
        website = urllib.request.Request(url)
    except ValueError:
        return flask.render_template('error.html')

    website.add_header('User-Agent','PurdueUniversityClassProject/1.0 (mtoner@purdue.edu https://goo.gl/dk8u5S)')
    html =  urllib.request.urlopen(website).read().decode(charset)
    html = '<base href=\"' + url + "\">\n" + html
    return html

def make_etree(html,url):
    parser = HTMLParser(encoding='UTF-8')
    root = document_fromstring(html, parser=parser, base_url=url)
    return root

def make_outline(etree):
    s = ""
    for node in etree.iter():
        if(node.tag == 'h1'):
            content = node.text_content()
            content = " ".join(content.split())
            s = s + content + "\n"
        if(node.tag == 'h2'):
            content = node.text_content()
            content = " ".join(content.split())
            s = s + "    " + content + "\n"
        if(node.tag == 'h3'):
            content = node.text_content()
            content = " ".join(content.split())
            s = s + "        " + content + "\n"
    return s

if __name__ == '__main__':
    app.run(host="127.0.0.1", port=os.environ.get("ECE364_HTTP_PORT", 8000),
            use_reloader=True, use_evalex=False, debug=True, use_debugger=False)
    # Each student has their own port, which is set in an environment variable.
    # When not on ecegrid, the port defaults to 8000.  Do not change the host,
    # use_evalex, and use_debugger parameters.  They are required for security.
    #
    # Credit:  Alex Quinn.  Used with permission.  Preceding line only.

# if __name__ == "__main__":
#     s = get_html_at_url('https://www.example.com/')
#     print(type(s))
#
#     url = "http://nyt.com"
#     html = get_html_at_url(url)
#     #print(html)
#     root = make_etree(html,url)
#     #print(make_outline(root))
#     print(root)
#     root.find(".//h2")
