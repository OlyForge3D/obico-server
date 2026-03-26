#!/usr/bin/env python

import flask
from flask_compress import Compress
from flask import abort, make_response, request, jsonify
from os import path, environ
import sentry_sdk
from sentry_sdk.integrations.flask import FlaskIntegration
import cv2
import numpy as np
import requests
import backoff
from requests.exceptions import HTTPError

from auth import token_required
from lib.detection_model import load_net, detect

THRESH = 0.08  # The threshold for a box to be considered a positive detection
SESSION_TTL_SECONDS = 60*2

# Sentry
if environ.get('SENTRY_DSN'):
    sentry_sdk.init(
        dsn=environ.get('SENTRY_DSN'),
        integrations=[FlaskIntegration(), ],
    )

app = flask.Flask(__name__)
Compress(app)

status = dict()

# SECURITY WARNING: don't run with debug turned on in production!
app.config['DEBUG'] = environ.get('DEBUG') == 'True'

model_dir = path.join(path.dirname(path.realpath(__file__)), 'model')
net_main = load_net(path.join(model_dir, 'model.cfg'), path.join(model_dir, 'model.meta'))


def _get_float_env(name, default):
    raw_value = environ.get(name)
    if raw_value in (None, ''):
        return default

    try:
        value = float(raw_value)
    except ValueError:
        app.logger.warning('Invalid %s=%s, falling back to %s', name, raw_value, default)
        return default

    if value <= 0:
        app.logger.warning('%s must be greater than 0, falling back to %s', name, default)
        return default

    return value


DEFAULT_CONNECT_TIMEOUT_SECONDS = _get_float_env('ML_API_CONNECT_TIMEOUT_SECONDS', 0.5)
DEFAULT_READ_TIMEOUT_SECONDS = _get_float_env('ML_API_READ_TIMEOUT_SECONDS', 5)
GCS_CONNECT_TIMEOUT_SECONDS = _get_float_env('ML_API_GCS_CONNECT_TIMEOUT_SECONDS', 10)
GCS_READ_TIMEOUT_SECONDS = _get_float_env('ML_API_GCS_READ_TIMEOUT_SECONDS', 30)


def _get_request_timeout(image_url):
    if 'storage.googleapis.com' in image_url:
        return (GCS_CONNECT_TIMEOUT_SECONDS, GCS_READ_TIMEOUT_SECONDS)

    return (DEFAULT_CONNECT_TIMEOUT_SECONDS, DEFAULT_READ_TIMEOUT_SECONDS)


def _should_retry(exc):
    """Only retry on HTTP 5xx server errors."""
    if isinstance(exc, HTTPError) and exc.response is not None:
        return exc.response.status_code >= 500
    return False


@backoff.on_exception(
    backoff.expo,
    HTTPError,
    max_tries=3,
    giveup=lambda exc: not _should_retry(exc)
)
def _get_with_retry(url, timeout, stream=True):
    """Make HTTP GET request with retry logic for 5xx errors."""
    resp = requests.get(url, stream=stream, timeout=timeout)
    resp.raise_for_status()
    return resp


@app.route('/p/', methods=['GET'])
@token_required
def get_p():
    if 'img' in request.args:
        try:
            timeout = _get_request_timeout(request.args['img'])
            resp = _get_with_retry(request.args['img'], timeout, stream=True)
            img_array = np.array(bytearray(resp.content), dtype=np.uint8)
            img = cv2.imdecode(img_array, -1)
            detections = detect(net_main, img, thresh=THRESH)
            return jsonify({'detections': detections})
        except Exception as err:
            sentry_sdk.capture_exception()
            app.logger.error(f"Failed to get image {request.args} - {err}")
            abort(
                make_response(
                    jsonify(
                        detections=[],
                        message=f"Failed to get image {request.args} - {err}",
                    ),
                    400,
                )
            )
    else:
        app.logger.warn(f"Invalid request params: {request.args}")
        abort(
            make_response(
                jsonify(
                    detections=[], message=f"Invalid request params: {request.args}"
                ),
                422,
            )
        )


@app.route('/hc/', methods=['GET'])
def health_check():
    return 'ok' if net_main is not None else 'error'

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=3333, threaded=False)
