"""
"""

import docker
import tarfile
import tempfile
import shutil
import json
import subprocess
import os


class DockerCLI:
    def __init__(self):
        cp = subprocess.run(
            ["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        if cp.returncode:
            raise docker.errors.DockerException("no Docker")

    def build(
        self,
        fileobj=None,
        tag=None,
        custom_context=False,
        buildargs=None,
        decode=False,
        forcerm=False,
        rm=False,
        container_limits=None,
        cache_from=None,
        path=None,
        **extra_build_kwargs,
    ):

        build_cmd = "docker build --progress plain"

        if tag is not None:
            build_cmd = build_cmd + " --tag " + tag

        tempdir = tempfile.mkdtemp()
        if fileobj is not None:
            tar = tarfile.open(fileobj=fileobj, mode="r")
            tar.extractall(tempdir)
            tar.close()

        if buildargs is not None:
            for key, value in buildargs.items():
                build_cmd = build_cmd + " --build-arg " + key + "=" + value

        # TODO: Handle extra_build_kwargs?

        if forcerm:
            build_cmd = build_cmd + " --force-rm"

        if rm:
            build_cmd = build_cmd + " --rm"

        if container_limits is not None:
            if "memlimit" in container_limits:
                build_cmd = build_cmd + " --memory " + container_limits["memlimit"]

        if cache_from:
            build_cmd = build_cmd + " --cache-from"
            for cache in cache_from:
                build_cmd = build_cmd + " " + cache

        build_cmd = build_cmd + " " + tempdir

        print(build_cmd)
        with subprocess.Popen(
            build_cmd,
            shell=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            env={"DOCKER_BUILDKIT": "1", "PROGRESS_NO_TRUNC": "1"},
        ) as p:

            while True:
                line = p.stdout.readline()
                if p.poll() is not None:
                    break
                yield {"stream": line}

            rc = p.poll()
            if rc != 0:
                yield {"error": line}

        shutil.rmtree(tempdir)
