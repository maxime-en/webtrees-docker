# Docker Image for [webtrees](https://webtrees.net/) from [NathanVaughn/webtrees-docker](https://github.com/NathanVaughn/webtrees-docker)

This docker image is very close to the NathanVaughn's one, apart from that
it can be executed without root rights (user option for instance).
Even if you start without the docker user option, the Dockerfile enforces
starting the application using a non-privileged user with the USER directive.

The NathanVaughn's docker image is multi-arch and can be executed standalone,
managing the SSL layer if required. This fork removes a lot of features not
useful from my side, for example the SSL layer is handled by a reverse
proxy. It also removes support for other database systems than mysql/mariadb.

## Usage

### Quickstart

No pre-built image is provided.
You can build the docker image easily by cloning the repository
and building from source:

```bash
git clone https://github.com/maxime-en/webtrees-docker.git
make
```

You will require the following dependancies:

* make
* curl
* docker
* docker buildx plugin

A [docker-compose.yml](https://github.com/maxime-en/webtrees-docker/blob/main/docker-compose.yml) example file is provided.

### Environment Variables

There are many environment variables available to help automatically configure
the container. For any environment variable you do not define,
the default value will be used.

> **🚨 WARNING 🚨**
> These environment variables will be visible in the webtrees control panel
> under "Server information". Either lock down the control panel
> to administrators, or use the webtrees setup wizard.

| Environment Variable                                                       | Required | Default               | Notes                                                                                                                                                                                                             |
| -------------------------------------------------------------------------- | -------- | --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `PRETTY_URLS`                                                              | No       | `False`               | Setting this to any truthy value (`True`, `1`, `yes`) will enable [pretty URLs](https://webtrees.net/faq/urls/). This can be toggled at any time, however you must go through initial setup at least once first.  |
| `LANG`                                                                     | Yes      | `en-us`               | webtrees localization setting. This takes a locale code. List: <https://github.com/fisharebest/webtrees/tree/main/resources/lang/>                                                                               |
| `BASE_URL`                                                                 | Yes      | None                  | Base URL of the installation, with protocol. This needs to be in the form of `http://webtrees.example.com`                                                                                                        |
| `DB_HOST`                                                                  | Yes      | None                  | Database server host.                                                                                                                                                                                             |
| `DB_PORT`                                                                  | Yes      | `3306`                | Database server port.                                                                                                                                                                                             |
| `DB_USER` or `MYSQL_USER` or `MARIADB_USER` or `POSTGRES_USER`             | Yes      | `webtrees`            | Database server username.                                                                                                                                                                                         |
| `DB_PASS` or `MYSQL_PASSWORD` or `MARIADB_PASSWORD` or `POSTGRES_PASSWORD` | Yes      | None                  | Database server password.                                                                                                                                                                                         |
| `DB_NAME` or `MYSQL_DATABASE` or `MARIADB_DATABASE` or `POSTGRES_DB`       | Yes      | `webtrees`            | Database name.                                                                                                                                                                                                    |
| `DB_PREFIX`                                                                | Yes      | `wt_`                 | Prefix to give all tables in the database. Set this to a value of `""` to have no table prefix.                                                                                                                   |
| `DB_KEY`                                                                   | No       | None                  | Key file used to verify the MySQL server. Only use with the `mysql` database driver. Relative to the `/var/www/webtrees/data/` directory.                                                                         |
| `DB_CERT`                                                                  | No       | None                  | Certificate file used to verify the MySQL server. Only use with the `mysql` database driver. Relative to the `/var/www/webtrees/data/` directory.                                                                 |
| `DB_CA`                                                                    | No       | None                  | Certificate authority file used to verify the MySQL server. Only use with the `mysql` database driver. Relative to the `/var/www/webtrees/data/` directory.                                                       |
| `DB_VERIFY`                                                                | No       | `False`               | Whether to verify the MySQL server. Only use with the `mysql` database driver. If `True`, you must also fill out `DB_KEY`, `DB_CERT`, and `DB_CA`.                                                                |
| `WT_USER`                                                                  | Yes      | None                  | First admin account username. Note, this is only used the first time the container is run, and the database is initialized.                                                                                       |
| `WT_NAME`                                                                  | Yes      | None                  | First admin account full name. Note, this is only used the first time the container is run, and the database is initialized.                                                                                      |
| `WT_PASS`                                                                  | Yes      | None                  | First admin account password. Note, this is only used the first time the container is run, and the database is initialized.                                                                                       |
| `WT_EMAIL`                                                                 | Yes      | None                  | First admin account email. Note, this is only used the first time the container is run, and the database is initialized.                                                                                          |
| `PHP_MEMORY_LIMIT`                                                         | No       | `1024M`               | PHP memory limit. See the [PHP documentation](https://www.php.net/manual/en/ini.core.php#ini.memory-limit)                                                                                                        |
| `PHP_MAX_EXECUTION_TIME`                                                   | No       | `90`                  | PHP max execution time for a request in seconds. See the [PHP documentation](https://www.php.net/manual/en/info.configuration.php#ini.max-execution-time)                                                         |
| `PHP_POST_MAX_SIZE`                                                        | No       | `50M`                 | PHP POST request max size. See the [PHP documentation](https://www.php.net/manual/en/ini.core.php#ini.post-max-size)                                                                                              |
| `PHP_UPLOAD_MAX_FILE_SIZE`                                                 | No       | `50M`                 | PHP max uploaded file size. See the [PHP documentation](https://www.php.net/manual/en/ini.core.php#ini.upload-max-filesize)                                                                                       |
| `TRUSTED_HEADERS`                                                          | No       | None                  | Header to trust when behind a reverse proxy to get the real user IP. See [webtrees documentation](https://webtrees.net/admin/proxy/).                                                                               |

Additionally, you can add `_FILE` to the end of any environment variable name,
and instead that will read the value in from the given filename.
For example, setting `DB_PASS_FILE=/run/secrets/my_db_secret` will read the contents
of that file into `DB_PASS`.

If you don't want the container to be configured automatically
(if you're migrating from an existing webtrees installation for example), simply leave
the database (`DB_`) and webtrees (`WT_`) variables blank, and you can complete the
[setup wizard](https://i.imgur.com/rw70cgW.png) like normal.

### Database

webtrees [recommends](https://webtrees.net/install/requirements/)
a MySQL (or compatible equivalent) database.
You will need a separate container for this.

- [MariaDB](https://hub.docker.com/_/mariadb)
- [MySQL](https://hub.docker.com/_/mysql)

### Volumes

The image mounts:

- `/var/www/webtrees/data/`

(media is stored in the `media` subfolder)

If you want to add custom [themes or modules](https://webtrees.net/download/modules),
you can also mount the `/var/www/webtrees/modules_v4/` directory.

Example `docker-compose`:

```yml
volumes:
  - app_data:/var/www/webtrees/data/
  - app_themes:/var/www/webtrees/modules_v4/
---
volumes:
  app_data:
    driver: local
  app_themes:
    driver: local
```

### Network

The image exposes port 8080.

Example `docker-compose`:

```yml
ports:
  - 8080:8080
```

### ImageMagick

`ImageMagick` is included in this image to speed up
[thumbnail creation](https://webtrees.net/faq/thumbnails/).
webtrees will automatically prefer it over `gd` with no configuration.
