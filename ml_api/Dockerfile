FROM thespaghettidetective/ml_api_base:1.4

WORKDIR /app
EXPOSE 3333

ADD . /app
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

RUN mkdir -p /model_cache/ml_api/darknet /model_cache/ml_api/onnx \
 && echo 'Downloading the latest failure detection AI model in Darknet format...' \
 && wget -O /model_cache/ml_api/darknet/model-weights.darknet "$(tr -d '\r' < model/model-weights.darknet.url)" \
 && echo 'Downloading the latest failure detection AI model in ONNX format...' \
 && wget -O /model_cache/ml_api/onnx/model-weights.onnx "$(tr -d '\r' < model/model-weights.onnx.url)"
