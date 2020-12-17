"""
Test that build args are working
"""

from unittest.mock import patch
from repo2docker import Repo2Docker
from repo2docker.utils import chdir
from repo2docker.__main__ import make_r2d


def test_build_args(tmpdir):

    with chdir(tmpdir):
        with open("postBuild", "w") as f:
            f.write("echo FOO=${FOO} > /tmp/foo.txt")

        with patch("repo2docker.buildpacks.BuildPack.get_build_args") as gba:
            gba.return_value = ["FOO"]
            r2d = make_r2d(
                [
                    "--build-arg",
                    "FOO=BAR",
                    "--debug",
                    str(tmpdir),
                    "cat",
                    "/tmp/foo.txt",
                ]
            )
            r2d.initialize()
            r2d.start()

            # Originally used capsys, but this failed when run with other tests
            log = r2d.log.handlers[0].stream
            log.seek(0)
            output = log.read()
            # ARG should be set in debug output
            assert "ARG FOO" in output
            # ARG and value should be present in cat output
            assert "FOO=BAR" in output
