from __future__ import print_function
from flask import Flask, request, redirect, render_template, send_from_directory
from uuid import uuid4
import os
import json
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import threading
from werkzeug.utils import secure_filename
from processing_unit import process_input
import logging

app = Flask(__name__)

UPLOAD_FOLDER = '/tmp/WebAppSunScene'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
else:
    if not os.access(UPLOAD_FOLDER, os.W_OK):
        UPLOAD_FOLDER += str(uuid4())
        os.makedirs(UPLOAD_FOLDER)
URL_ROOT = None


# formatter = logging.Formatter(
#     "[%(asctime)s] {%(pathname)s:%(lineno)d} %(levelname)s - %(message)s")
# handler = RotatingFileHandler(LOG_FILE, maxBytes=1000000, backupCount=5)
# handler.setLevel(logging.INFO)
# handler.setFormatter(formatter)
# logging.addHandler(handler)


def files_folder(identifier):
    folder = os.path.join(UPLOAD_FOLDER, identifier)
    if not os.path.exists(folder):
        os.makedirs(folder)
    return folder


def json_file(identifier):
    return files_folder(identifier)+'.json'


def load_json(filename):
    try:
        with open(filename, 'r') as fp:
            saved_data = json.load(fp)
    except IOError:
        saved_data = {}
    return saved_data


def load_data(identifier):
    return load_json(json_file(identifier))


def save_data(data, identifier):
    saved_data = load_data(identifier)
    saved_data.update(data)
    with open(json_file(identifier), 'w') as fp:
        json.dump(saved_data, fp)


def save_file(the_file, identifier, filename):
    the_file.save(os.path.join(files_folder(identifier), filename))


def send_mail(toaddr, identifier):
    fromaddr = "pysunscene@gmail.com"
    frompasswd = "uibdmidfis"

    msg = MIMEMultipart()

    msg['From'] = fromaddr
    msg['To'] = toaddr
    msg['Subject'] = "Results of computation of PySunScene"

    body = """\
    <html>
    Get your results at:
    <a href="%s">link</a>
    </html>
    """ % (URL_ROOT + 'results/' + identifier)

    msg.attach(MIMEText(body, 'html'))

    server = smtplib.SMTP('smtp.gmail.com', 587)
    server.starttls()
    server.login(fromaddr, frompasswd)
    text = msg.as_string()
    server.sendmail(fromaddr, toaddr, text)
    server.quit()


def process_request(identifier):
    # Call the processing unit
    dirname = files_folder(identifier)
    datafile = json_file(identifier)
    process_input(datafile, dirname)
    # Send mail with link
    data = load_data(identifier)
    send_mail(toaddr=data['email'], identifier=identifier)


@app.route('/')
def hello():
    logging.info("Processing root")
    global URL_ROOT
    if URL_ROOT is None:
        URL_ROOT = request.url_root
    return redirect('node/start')


@app.route('/node/<name>/<identifier>', methods=['GET', 'POST'])
@app.route('/node/<name>', methods=['GET', 'POST'])
def node(name, identifier=None):
    if identifier:
        logging.info("Processing %s/%s", name, identifier)
    else:
        logging.info("Processing %s ", name)
    if request.method == 'GET':
        return render_template(name + ".html", identifier=identifier)
    if request.method == 'POST':
        data = request.form.to_dict()
        if identifier is None:
            identifier = str(uuid4())
        file_ids = request.files
        for file_id in file_ids:
            the_file = request.files[file_id]
            if the_file and the_file.filename != "":
                filename = the_file.filename
                filename = secure_filename(filename)
                logging.debug("filename is %s", filename)
                save_file(the_file, identifier, filename)
                data[file_id] = filename
        save_data(data, identifier)
        if 'next_step' in data:
            return redirect('node/' + data['next_step'] + '/' + identifier)
        else:
            return redirect('end/' + identifier)


@app.route('/end/<identifier>')
def end_process(identifier):
    if identifier:
        logging.info("Processing end/%s", identifier)
    else:
        logging.info("Processing end ")
    global URL_ROOT
    if URL_ROOT is None:
        URL_ROOT = request.url_root
    compute_thread = threading.Thread(target=process_request, args=(identifier,))
    compute_thread.start()
    return render_template("end.html", identifier=identifier)


@app.route('/status/<identifier>')
def status(identifier):
    if identifier:
        logging.info("Processing status/%s", identifier)
    else:
        logging.info("Processing status ")
    statusfile = files_folder(identifier) + '.status'
    data_status = load_json(statusfile)
    if not data_status:
        return render_template("error.html", identifier=identifier)
    return render_template("status.html", identifier=identifier, data_status=data_status)


@app.route('/results/<identifier>', methods=['GET'])
@app.route('/results/')
def send_file(identifier=None):
    if identifier:
        logging.info("Requesting results of %s", identifier)
    else:
        logging.info("Requesting results")
    if identifier is None:
        return "No process job specified"
    return send_from_directory(UPLOAD_FOLDER, identifier + '.zip')


if __name__ == '__main__':
    logging.getLogger().setLevel(logging.DEBUG)
    app.jinja_env.auto_reload = True
    app.config['TEMPLATES_AUTO_RELOAD'] = True
    app.run(host='0.0.0.0', port=5002, threaded=True, debug=True)
