from .base import BuildPack, BaseImage
from .python import PythonBuildPack
from .pipfile import PipfileBuildPack
from .conda import CondaBuildPack
from .julia import JuliaProjectTomlBuildPack
from .julia import JuliaRequireBuildPack
from .docker import DockerBuildPack
from .legacy import LegacyBinderDockerBuildPack
from .r import RBuildPack
from .nix import NixBuildPack

class ComposableBuildPack(BuildPack):
    def __init__(self):
        super().__init__()
        self.buildpacks = []

    def detect(self):
        for buildpack in [BaseImage, CondaBuildPack, PythonBuildPack, RBuildPack, JuliaProjectTomlBuildPack]:
            if buildpack().detect():
                self.buildpacks.append(buildpack)
                # For backward compatibility preserve inheritance
                while buidpack.__bases__[0] is not BuildPack:
                    buildpack = buidpack_class.__bases__[0]
                    self.buildpacks.append(buildpack)
        if self.buildpacks:
            self.buildpacks = sorted(set(self.buildpacks), key=operator.attrgetter("_order"))
            self.buildpacks = [_() for _ in self.buildpacks]  # initialize

        print("Using following buildpacks:")
        for buildpack_class in self.buildpacks:
            print(" -> {}".format(str(buildpack)))
        return True

    def get_packages(self):
        packages = set()
        for buildpack in self.buildpacks:
            packages |= buildpack.get_packages()
        return packages

    def get_base_packages(self):
        packages = set()
        for buildpack in self.buildpacks:
            packages |= buildpack.get_base_packages()
        return packages

    def get_build_env(self):
        env = []
        for buildpack in self.buildpacks:
            env += buildpack.get_build_env()
        return env

    def get_env(self):
        env = []
        for buildpack in self.buildpacks:
            env += buildpack.get_env()
        return env

    def get_path(self):
        path = []
        for buildpack in self.buildpacks:
            path += buildpack.get_path()
        return path

    def get_build_script_files(self):
        scripts = {}
        for buildpack in self.buildpacks:
            scripts.update(buildpack.get_build_script_files())
        return scripts

    def get_build_scripts(self):
        scripts = []
        for buildpack in self.buildpacks:
            scripts += buildpack.get_build_scripts()
        return scripts

    def get_preassemble_script_files(self):
        files = {}
        for buildpack in self.buildpacks:
            files.update(buildpack.get_preassemble_script_files())
        return files

    def get_preassemble_scripts(self):
        files = []
        for buildpack in self.buildpacks:
            files += buildpack.get_preassemble_scripts()
        return files

    def get_assemble_scripts(self):
        scripts = []
        for buildpack in self.buildpacks:
            scripts += buildpack.get_assemble_scripts()
        return scripts

    def get_post_build_scripts(self):
        scripts = []
        for buildpack in self.buildpacks:
            scripts += buildpack.get_post_build_scripts()
        return scripts
