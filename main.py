#!/usr/local/bin/python3.4
import urllib.request
import hashlib
import re
from lxml.html import HTMLParser, document_fromstring, etree
import sys, tempfile, shutil, contextlib
import collections
import cv2
from PIL import Image
import math

# Port Number: 10213

# !/usr/local/bin/python3.4
import flask
import os

app = flask.Flask(__name__)
banned_list = ['facebook', 'snapchat', 'reddit', 'twitter', 'instagram', 'myspace']


@app.route('/')
def root_page():
    return flask.render_template('root.html')


@app.route('/view')
def view_page():
    url = flask.request.args.get("url")
    return get_html_at_url(url)


def get_html_at_url(url, charset='UTF-8',):
    for banned in banned_list:
        if (banned in url):
            return flask.render_template('error.html')

    try:
        website = urllib.request.Request(url)
    except ValueError:
        return flask.render_template('error.html')


    try:
        html = urllib.request.urlopen(website).read().decode(charset)
    except Exception as e:
        return flask.render_template('error.html')

    root = make_etree(html, url)
    head = root.find('.//head')
    if head is not None:
        base = etree.Element('base', href=url)
        head.insert(0, base)
    profile_photo = copy_profile_photo_to_static(root)



    if profile_photo is not None:
        img_info = get_image_info(profile_photo)
        add_glasses(profile_photo,img_info['faces'][0])
        new_html = etree.tostring(root)
        
        # Credit:  Alexander J. Quinn.  Used with permission.  https://piazza.com/class/jkspuifikh3s9?cid=789
        mo = re.search(r"\s*<.+?>", html, flags=re.DOTALL)
        if mo is not None:
            doctype = mo.group(0)
            new_html = doctype.encode('utf8') + b"\n" + new_html
        return new_html

    else:
        return flask.render_template('noprofile.html')


def make_etree(html, url):
    parser = HTMLParser(encoding='UTF-8')
    root = document_fromstring(html, parser=parser, base_url=url)
    return root


def copy_profile_photo_to_static(etree):
    with fetch_images(etree) as filename_to_node:
        profile_photo = find_profile_photo_filename(filename_to_node)
        if profile_photo is not None:
            os.system('cp ' + profile_photo + ' ../../static/' + profile_photo)
            img_node = filename_to_node[profile_photo]
            new_url = flask.url_for('static', filename=os.path.basename(profile_photo),_external=True) 
            img_node.set('src',new_url)
            return os.path.join(app.static_folder,profile_photo)
    return None

def make_filename(url, extension):
    url = url.encode('utf8')
    name = hashlib.sha1(url).hexdigest()
    return name + '.' + extension


@contextlib.contextmanager
def fetch_images(etree):
    with pushd_temp_dir():
        filename_to_node = collections.OrderedDict()
        img_nodes = etree.findall(".//img")
        base_node = etree.find(".//base")
        try:
            base_url = base_node.get('href')
        except Exception as e:
            base_url = ""

        for node in img_nodes:
            if base_url is "" or None:
                img_url = node.get('src')
            else:
                img_url = base_url + '/' + node.get('src')


            website = urllib.request.Request(img_url)
            website.add_header('User-Agent', 'PurdueUniversityClassProject/1.0 (mtoner@purdue.edu https://goo.gl/dk8u5S)')
            img = urllib.request.urlopen(website)


            type = img.info().get('Content-Type')
            ext = type.split('/')[1]
            filename = make_filename(img_url, ext)
            with open(filename, 'wb') as tempfile:
                tempfile.write(img.read())
            if ext in ['gif', 'GIF']:
                ext = 'jpg'
                new_filename = make_filename(img_url, ext)
                Image.open(filename).convert('RGB').save(new_filename)
                filename = new_filename
            elif ext in ['jpg','jpeg','png','jpe','.jp2']:
                filename_to_node[filename] = node
        yield filename_to_node


def get_image_info(filename):
    img = cv2.imread(filename)
    #print(filename)
    (h, w, d) = img.shape
    # Found from https://docs.opencv.org/3.0-beta/doc/py_tutorials/py_core/py_basic_ops/py_basic_ops.html#accessing-image-properties

    FACE_DATA_PATH = '/home/ecegridfs/a/ee364/site-packages/cv2/data/haarcascade_frontalface_default.xml'
    face_cascade = cv2.CascadeClassifier(FACE_DATA_PATH)
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray_img, 1.3, 5)
    faces = list(faces)
    faces.sort(key=area, reverse=True)
    faces_list = []
    for face in faces:
        face_dict = {'x': face[0], 'y': face[1], 'w': face[2], 'h': face[3]}
        faces_list.append(face_dict)

    info_dict = {'w': w, 'h': h, 'faces': faces_list}
    return info_dict


def add_glasses(filename, face_info,debug=False):
    EYE_DATA = "/home/ecegridfs/a/ee364/site-packages/cv2/data/haarcascade_eye.xml"
    eye_cascade = cv2.CascadeClassifier(EYE_DATA)
    img = cv2.imread(filename)
    (h, w, d) = img.shape
    gray_img = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    eyes = eye_cascade.detectMultiScale(gray_img, 1.3, 5)
    real_eyes = []
    for eye in eyes:
        eye_info = {'x': eye[0], 'y': eye[1], 'w': eye[2], 'h': eye[3]}
        if is_eye_in_face(face_info, eye_info):
            real_eyes.append(eye_info)

    if(debug):
        glasses = 'pixel'
    else:
        glasses = flask.request.args.get('glasses')


    print('Num Eyes: ' + str(len(eyes)) + ' Real Eyes: ' + str(len(real_eyes)))
    if len(real_eyes) == 2:
        if(real_eyes[0]['x'] < real_eyes[0]['y']):
            left_center = get_center(real_eyes[0])
            right_center = get_center(real_eyes[1])
        else:
            left_center = get_center(real_eyes[1])
            right_center = get_center(real_eyes[0])
    else:
        left_center = (face_info['x'] + face_info['w']*.3,face_info['y'] + face_info['h']*.4)
        right_center = (face_info['x'] + face_info['w']*.7,face_info['y'] + face_info['h']*.4)

    draw_glasses(img,left_center,right_center,glasses=glasses)

    #draw_rectangle(face_info,img)
    #for eye in real_eyes:
    #    draw_rectangle(eye,img)

    if debug:
        cv2.imwrite('test.png',img)
    else:
        cv2.imwrite(filename, img)

def draw_rectangle(rect,img):
    l = (rect['x'], rect['y'])
    b = (rect['x'] + rect['w'],rect['y'] + rect['h'])
    cv2.rectangle(img,l,b,(0,255,0),5)

def get_center(eye):
    return (eye['x'] + eye['w']//2,eye['y'] + eye['h']//2)

def is_eye_in_face(face, eye):
    if face['x'] < eye['x'] and face['y'] < eye['y'] and eye['x'] < face['x'] + face['w'] and eye['y'] < face['y'] + face['h']:
        return True
    else:
        return False

def draw_glasses(img,left_center,right_center,glasses='pixel'):
    y_off = 0
    if glasses == 'pixel':
        glasses_img = cv2.imread("static/PixelGlasses.png", cv2.IMREAD_UNCHANGED)
        left_lense = (295, 260)
        right_lense = (710, 260)
        glasses_scale = 1.8
    elif glasses == 'sun':
        glasses_img = cv2.imread("static/sunglasses.png", cv2.IMREAD_UNCHANGED)
        left_lense = (141, 80)
        right_lense = (377, 80)
        glasses_scale = 3.5
    elif glasses == 'clout':
        glasses_img = cv2.imread("static/clout.png", cv2.IMREAD_UNCHANGED)
        left_lense = (478, 312)
        right_lense = (1477, 330)
        glasses_scale = 3.3
    elif glasses == 'ski':
        glasses_img = cv2.imread("static/ski.png", cv2.IMREAD_UNCHANGED)
        left_lense = (206, 160)
        right_lense = (527, 160)
        glasses_scale = 2
    elif glasses == 'mustache':
        glasses_img = cv2.imread("static/mustache.png", cv2.IMREAD_UNCHANGED)
        left_lense = (222, 300)
        right_lense = (700, 300)
        glasses_scale = 1.4
        y_off = glasses_img.shape[1]//2 - left_lense[1]
        #mustache needs an offset because its not in the center
        #found out i wasnt compensating for that but its not worth it at this point to fix

    glasses_dist = right_lense[0]-left_lense[0]
    aspect_ratio = glasses_img.shape[0] / glasses_img.shape[1]

    eye_dist = math.sqrt((right_center[0] - left_center[0])**2 + (right_center[1]-left_center[1])**2)
    width = glasses_img.shape[0] / glasses_dist * eye_dist * glasses_scale
    width = int(width)
    height = int(width * aspect_ratio)
    y_off = y_off * height//glasses_img.shape[1]
    glasses_img = cv2.resize(glasses_img,(width,height), interpolation=cv2.INTER_NEAREST)
    theta = math.atan((left_center[1]-right_center[1])/(right_center[0]-left_center[0])) #for the y values its reverse because origin is top left
    theta = math.degrees(theta)
    R = cv2.getRotationMatrix2D((width/2,height/2),theta,1)
    glasses_img = cv2.warpAffine(glasses_img,R,(width,height))
    alphas = glasses_img[:, :, 3] / 255

    midpoint = (int((right_center[0]+left_center[0])/2),int((right_center[1]+left_center[1])/2))

    translate = (midpoint[0]-width//2,midpoint[1] - height//2 + y_off)
    print(translate)
    #print(midpoint)
    #cv2.circle(img,midpoint,5,5)
    #cv2.circle(img,right_center,5,5)
    #cv2.circle(img,left_center,5,5)

    for c in range(0, 3):
        img[translate[1]:translate[1]+height, translate[0]:translate[0] + width, c] \
            = glasses_img[0:height, 0:width, c] * alphas + img[translate[1]:translate[1]+height, translate[0]:translate[0]+width, c] * (1 - alphas)



def find_profile_photo_filename(filename_to_etree):
    # Find the photo whose largest face takes up the highest proportion of the image
    max_ratio = 0
    best_photo = None
    for filename, node in filename_to_etree.items():
        img_info = get_image_info(filename)
        img_area = img_info['w'] * img_info['h']
        if len(img_info['faces']) is 0:
            continue
        face_area = img_info['faces'][0]['w'] * img_info['faces'][0]['w']
        ratio = face_area / img_area
        if ratio > max_ratio:
            max_ratio = ratio
            best_photo = filename
    return best_photo


def area(face):
    return face[2] * face[3]


@contextlib.contextmanager
def pushd_temp_dir(base_dir=None, prefix="tmp.hpo."):
    '''
    Create a temporary directory starting with {prefix} within {base_dir}
    and cd to it.

    This is a context manager.  That means it can---and must---be called using
    the with statement like this:

        with pushd_temp_dir():
            ....   # We are now in the temp directory
        # Back to original directory.  Temp directory has been deleted.

    After the with statement, the temp directory and its contents are deleted.


    Putting the @contextlib.contextmanager decorator just above a function
    makes it a context manager.  It must be a generator function with one yield.

    - base_dir --- the new temp directory will be created inside {base_dir}.
                   This defaults to {main_dir}/data ... where {main_dir} is
                   the directory containing whatever .py file started the
                   application (e.g., main.py).

    - prefix ----- prefix for the temp directory name.  In case something
                   happens that prevents
    '''
    if base_dir is None:
        proj_dir = sys.path[0]
        # e.g., "/home/ecegridfs/a/ee364z15/hpo"

        main_dir = os.path.join(proj_dir, "data")
        # e.g., "/home/ecegridfs/a/ee364z15/hpo/data"
    # Create temp directory
    temp_dir_path = tempfile.mkdtemp(prefix=prefix, dir=main_dir)

    try:
        start_dir = os.getcwd()  # get current working directory
        os.chdir(temp_dir_path)  # change to the new temp directory

        try:
            yield
        finally:
            # No matter what, change back to where you started.
            os.chdir(start_dir)
    finally:
        # No matter what, remove temp dir and contents.
        shutil.rmtree(temp_dir_path, ignore_errors=True)


if __name__ == '__main__':
    debug = False
    if (not debug):
        app.run(host="127.0.0.1", port=os.environ.get("ECE364_HTTP_PORT", 8000),
                use_reloader=True, use_evalex=False, debug=True, use_debugger=False)
    else:
        img_info = get_image_info('static/chrishan2.jpg')
        add_glasses('static/chrishan2.jpg', img_info['faces'][0],debug=True)
        # Each student has their own port, which is set in an environment variable.
        # When not on ecegrid, the port defaults to 8000.  Do not change the host,
        # use_evalex, and use_debugger parameters.  They are required for security.
        #
        # Credit:  Alex Quinn.  Used with permission.  Preceding line only.
