## Building ML backend images
The repo currently includes `ml_api/scripts/build_base_images.sh` for publishing the
architecture-specific `ml_api_base` images used by the runtime image.

To build the runtime `ml_api` image from your fork, run from the repository root:

```bash
docker build -t olyforge3d/ml_api:timeout-tuned ./ml_api
```

The runtime Dockerfile downloads model weights during the build with `wget`. That is intentional: the published `thespaghettidetective/ml_api_base:*` images already include `wget`, while they do not consistently include `curl`.

To validate it locally with the compose stack:

```bash
ML_API_CONNECT_TIMEOUT_SECONDS=0.5 docker compose build ml_api
ML_API_CONNECT_TIMEOUT_SECONDS=0.5 docker compose up -d ml_api
```

If you also need to publish refreshed base images, `build_base_images.sh` executes `docker`
to build, tag, and push them. The script should be run from the `ml_api` directory.

Arguments:
* -v VERSION argument should contain version number, like 1.3 or similar. It can also be `latest`
* -p PREFIX can be used to push images into a private repository or into a docker registry with a new name
* -i flag is used to help Docker work with insecure (like local private) repositories

To run local registry, use: https://docs.docker.com/registry/deploying/
Ex: `docker run -d -p 5000:5000 --restart=always --name registry registry:2`
