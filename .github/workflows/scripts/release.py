# WARNING: DO NOT EDIT!
#
# This file was generated by plugin_template, and is managed by it. Please use
# './plugin-template --github pulp_2to3_migration' to update this file.
#
# For more info visit https://github.com/pulp/plugin_template

import argparse
import asyncio
import re
import os
import shutil
import textwrap

from bandersnatch.mirror import BandersnatchMirror
from bandersnatch.master import Master
from bandersnatch.configuration import BandersnatchConfig

from git import Repo

from packaging.requirements import Requirement
from pathlib import Path


async def get_package_from_pypi(package_name, plugin_path):
    """
    Download a package from PyPI.

    :param name: name of the package to download from PyPI
    :return: String path to the package
    """
    config = BandersnatchConfig().config
    config["mirror"]["master"] = "https://pypi.org"
    config["mirror"]["workers"] = "1"
    config["mirror"]["directory"] = plugin_path
    if not config.has_section("plugins"):
        config.add_section("plugins")
    config["plugins"]["enabled"] = "blocklist_release\n"
    if not config.has_section("allowlist"):
        config.add_section("allowlist")
    config["plugins"]["enabled"] += "allowlist_release\nallowlist_project\n"
    config["allowlist"]["packages"] = "\n".join([package_name])
    os.makedirs(os.path.join(plugin_path, "dist"), exist_ok=True)
    async with Master("https://pypi.org/") as master:
        mirror = BandersnatchMirror(homedir=plugin_path, master=master)
        name = Requirement(package_name).name
        result = await mirror.synchronize([name])
    package_found = False

    for package in result[name]:
        current_path = os.path.join(plugin_path, package)
        destination_path = os.path.join(plugin_path, "dist", os.path.basename(package))
        shutil.move(current_path, destination_path)
        package_found = True
    return package_found


def create_release_commits(repo, release_version, plugin_path):
    """Build changelog, set version, commit, bump to next dev version, commit."""
    issues_to_close = set()
    for filename in Path(f"{plugin_path}/CHANGES").rglob("*"):
        if filename.stem.isdigit():
            issue = filename.stem
            issues_to_close.add(issue)

    issues = ",".join(issues_to_close)
    # First commit: changelog
    os.system(f"towncrier --yes --version {release_version}")
    git = repo.git
    git.add("CHANGES.rst")
    git.add("CHANGES/*")
    git.commit("-m", f"Add changelog for {release_version}\n\n[noissue]")

    # Second commit: release version
    os.system("bump2version release --allow-dirty")

    git.add(f"{plugin_path}/{plugin_name}/*")
    git.add(f"{plugin_path}/docs/conf.py")
    git.add(f"{plugin_path}/setup.py")
    git.add(f"{plugin_path}/requirements.txt")
    git.add(f"{plugin_path}/.bumpversion.cfg")

    git.commit("-m", f"Release {release_version}\nGH Issues: {issues}\n\n[noissue]")

    sha = repo.head.object.hexsha
    short_sha = git.rev_parse(sha, short=7)

    os.system("bump2version patch --allow-dirty")

    new_dev_version = None
    with open(f"{plugin_path}/setup.py") as fp:
        for line in fp.readlines():
            if "version=" in line:
                new_dev_version = re.split("\"|'", line)[1]
        if not new_dev_version:
            raise RuntimeError("Could not detect new dev version ... aborting.")

    git.add(f"{plugin_path}/{plugin_name}/*")
    git.add(f"{plugin_path}/docs/conf.py")
    git.add(f"{plugin_path}/setup.py")
    git.add(f"{plugin_path}/requirements.txt")
    git.add(f"{plugin_path}/.bumpversion.cfg")
    git.commit("-m", f"Bump to {new_dev_version}\n\n[noissue]")

    print(f"Release commit == {short_sha}")
    print(f"All changes were committed on branch: release_{release_version}")
    return sha


def create_tag_and_build_package(repo, desired_tag, commit_sha, plugin_path):
    """Create a tag if one is needed and build a package if one is not on PyPI."""
    # Remove auth header config
    with repo.config_writer() as conf:
        conf.remove_section('http "https://github.com/"')
        conf.release()

    # Determine if a tag exists and if it matches the specified commit sha
    tag = None
    for existing_tag in repo.tags:
        if existing_tag.name == desired_tag:
            if existing_tag.commit.hexsha == commit_sha:
                tag = existing_tag
            else:
                raise RuntimeError(
                    "The '{desired_tag}' tag already exists, but the commit sha does not match "
                    "'{commit_sha}'."
                )

    # Create a tag if one does not exist
    if not tag:
        tag = repo.create_tag(desired_tag, ref=commit_sha)

    # Checkout the desired tag and reset the tree
    repo.head.reference = tag.commit
    repo.head.reset(index=True, working_tree=True)

    # Check if Package is available on PyPI
    loop = asyncio.get_event_loop()  # noqa
    # fmt: off
    package_found = asyncio.run(
        get_package_from_pypi("pulp-2to3-migration=={tag.name}", plugin_path)
    )  # noqa
    # fmt: on
    if not package_found:
        os.system("python3 setup.py sdist bdist_wheel --python-tag py3")


helper = textwrap.dedent(
    """\
        Start the release process.

        Example:
            setup.py on plugin before script:
                version="2.0.0.dev"

            $ python .ci/scripts/release.py

            setup.py on plugin after script:
                version="2.0.1.dev"


    """
)
parser = argparse.ArgumentParser(formatter_class=argparse.RawTextHelpFormatter, description=helper)

parser.add_argument(
    "release_version",
    type=str,
    help="The version string for the release.",
)

args = parser.parse_args()

release_version_arg = args.release_version

release_path = os.path.dirname(os.path.abspath(__file__))
plugin_path = release_path.split("/.github")[0]

plugin_name = "pulp_2to3_migration"
version = None
with open(f"{plugin_path}/setup.py") as fp:
    for line in fp.readlines():
        if "version=" in line:
            version = re.split("\"|'", line)[1]
    if not version:
        raise RuntimeError("Could not detect existing version ... aborting.")
release_version = version.replace(".dev", "")

print(f"\n\nRepo path: {plugin_path}")
repo = Repo(plugin_path)

release_commit = None
if release_version != release_version_arg:
    # Look for a commit with the requested release version
    for commit in repo.iter_commits():
        if f"Release {release_version_arg}\n" in commit.message:
            release_commit = commit
            release_version = release_version_arg
            break
    if not release_commit:
        raise RuntimeError(
            f"The release version {release_version_arg} does not match the .dev version at HEAD. "
            "A release commit for such version does not exist."
        )

if not release_commit:
    release_commit_sha = create_release_commits(repo, release_version, plugin_path)
else:
    release_commit_sha = release_commit.hexsha
create_tag_and_build_package(repo, release_version, release_commit_sha, plugin_path)
