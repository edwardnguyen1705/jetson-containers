# Build docker images

```bash
$ jetson-containers build --name=torch2trt torch2trt
```

After the building process, there are many docker images (`torch2trt:r36.3.0*`) that will be created, but the image `torch2trt:r36.3.0` contains both `torch` and `tensorrt`.

You can create a docker container and check

```bash
$ jetson-containers run torch2trt:r36.3.0
```
