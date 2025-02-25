---
title: "Manual installation"
slug: "manual-installation"
hidden: false
createdAt: "2022-07-12T00:00:00.000Z"
---

> 🚧 This page describes an old, deprecated method for installing Pants. 
> We highly recommend using the `pants` [launcher binary](doc:installation) instead.

Manual installation
-------------------

This installation method requires Python 3.7, 3.8, or 3.9 discoverable on your `PATH`. On macOS on Apple Silicon (M1/M2), it must be Python 3.9. 

Pants is invoked via a launch script named `./pants` , saved at the root of the repository. This script will install Pants and handle upgrades.

First, pick a release version. You can see the available releases [on PyPI](https://pypi.org/project/pantsbuild.pants/). We recommend picking the current stable release, unless you have reason to need a more recent one, such as a release candidate or a development release.

Then, set up a minimal `pants.toml` config file, filling in the version you selected:

```bash
printf '[GLOBAL]\npants_version = "X.Y.Z"\n' > pants.toml
```

Then, download the script:

```bash
curl -L -O https://static.pantsbuild.org/setup/pants && chmod +x ./pants
```

Now, run this to bootstrap Pants and to verify the version it installs:

```bash
./pants --version
```

> 📘 Add `./pants` to version control
> 
> You should check the `./pants` script into your repo so that all users can easily run Pants.

> 👍 Upgrading Pants
> 
> The `./pants` script will automatically install and use the Pants version specified in `pants.toml`, so upgrading Pants is as simple as editing `pants_version` in that file.

Building Pants from sources
---------------------------

We currently distribute Pants for Linux (x86_64 and ARM64) and macOS (x86_64 and ARM64).

If you need to run Pants on some other platform, such as Alpine Linux, you can try building it yourself by checking out the [Pants repo](https://github.com/pantsbuild/pants), and running `./pants package src/python/pants:pants-packaged` to build a wheel.
