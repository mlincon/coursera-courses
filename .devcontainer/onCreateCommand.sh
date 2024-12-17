#!/bin/bash

# Install dvc
echo "(*) Installing DVC ..."
pip install "dvc==3.55.2" "dvc-s3==3.2.0"

# Install pre-commit for git hook
echo "(*) Installing pre-commit requirements ..."
pip install \
    "isort" \
    "pre-commit" \
    "ruff" \
    "sqlfluff" \
    "yamllint"

# install flyway at home directory
echo "(*) Installing Flyway..."
cd ~
FLYWAY_VERSION="10.19.0"
wget -qO- "https://repo1.maven.org/maven2/org/flywaydb/flyway-commandline/${FLYWAY_VERSION}/flyway-commandline-${FLYWAY_VERSION}-linux-x64.tar.gz" \
    | tar -xvz && sudo ln -s "$(pwd)/flyway-${FLYWAY_VERSION}/flyway" /usr/local/bin

# install hadolint
echo "(*) Installing hadolint..."
HADOLINT_VERSION="2.12.0"
sudo wget -O /usr/local/bin/hadolint "https://github.com/hadolint/hadolint/releases/download/v${HADOLINT_VERSION}/hadolint-Linux-x86_64"
sudo chmod +x /usr/local/bin/hadolint
