import argparse
import sys
import os
import logging
from .app import Repo2Docker
from .engine import BuildError, ImageLoadError
from . import __version__
from .utils import validate_and_generate_port_mapping, is_valid_docker_image_name


def validate_image_name(image_name):
    """
    Validate image_name read by argparse

    Note: Container names must start with an alphanumeric character and
    can then use _ . or - in addition to alphanumeric.
    [a-zA-Z0-9][a-zA-Z0-9_.-]+

    Args:
        image_name (string): argument read by the argument parser

    Returns:
        unmodified image_name

    Raises:
        ArgumentTypeError: if image_name contains characters that do not
                            meet the logic that container names must start
                            with an alphanumeric character and can then
                            use _ . or - in addition to alphanumeric.
                            [a-zA-Z0-9][a-zA-Z0-9_.-]+
    """
    if not is_valid_docker_image_name(image_name):
        msg = (
            "%r is not a valid docker image name. Image name "
            "must start with a lowercase or numeric character and "
            "can then use _ . or - in addition to lowercase and numeric." % image_name
        )
        raise argparse.ArgumentTypeError(msg)
    return image_name


# See https://github.com/jupyterhub/repo2docker/issues/871 for reason
class MimicDockerEnvHandling(argparse.Action):
    def __call__(self, parser, namespace, values, option_string=None):
        # There are 3 cases:
        #  key=value    pass as is
        #  key=         pass as is
        #  key          pass using current value, or don't pass
        if "=" not in values:
            try:
                value_to_append = "{}={}".format(values, os.environ[values])
            except KeyError:
                # no local def, so don't pass
                return
        else:
            value_to_append = values

        # destination variable is initially defined as an empty list, so
        # no special casing of first time is needed.
        getattr(namespace, self.dest).append(value_to_append)


def get_argparser():
    """Get arguments that may be used by repo2docker"""
    argparser = argparse.ArgumentParser(
        description="Fetch a repository and build a container image"
    )

    argparser.add_argument(
        "--config",
        default="repo2docker_config.py",
        help="Path to config file for repo2docker",
    )

    argparser.add_argument(
        "--json-logs",
        default=False,
        action="store_true",
        help="Emit JSON logs instead of human readable logs",
    )

    argparser.add_argument(
        "repo",
        help=(
            "Path to repository that should be built. Could be "
            "local path or a git URL."
        ),
    )

    argparser.add_argument(
        "--image-name",
        help=("Name of image to be built. If unspecified will be " "autogenerated"),
        type=validate_image_name,
    )

    argparser.add_argument(
        "--ref",
        help=(
            "Reference to build instead of default reference. For example"
            " branch name or commit for a Git repository."
        ),
    )

    argparser.add_argument("--debug", help="Turn on debug logging", action="store_true")

    argparser.add_argument(
        "--no-build",
        dest="build",
        action="store_false",
        help=(
            "Do not actually build the image. Useful in conjunction " "with --debug."
        ),
    )

    argparser.add_argument(
        "--build-memory-limit",
        help="Total Memory that can be used by the docker build process",
    )

    argparser.add_argument(
        "cmd",
        nargs=argparse.REMAINDER,
        help="Custom command to run after building container",
    )

    argparser.add_argument(
        "--no-run",
        dest="run",
        action="store_false",
        help="Do not run container after it has been built",
    )

    argparser.add_argument(
        "--publish",
        "-p",
        dest="ports",
        action="append",
        help=(
            "Specify port mappings for the image. Needs a command to "
            "run in the container."
        ),
    )

    argparser.add_argument(
        "--publish-all",
        "-P",
        dest="all_ports",
        action="store_true",
        help="Publish all exposed ports to random host ports.",
    )

    argparser.add_argument(
        "--no-clean",
        dest="clean",
        action="store_false",
        help="Don't clean up remote checkouts after we are done",
    )

    argparser.add_argument(
        "--push",
        dest="push",
        action="store_true",
        help="Push docker image to repository",
    )

    argparser.add_argument(
        "--volume",
        "-v",
        dest="volumes",
        action="append",
        help="Volumes to mount inside the container, in form src:dest",
        default=[],
    )

    argparser.add_argument(
        "--user-id", help="User ID of the primary user in the image", type=int
    )

    argparser.add_argument(
        "--user-name", help="Username of the primary user in the image"
    )

    # Process the environment options the same way that docker does, as
    # they are passed directly to docker as the environment to use. This
    # requires a custom action for argparse.
    argparser.add_argument(
        "--env",
        "-e",
        dest="environment",
        action=MimicDockerEnvHandling,
        help="Environment variables to define at container run time",
        default=[],
    )

    argparser.add_argument(
        "--editable",
        "-E",
        dest="editable",
        action="store_true",
        help="Use the local repository in edit mode",
    )

    argparser.add_argument("--target-repo-dir", help=Repo2Docker.target_repo_dir.help)

    argparser.add_argument("--appendix", type=str, help=Repo2Docker.appendix.help)

    argparser.add_argument(
        "--label",
        dest="labels",
        action="append",
        help="Extra label to set on the image, in form name=value",
        default=[],
    )

    argparser.add_argument(
        "--build-arg",
        dest="build_args",
        action="append",
        help="Extra build arg to pass to the build process, in form name=value",
        default=[],
    )

    argparser.add_argument("--subdir", type=str, help=Repo2Docker.subdir.help)

    argparser.add_argument(
        "--version",
        dest="version",
        action="store_true",
        help="Print the repo2docker version and exit.",
    )

    argparser.add_argument(
        "--cache-from", action="append", default=[], help=Repo2Docker.cache_from.help
    )

    argparser.add_argument("--engine", help="Name of the container engine")

    return argparser


argparser = get_argparser()


def make_r2d(argv=None):
    if argv is None:
        argv = sys.argv[1:]

    # version must be checked before parse, as repo/cmd are required and
    # will spit out an error if allowed to be parsed first.
    if "--version" in argv:
        print(__version__)
        sys.exit(0)

    args = get_argparser().parse_args(argv)

    r2d = Repo2Docker()

    if args.debug:
        r2d.log_level = logging.DEBUG

    r2d.load_config_file(args.config)
    if args.appendix:
        r2d.appendix = args.appendix

    for l in args.labels:
        key, _, val = l.partition("=")
        r2d.labels[key] = val

    for a in args.build_args:
        key, _, val = a.partition("=")
        r2d.extra_build_args[key] = val

    r2d.repo = args.repo
    r2d.ref = args.ref

    # user wants to mount a local directory into the container for
    # editing
    if args.editable:
        # the user has to point at a directory, not just a path for us
        # to be able to mount it. We might have content providers that can
        # provide content from a local `something.zip` file, which we
        # couldn't mount in editable mode
        if os.path.isdir(args.repo):
            r2d.volumes[os.path.abspath(args.repo)] = "."
        else:
            r2d.log.error(
                'Cannot mount "{}" in editable mode '
                "as it is not a directory".format(args.repo),
                extra=dict(phase="failed"),
            )
            sys.exit(1)

    if args.image_name:
        r2d.output_image_spec = args.image_name
    else:
        # we will pick a name after fetching the repository
        r2d.output_image_spec = ""

    r2d.json_logs = args.json_logs

    r2d.dry_run = not args.build

    if r2d.dry_run:
        # Can't push nor run if we aren't building
        args.run = False
        args.push = False

    r2d.run = args.run
    r2d.push = args.push

    # check against r2d.run and not args.run as r2d.run is false on
    # --no-build. Also r2d.volumes and not args.volumes since --editable
    # modified r2d.volumes
    if r2d.volumes and not r2d.run:
        # Can't mount if we aren't running
        print("To Mount volumes with -v, you also need to run the " "container")
        sys.exit(1)

    for v in args.volumes:
        src, dest = v.split(":")
        r2d.volumes[src] = dest

    r2d.run_cmd = args.cmd

    if args.all_ports and not r2d.run:
        print(
            "To publish user defined port mappings, the container must " "also be run"
        )
        sys.exit(1)

    if args.ports and not r2d.run:
        print(
            "To publish user defined port mappings, the container must " "also be run"
        )
        sys.exit(1)

    if args.ports and not r2d.run_cmd:
        print(
            "To publish user defined port mapping, user must specify "
            "the command to run in the container"
        )
        sys.exit(1)

    r2d.ports = validate_and_generate_port_mapping(args.ports)
    r2d.all_ports = args.all_ports

    if args.user_id:
        r2d.user_id = args.user_id
    if args.user_name:
        r2d.user_name = args.user_name
    if r2d.user_id == 0 and not r2d.dry_run:
        print("Root as the primary user in the image is not permitted.")
        print(
            "The uid and the username of the user invoking repo2docker "
            "is used to create a mirror account in the image by default. "
            "To override that behavior pass --user-id <numeric_id> and "
            " --user-name <string> to repo2docker.\n"
            "Please see repo2docker --help for more details.\n"
        )
        sys.exit(1)

    if args.build_memory_limit:
        # if the string only contains numerals we assume it should be an int
        # and specifies a size in bytes
        if args.build_memory_limit.isnumeric():
            r2d.build_memory_limit = int(args.build_memory_limit)
        else:
            r2d.build_memory_limit = args.build_memory_limit

    if args.environment and not r2d.run:
        print("To specify environment variables, you also need to run " "the container")
        sys.exit(1)

    if args.subdir:
        r2d.subdir = args.subdir

    if args.cache_from:
        r2d.cache_from = args.cache_from

    if args.engine:
        r2d.engine = args.engine

    r2d.environment = args.environment

    # if the source exists locally we don't want to delete it at the end
    # FIXME: Find a better way to figure out if repo is 'local'. Push this into ContentProvider?
    if os.path.exists(args.repo):
        r2d.cleanup_checkout = False
    else:
        r2d.cleanup_checkout = args.clean

    if args.target_repo_dir:
        r2d.target_repo_dir = args.target_repo_dir

    return r2d


def main():
    r2d = make_r2d()
    r2d.initialize()
    try:
        r2d.start()
    except BuildError as e:
        # This is only raised by us
        if r2d.log_level == logging.DEBUG:
            r2d.log.exception(e)
        sys.exit(1)
    except ImageLoadError as e:
        # This is only raised by us
        if r2d.log_level == logging.DEBUG:
            r2d.log.exception(e)
        sys.exit(1)


if __name__ == "__main__":
    main()
