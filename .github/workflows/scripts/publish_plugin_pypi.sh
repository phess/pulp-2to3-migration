#!/bin/bash

# WARNING: DO NOT EDIT!
#
# This file was generated by plugin_template, and is managed by it. Please use
# './plugin-template --github pulp_2to3_migration' to update this file.
#
# For more info visit https://github.com/pulp/plugin_template

# make sure this script runs at the repo root
cd "$(dirname "$(realpath -e "$0")")"/../../..

set -euv

export PULP_URL="${PULP_URL:-http://pulp}"

export response=$(curl --write-out %{http_code} --silent --output /dev/null https://pypi.org/project/pulp-2to3-migration/$1/)
if [ "$response" == "200" ];
then
  echo "pulp-2to3-migration $1 has already been released. Skipping."
  exit
fi

pip install twine

twine check dist/pulp_2to3_migration-$1-py3-none-any.whl || exit 1
twine check dist/pulp-2to3-migration-$1.tar.gz || exit 1
twine upload dist/pulp_2to3_migration-$1-py3-none-any.whl -u pulp -p $PYPI_PASSWORD
twine upload dist/pulp-2to3-migration-$1.tar.gz -u pulp -p $PYPI_PASSWORD

exit $?
